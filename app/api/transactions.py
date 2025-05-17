# /imanipay-blockchain-service/app/api/transactions.py
from fastapi import APIRouter, Depends, HTTPException
from app.services.transactions import TransactionService
from app.schemas import SendPaymentRequest, SendPaymentResponse # Import the new response schema
from typing import Annotated
from fastapi import Header

router = APIRouter(prefix="/transactions", tags=["Transactions"])

@router.post("/send", response_model=SendPaymentResponse) # Change the response model
async def send_payment(payment_in: SendPaymentRequest, transaction_service: TransactionService = Depends()):
    print(f"Received payment_in: {payment_in}")
    """
    Calculates the payment transaction details.  The Main Backend is responsible
    for sending the transaction and recording it in the database.
    """
    return await transaction_service.send_payment(payment_in)


@router.post("/sent", response_model=SendPaymentResponse)
async def send_funds(
    payment_in: SendPaymentRequest,
    transaction_service: TransactionService = Depends(),
    # user_id: Annotated[str | None, Header()] = None  # Example: Get user ID from header
):
    """Allows a user to send Algos or stablecoins."""
    user_id = payment_in.user_id
    if not user_id:
        raise HTTPException(status_code=401, detail="User authentication required")
    # In a real application, you would retrieve the sender's private key
    # securely based on the user_id. DO NOT hardcode or expose private keys.
    # Example (replace with your secure key retrieval mechanism):
    sender_wallet_info = await transaction_service.get_user_wallet_info(user_id)
    if not sender_wallet_info or "private_key" not in sender_wallet_info:
        raise HTTPException(status_code=404, detail="Sender wallet not found")

    sender_private_key = sender_wallet_info["private_key"]
    sender_address = sender_wallet_info["wallet_address"]

    return await transaction_service.send_payment(payment_in, sender_private_key, sender_address)
