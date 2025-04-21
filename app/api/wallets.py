# /imanipay-blockchain-service/app/api/wallets.py
from fastapi import APIRouter, Depends
from app.services.wallets import WalletService
from app.schemas import WalletResponse, BalanceResponse, BalanceRequest, ValidateWalletRequest, ValidateWalletResponse # Import the new schema

router = APIRouter(prefix="/wallets", tags=["Wallets"])

@router.post("/balance", response_model=BalanceResponse)
async def get_balance(balance_in: BalanceRequest, wallet_service: WalletService = Depends()):
    """Retrieves the balance of a given Algorand wallet address."""
    return await wallet_service.get_balance(balance_in)

@router.post("/validate", response_model=ValidateWalletResponse) # Add the new endpoint
async def validate_wallet(validate_in: ValidateWalletRequest, wallet_service: WalletService = Depends()):
    """
    Validates if a given Algorand wallet address is valid and exists on the blockchain.
    """
    return await wallet_service.validate_wallet(validate_in)


@router.post("/create", response_model=WalletResponse) # Add the new endpoint
async def create_wallet(wallet_service: WalletService = Depends()):
    """Creates a new Algorand wallet.  For DEVELOPMENT PURPOSES ONLY."""
    return await wallet_service.create_wallet()