from sqlalchemy import Column, Integer, String, BigInteger, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    wallet_address = Column(String, unique=True, index=True, nullable=False)
    nonce = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    apis = relationship("Api", back_populates="owner")
    usage_logs = relationship("UsageLog", back_populates="user")

class Api(Base):
    __tablename__ = "apis"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    price_per_request = Column(BigInteger, nullable=False)  # in wei
    owner_id = Column(Integer, ForeignKey("users.id"))
    contract_api_id = Column(Integer, nullable=True)  # ID on blockchain
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    owner = relationship("User", back_populates="apis")
    usage_logs = relationship("UsageLog", back_populates="api")

class UsageLog(Base):
    __tablename__ = "usage_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    api_id = Column(Integer, ForeignKey("apis.id"))
    request_count = Column(Integer, default=0)
    pending_payment = Column(BigInteger, default=0)  # in wei
    batch_id = Column(String, nullable=True)  # for blockchain settlement
    is_settled = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    user = relationship("User", back_populates="usage_logs")
    api = relationship("Api", back_populates="usage_logs")