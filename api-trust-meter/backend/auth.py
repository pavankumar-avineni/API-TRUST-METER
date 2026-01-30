import secrets
from datetime import datetime, timedelta
from eth_account.messages import encode_defunct
from web3 import Web3
from sqlalchemy.orm import Session
from models import User

def generate_nonce():
    return secrets.token_hex(32)

def verify_signature(message, signature, address):
    try:
        w3 = Web3()
        message_hash = encode_defunct(text=message)
        recovered_address = w3.eth.account.recover_message(message_hash, signature=signature)
        return recovered_address.lower() == address.lower()
    except:
        return False

def create_siwe_message(address, nonce):
    issued_at = datetime.utcnow().isoformat()
    expiration = (datetime.utcnow() + timedelta(hours=24)).isoformat()
    
    return f"""localhost:3000 wants you to sign in with your Ethereum account:
{address}

I accept the Terms of Service: https://localhost:3000/tos

URI: http://localhost:3000
Version: 1
Chain ID: 31337
Nonce: {nonce}
Issued At: {issued_at}
Expiration Time: {expiration}"""

def get_or_create_user(db: Session, wallet_address: str):
    user = db.query(User).filter(User.wallet_address == wallet_address).first()
    if not user:
        user = User(wallet_address=wallet_address, nonce=generate_nonce())
        db.add(user)
        db.commit()
        db.refresh(user)
    return user