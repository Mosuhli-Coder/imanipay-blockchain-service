# /imanipay-blockchain-service/app/services/transactions.py
import logging
from algosdk.v2client import algod
from algosdk import transaction, account, mnemonic
from algosdk.transaction import (
    ApplicationCallTxn,
    SuggestedParams,
    PaymentTxn,
    AssetTransferTxn,
)
from algosdk.encoding import encode_address, decode_address
from app.core.config import settings
from app.schemas import SendPaymentRequest, SendPaymentResponse
from app.services.wallets import WalletService

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
        self.algod_client = algod.AlgodClient(
            settings.ALGORAND_API_KEY,
            settings.ALGORAND_NODE_URL,
            headers={"X-API-Key": settings.ALGORAND_API_KEY},
        )

        self.network = settings.ALGORAND_NETWORK
        self.usdc_asset_id = int(settings.USDC_ASSET_ID)
        self.usdt_asset_id = int(settings.USDT_ASSET_ID)  # Add this to your settings

        if not settings.FUNDER_MNEMONIC_KEY:
            raise ValueError("FUNDER_MNEMONIC_KEY is not set")

        self.admin_wallet_address = settings.IMANIPAY_WALLET_ADDRESS

    def calculate_transaction_fee(self, amount: float) -> float:
        """Calculates the transaction fee based on the amount."""
        for tier in TRANSACTION_FEES:
            if tier.get("max") is None and amount >= tier["min"]:
                return amount * tier.get("percentageCharge", 0) + tier.get(
                    "flatCharge", 0
                )
            if tier.get("min", 0) <= amount <= tier.get("max", float("inf")):
                return amount * tier.get("percentageCharge", 0) + tier.get(
                    "flatCharge", 0
                )
        return 0  # Default to no fee

    def get_suggested_params(self) -> SuggestedParams:
        """Gets suggested transaction parameters from the Algorand client."""
        return self.algod_client.suggested_params()


    async def send_payment(
        self,
        payment_in: SendPaymentRequest,
        sender_private_key: str,
        sender_address: str,
    ) -> SendPaymentResponse:
        """
        Allows a user to send Algos or stablecoins (by asset name) to another user.
        """
        algod_client = self.algod_client
        receiver_address = payment_in.receiver_wallet_address
        amount = payment_in.amount
        asset_name = payment_in.asset_name.upper()  # Use name instead of asset_id

        # Map asset name to ID using environment settings
        asset_map = {
            "ALGO": 0,
            "USDC": int(settings.USDC_ASSET_ID),
            "USDT": int(settings.USDT_ASSET_ID),
        }

        if asset_name not in asset_map:
            raise ValueError(f"Unsupported asset: {asset_name}")

        asset_id = asset_map[asset_name]

        print(
            f"Sending {amount} of asset {asset_name} (ID: {asset_id}) from {sender_address} to {receiver_address}"
        )

        params: SuggestedParams = self.get_suggested_params()

        if asset_id == 0:  # Sending Algos
            scaled_amount = int(amount * 1_000_000)
            txn = PaymentTxn(
                sender=sender_address,
                receiver=receiver_address,
                amt=scaled_amount,
                sp=params,
            )
        else:  # Sending a specific asset
            asset_info = algod_client.asset_info(asset_id)
            decimals = asset_info["params"]["decimals"]
            scaled_amount = int(amount * (10**decimals))
            txn = AssetTransferTxn(
                sender=sender_address,
                receiver=receiver_address,
                amt=scaled_amount,
                index=asset_id,
                sp=params,
            )

        signed_txn = txn.sign(sender_private_key)

        try:
            txid = algod_client.send_transaction(signed_txn)
            logger.info(f"Transaction sent with ID: {txid}")
            pending_txn = transaction.wait_for_confirmation(algod_client, txid, 4)
            logger.info(f"Transaction confirmed in round {pending_txn['confirmed-round']}")
        except Exception as e:
            logger.error(f"Error sending transaction: {e}")
            raise

        return SendPaymentResponse(
            sender_wallet_address=sender_address,
            receiver_wallet_address=receiver_address,
            amount=amount,
            actual_payment_amount=amount,
            fee_amount=params.fee / 1_000_000,
            params={
                "fee": params.fee,
                "first": params.first,
                "last": params.last,
                "ghash": params.gh,
            },
            asset_id=asset_id,
            admin_wallet_address=self.admin_wallet_address,
            txid=txid,
        )

    # *** ADD THIS FUNCTION ***
    # async def get_user_wallet_info(self, user_id: str):  # -> Optional[Dict[str, str]]:
    #     """
    #     Retrieves the wallet address and (decrypted) private key for a given user ID.
    #     **IMPORTANT: This function must securely retrieve and decrypt the private key.**
    #     """
    #     # Replace this with your actual database interaction logic
    #     # Example using SQLAlchemy (adapt to your ORM or database):
    #     # db: Session = Depends(get_db) # If using FastAPI Depends for DB session
    #     # user_wallet = db.query(UserWallet).filter(UserWallet.user_id == user_id).first()
    #     # if user_wallet:
    #     #     # Assuming user_wallet.encrypted_mnemonic holds the encrypted mnemonic
    #     #     decrypted_mnemonic = self._decrypt_mnemonic(user_wallet.encrypted_mnemonic)
    #     #     private_key = self.get_private_key_from_mnemonic(decrypted_mnemonic)
    #     #     return {
    #     #         "wallet_address": user_wallet.wallet_address,
    #     #         "private_key": private_key
    #     #     }
    #     # return None
    #     # *** SECURE KEY RETRIEVAL IMPLEMENTATION REQUIRED HERE ***
    #     # This is a placeholder - replace with your actual secure retrieval
    #     # and decryption logic.
    #     # You might need to inject a dependency for your database session.
    #     print(
    #         f"Simulating retrieval of wallet info for user: {user_id} - SECURE IMPLEMENTATION NEEDED"
    #     )
    #     # In a real scenario, you would fetch from your database, decrypt, and derive.
    #     # For this example, we'll return a placeholder (DO NOT DO THIS IN PRODUCTION)
    #     #         {
    #     #     "user_id": "some_unique_user_identifier",
    #     #     "wallet_address": "DVNLHVNF36VI5J74UFNOO3DELPKQSYFNVBFD2C3NKV7SDI2PGU6QYZJKGQ",
    #     #     "opted_in_usdc": true,
    #     #     "network": "testnet",
    #     #     "mnemonic_phrase": "siren injury come emotion utility pond shock skirt chimney tag coin palace lumber version south olive sock away elegant tomato message soul hazard about damp",
    #     #     "error": null
    #     # }
    #     if user_id == "some_user":
    #         mnemonic_phrase = "siren injury come emotion utility pond shock skirt chimney tag coin palace lumber version south olive sock away elegant tomato message soul hazard about damp"  # Replace with secure retrieval
    #         wallet_service = WalletService()
    #         private_key = wallet_service.get_private_key_from_mnemonic(mnemonic_phrase)
    #         address = account.address_from_private_key(private_key)
    #         return {"wallet_address": address, "private_key": private_key}
    #     return None

    async def get_user_wallet_info(self, user_wallet: dict) -> dict | None:
        """
        Takes in a user_wallet dict (with encrypted_mnemonic) and returns
        wallet_address and private_key after decrypting.
        """
        wallet_service = WalletService()
        if not user_wallet:
            return None

        try:
            encrypted_mnemonic = user_wallet.get("encrypted_mnemonic")
            if not encrypted_mnemonic:
                return None

            # Decrypt the mnemonic
            encrypted_mnemonic = user_wallet.encrypted_mnemonic_phrase
            decrypted_mnemonic = wallet_service._decrypt_mnemonic(encrypted_mnemonic)
            # decrypted_mnemonic = self._decrypt_mnemonic(encrypted_mnemonic)

            # Derive private key
            
            private_key = wallet_service.get_private_key_from_mnemonic(decrypted_mnemonic)

            return {
                "wallet_address": user_wallet.get("wallet_address"),
                "private_key": private_key
            }
        except Exception as e:
            # You can add proper logging here
            print(f"Failed to retrieve wallet info: {e}")
            return None