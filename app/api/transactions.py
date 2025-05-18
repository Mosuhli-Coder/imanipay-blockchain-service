# /imanipay-blockchain-service/app/api/transactions.py
from fastapi import APIRouter, Depends, HTTPException
from app.services.transactions import TransactionService
from app.schemas import SendPaymentRequest, SendPaymentResponse # Import the new response schema
from typing import Annotated
from fastapi import Header
from app.services.wallets import WalletService

router = APIRouter(prefix="/transactions", tags=["Transactions"])

# @router.post("/send", response_model=SendPaymentResponse) # Change the response model
# async def send_payment(payment_in: SendPaymentRequest, transaction_service: TransactionService = Depends()):
#     print(f"Received payment_in: {payment_in}")
#     """
#     Calculates the payment transaction details.  The Main Backend is responsible
#     for sending the transaction and recording it in the database.
#     """
#     return await transaction_service.send_payment(payment_in)


@router.post("/send", response_model=SendPaymentResponse)
async def send_funds(
    payment_in: SendPaymentRequest,
    wallet_service: WalletService = Depends(),
    transaction_service: TransactionService = Depends(),
):
    """Allows a user to send Algos or stablecoins."""
    user_wallet_data = payment_in.user_wallet
    if not user_wallet_data or "encrypted_mnemonic" not in user_wallet_data or "wallet_address" not in user_wallet_data:
        raise HTTPException(status_code=400, detail="Invalid user wallet data provided")

    sender_wallet_info = await transaction_service.get_user_wallet_info(user_wallet_data)
    print(f"Sender wallet data: {user_wallet_data}")
    print(f"Sender wallet info: {sender_wallet_info}")
    if not sender_wallet_info or "private_key" not in sender_wallet_info or "wallet_address" not in sender_wallet_info:
        raise HTTPException(status_code=500, detail="Failed to retrieve sender wallet details")

    sender_private_key = sender_wallet_info["private_key"]
    sender_address = sender_wallet_info["wallet_address"]

    return await transaction_service.send_payment(payment_in, sender_private_key, sender_address)