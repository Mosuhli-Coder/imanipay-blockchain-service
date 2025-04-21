# /imanipay-blockchain-service/app/api/transactions.py
from fastapi import APIRouter, Depends
from app.services.transactions import TransactionService
from app.schemas import SendPaymentRequest, SendPaymentResponse # Import the new response schema

router = APIRouter(prefix="/transactions", tags=["Transactions"])

@router.post("/send", response_model=SendPaymentResponse) # Change the response model
async def send_payment(payment_in: SendPaymentRequest, transaction_service: TransactionService = Depends()):
    print(f"Received payment_in: {payment_in}")
    """
    Calculates the payment transaction details.  The Main Backend is responsible
    for sending the transaction and recording it in the database.
    """
    return await transaction_service.send_payment(payment_in)
