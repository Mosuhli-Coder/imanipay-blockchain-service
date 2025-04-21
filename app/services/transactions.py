# /imanipay-blockchain-service/app/services/transactions.py
import logging
from algosdk.v2client import algod
from algosdk import transaction, account
from algosdk.transaction import ApplicationCallTxn, SuggestedParams, PaymentTxn, AssetTransferTxn
from algosdk.encoding import encode_address, decode_address
from app.core.config import settings
from app.schemas import SendPaymentRequest, SendPaymentResponse
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the transaction fee tiers.
TRANSACTION_FEES = [
    {"min": 0, "max": 100, "percentageCharge": 0.01, "flatCharge": 0},
    {"min": 100, "max": 1000, "percentageCharge": 0.005, "flatCharge": 0},
    {"min": 1000, "percentageCharge": 0, "flatCharge": 5},
]

class TransactionService:
    def __init__(self):
        self.algod_client = algod.AlgodClient(settings.ALGORAND_API_KEY, settings.ALGORAND_NODE_URL)
        self.admin_wallet_address = settings.IMANIPAY_WALLET_ADDRESS
        self.deployer_private_key = settings.DEPLOYER_PRIVATE_KEY
        if not self.deployer_private_key:
            raise ValueError("DEPLOYER_PRIVATE_KEY is not set. Cannot send fees.")
        self.sender_account = account.Account.from_private_key(self.deployer_private_key)  # Derive sender account
        self.app_id = settings.PAYMENT_CONTRACT_APP_ID # Load app ID from settings
        if not self.app_id:
            raise ValueError("PAYMENT_CONTRACT_APP_ID is not set.  You must deploy the contract.")

    def calculate_transaction_fee(self, amount: float) -> float:
        """Calculates the transaction fee based on the amount."""
        for tier in TRANSACTION_FEES:
            if tier.get("max") is None and amount >= tier["min"]:
                return amount * tier.get("percentageCharge", 0) + tier.get("flatCharge", 0)
            if tier.get("min", 0) <= amount <= tier.get("max", float('inf')):
                return amount * tier.get("percentageCharge", 0) + tier.get("flatCharge", 0)
        return 0  # Default to no fee

    async def send_payment(self, payment_in: SendPaymentRequest) -> SendPaymentResponse:
        """
        Calculates the transaction details and sends the transaction to the Algorand blockchain
        using a smart contract.
        """
        algod_client = self.algod_client
        sender = self.sender_account.address
        sender_private_key = self.deployer_private_key  # Use the deployer key
        app_id = self.app_id

        # 1. Calculate the transaction fee.
        fee_amount = self.calculate_transaction_fee(payment_in.amount)
        total_amount_to_send = payment_in.amount + fee_amount # Sender pays amount + fee
        actual_payment_amount = payment_in.amount  # Contract sends the amount

        print(f"Calculated fee: {fee_amount}, Total amount from sender: {total_amount_to_send}, Amount to receiver: {actual_payment_amount}")

        # 2. Get transaction parameters.
        params: SuggestedParams = await algod_client.suggested_params()

        # 3. Prepare the smart contract call.
        app_call_txn = ApplicationCallTxn(
            sender=sender,
            sp=params,
            index=app_id,  # The Application ID of the deployed contract
            on_complete=transaction.OnComplete.NoOpOC,  # NoOp call
            application_args=[
                encode_address(payment_in.receiver_wallet_address),  # Receiver address (encoded)
                actual_payment_amount.to_bytes(8, "big"),  # Amount (as bytes)
                fee_amount.to_bytes(8, "big"), # Fee amount (as bytes)
            ],
        )

        # 4. Create a transaction that pays the smart contract, including the fee.
        payment_txn = PaymentTxn(
            sender=sender,
            sp=params,
            receiver=sender,  # Send to yourself (contract address will handle it)
            amt=total_amount_to_send, # Sender pays amount + fee
        )
        # Group the transactions
        grouped_transaction = transaction.Group([app_call_txn, payment_txn])


        # 5. Sign the grouped transaction
        signed_group = grouped_transaction.sign(sender_private_key)
        # signed_txn = app_call_txn.sign(sender_private_key)  # Sign the transaction

        # 6. Send the transaction to the blockchain
        try:
            txid = await algod_client.send_transactions(signed_group) # Send the group
            logger.info(f"Transaction group sent with ID: {txid}")
        except Exception as e:
            logger.error(f"Error sending transaction: {e}")
            raise  # Re-raise the exception to be handled by FastAPI

        # 7. Return the transaction data. Include the txid.
        return SendPaymentResponse(
            sender_wallet_address=sender,
            receiver_wallet_address=payment_in.receiver_wallet_address,
            amount=payment_in.amount,
            actual_payment_amount=actual_payment_amount,
            fee_amount=fee_amount,
            params={
                "fee": params.fee,
                "first": params.first,
                "last": params.last,
                "ghash": params.genesis_hash,
                "genesisID": params.genesis_id,
                "genesisHash": params.genesis_hash,
            },
            asset_id=payment_in.asset_id,
            admin_wallet_address=self.admin_wallet_address,
            txid=txid,  # Include the transaction ID in the response
        )
