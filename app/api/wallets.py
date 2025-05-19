# /imanipay-blockchain-service/app/api/wallets.py
from fastapi import APIRouter, Depends
from app.services.wallets import WalletService
from app.schemas import WalletResponse, BalanceResponse, BalanceRequest, ValidateWalletRequest, ValidateWalletResponse, CreateWalletRequest, CreateWalletOptInResponse # Import the new schema
from typing import Dict, Any

router = APIRouter(prefix="/wallets", tags=["Wallets"])

@router.post("/balance")
async def get_balance(balance_in: Dict[str, str], wallet_service: "WalletService" = Depends()):
    """Retrieves the balance of a given Algorand wallet address."""
    return await wallet_service.get_balance(balance_in)

@router.post("/validate", response_model=ValidateWalletResponse) # Add the new endpoint
async def validate_wallet(validate_in: ValidateWalletRequest, wallet_service: WalletService = Depends()):
    """
    Validates if a given Algorand wallet address is valid and exists on the blockchain.
    """
    return await wallet_service.validate_wallet(validate_in)


@router.post("/create-with-optin", response_model=CreateWalletOptInResponse)
async def create_wallet_with_optin(create_in: CreateWalletRequest, wallet_service: WalletService = Depends()):
    """Creates a new Algorand wallet, opts it into USDC, and associates it with a user ID."""
    return await wallet_service.generate_and_opt_in_wallet(create_in.user_id)