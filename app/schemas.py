# /imanipay-blockchain-service/app/schemas.py
from pydantic import BaseModel
from typing import Optional, Dict

class ConnectWalletRequest(BaseModel):
    user_id: str  # The ID of the user from the Main Backend's database
    wallet_address: str

class WalletResponse(BaseModel):
    user_id: str
    wallet_address: str

class BalanceRequest(BaseModel):
    wallet_address: str

class BalanceResponse(BaseModel):
    wallet_address: str
    balances: dict

class SendPaymentRequest(BaseModel):
    sender_wallet_address: str
    receiver_wallet_address: str
    amount: float
    asset_name: str
    user_id: str

class TransactionResponse(BaseModel):
    transaction_id: str

class CreateEscrowRequest(BaseModel):
    seller_wallet_address: str
    buyer_wallet_address: str
    payment_amount: float
    asset_id: int
    timeout: int  # Unix timestamp

class EscrowResponse(BaseModel):
    app_id: int
    transaction_id: str = None

class ReleaseEscrowRequest(BaseModel):
    escrow_id: int # The application ID of the escrow contract
    release_address: str # Address authorized to release (seller or buyer based on logic)

# Add the new schema for the /wallets/validate endpoint
class ValidateWalletRequest(BaseModel):
    wallet_address: str

class ValidateWalletResponse(BaseModel):
    is_valid: bool
    wallet_address: str

class SendPaymentResponse(BaseModel): #  Define the new response schema
    sender_wallet_address: str
    receiver_wallet_address: str
    amount: float
    actual_payment_amount: float
    fee_amount: float
    params: Dict #  Dictionary of the params
    asset_id: int
    admin_wallet_address: str

class CreateWalletRequest(BaseModel):
    user_id: str

class CreateWalletOptInResponse(BaseModel):
    user_id: str
    wallet_address: Optional[str]  # ✅ Make it optional
    opted_in_usdc: bool
    network: str
    encrypted_mnemonic_phrase: Optional[str]
    error: Optional[str] = None