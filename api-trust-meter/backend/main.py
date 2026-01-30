from fastapi import FastAPI, Depends, HTTPException, status, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from web3 import Web3
import secrets
import json
from typing import Optional

from database import get_db, init_db
from models import User, Api, UsageLog
from auth import verify_signature, create_siwe_message, get_or_create_user, generate_nonce

app = FastAPI(title="Decentralized API Trust Meter")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
init_db()

# Web3 connection to local Hardhat node
w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:8545'))

# Load contract ABI (simplified for this example)
CONTRACT_ABI = [
    {
        "inputs": [
            {"internalType": "string", "name": "_name", "type": "string"},
            {"internalType": "uint256", "name": "_pricePerRequest", "type": "uint256"}
        ],
        "name": "registerApi",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "bytes32", "name": "_batchId", "type": "bytes32"},
            {"internalType": "address", "name": "_user", "type": "address"},
            {"internalType": "uint256", "name": "_apiId", "type": "uint256"},
            {"internalType": "uint256", "name": "_requestCount", "type": "uint256"}
        ],
        "name": "settlePayment",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    }
]

def get_contract():
    # This will be set after deployment
    contract_address = "0x5FbDB2315678afecb367f032d93F642f64180aa3"  # Default Hardhat first account
    return w3.eth.contract(address=contract_address, abi=CONTRACT_ABI)

# Authentication dependency
async def get_current_user(
    wallet_address: str = Header(None),
    signature: str = Header(None),
    db: Session = Depends(get_db)
):
    if not wallet_address or not signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Wallet address and signature required"
        )
    
    user = get_or_create_user(db, wallet_address)
    message = create_siwe_message(wallet_address, user.nonce)
    
    if not verify_signature(message, signature, wallet_address):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature"
        )
    
    # Generate new nonce for next request
    user.nonce = generate_nonce()
    db.commit()
    
    return user

@app.get("/")
def read_root():
    return {"message": "Decentralized API Trust Meter Backend"}

@app.post("/api/nonce")
def get_nonce(wallet_address: str, db: Session = Depends(get_db)):
    user = get_or_create_user(db, wallet_address)
    return {"nonce": user.nonce}

@app.post("/api/register")
def register_api(
    api_name: str,
    price_per_request: int,  # in wei
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Create API in database
    api = Api(
        name=api_name,
        price_per_request=price_per_request,
        owner_id=current_user.id
    )
    db.add(api)
    db.commit()
    db.refresh(api)
    
    # Register on blockchain (optional - could be done later)
    try:
        contract = get_contract()
        # In production, you'd use the user's private key to sign
        # For simplicity, we're just storing locally
        api.contract_api_id = api.id  # Use same ID for simplicity
        db.commit()
    except Exception as e:
        print(f"Blockchain registration failed: {e}")
    
    return {"api_id": api.id, "message": "API registered successfully"}

@app.post("/api/log-usage")
def log_api_usage(
    api_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    api = db.query(Api).filter(Api.id == api_id).first()
    if not api:
        raise HTTPException(status_code=404, detail="API not found")
    
    # Find or create usage log
    usage_log = db.query(UsageLog).filter(
        UsageLog.user_id == current_user.id,
        UsageLog.api_id == api_id,
        UsageLog.is_settled == False
    ).first()
    
    if not usage_log:
        usage_log = UsageLog(
            user_id=current_user.id,
            api_id=api_id,
            request_count=0,
            pending_payment=0
        )
        db.add(usage_log)
    
    # Update counts
    usage_log.request_count += 1
    usage_log.pending_payment += api.price_per_request
    
    db.commit()
    db.refresh(usage_log)
    
    return {
        "request_count": usage_log.request_count,
        "pending_payment": usage_log.pending_payment,
        "total_cost": usage_log.pending_payment
    }

@app.get("/api/usage/{api_id}")
def get_api_usage(
    api_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    usage_log = db.query(UsageLog).filter(
        UsageLog.user_id == current_user.id,
        UsageLog.api_id == api_id,
        UsageLog.is_settled == False
    ).first()
    
    if not usage_log:
        return {"request_count": 0, "pending_payment": 0, "total_cost": 0}
    
    return {
        "request_count": usage_log.request_count,
        "pending_payment": usage_log.pending_payment,
        "total_cost": usage_log.pending_payment
    }

@app.get("/api/my-apis")
def get_my_apis(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    apis = db.query(Api).filter(Api.owner_id == current_user.id).all()
    return [{"id": api.id, "name": api.name, "price": api.price_per_request} for api in apis]

@app.get("/api/available-apis")
def get_available_apis(db: Session = Depends(get_db)):
    apis = db.query(Api).all()
    return [{"id": api.id, "name": api.name, "price": api.price_per_request} for api in apis]

@app.post("/api/settle/{api_id}")
def settle_payment(
    api_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    usage_log = db.query(UsageLog).filter(
        UsageLog.user_id == current_user.id,
        UsageLog.api_id == api_id,
        UsageLog.is_settled == False
    ).first()
    
    if not usage_log or usage_log.request_count == 0:
        raise HTTPException(status_code=400, detail="No pending payments")
    
    api = db.query(Api).filter(Api.id == api_id).first()
    if not api:
        raise HTTPException(status_code=404, detail="API not found")
    
    # Generate batch ID
    batch_id = secrets.token_hex(32)
    usage_log.batch_id = batch_id
    
    # Prepare settlement data
    settlement_data = {
        "batch_id": batch_id,
        "user_address": current_user.wallet_address,
        "api_id": api.contract_api_id or api.id,
        "request_count": usage_log.request_count,
        "total_amount": usage_log.pending_payment,
        "api_owner": api.owner.wallet_address
    }
    
    return {
        "settlement_data": settlement_data,
        "message": "Ready for blockchain settlement"
    }

@app.post("/api/confirm-settlement/{api_id}")
def confirm_settlement(
    api_id: int,
    transaction_hash: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    usage_log = db.query(UsageLog).filter(
        UsageLog.user_id == current_user.id,
        UsageLog.api_id == api_id,
        UsageLog.is_settled == False
    ).first()
    
    if not usage_log:
        raise HTTPException(status_code=404, detail="No pending settlement")
    
    # Verify transaction (simplified)
    try:
        tx = w3.eth.get_transaction(transaction_hash)
        if tx and tx['to']:  # Basic validation
            usage_log.is_settled = True
            db.commit()
            return {"message": "Settlement confirmed"}
    except:
        pass
    
    raise HTTPException(status_code=400, detail="Invalid transaction")