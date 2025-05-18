# /imanipay-blockchain-service/app/services/transactions.py
import logging
from algosdk.v2client import algod
from algosdk.util import algos_to_microalgos
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

    async def get_balance(self, balance_in: dict) -> dict:
        """Retrieves the balance of a given Algorand wallet address."""
        wallet_address = balance_in.get("wallet_address")
        if not wallet_address:
            raise ValueError("Wallet address is required")
        account_info = self.algod_client.account_info(wallet_address)
        balance = (
            account_info.get("amount", 0) / 1_000_000
        )  # Convert microAlgos to Algos
        assets = account_info.get("assets", [])
        asset_balances = {}
        for asset in assets:
            asset_info = self.algod_client.asset_info(asset["asset-id"])
            if (
                asset_info
                and "params" in asset_info
                and "decimals" in asset_info["params"]
            ):
                decimals = asset_info["params"]["decimals"]
                asset_balances[asset["asset-id"]] = asset["amount"] / (10**decimals)
            else:
                asset_balances[asset["asset-id"]] = asset[
                    "amount"
                ]  # Handle cases where decimals might not be available

        return {
            "wallet_address": wallet_address,
            "balance": balance,
            "assets": asset_balances,
        }

    async def send_payment(
        self,
        payment_in: SendPaymentRequest,
        sender_private_key: str,
        sender_address: str,
    ) -> SendPaymentResponse:
        """
        Allows a user to send Algos or stablecoins (by asset name) to another user,
        charging a fee for stablecoin transfers and checking for sufficient balance.
        """
        algod_client = self.algod_client
        receiver_address = payment_in.receiver_wallet_address
        amount = payment_in.amount
        asset_name = payment_in.asset_name.upper()  # Use name instead of asset_id

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

        txn = None
        fee_txn = None
        signed_txns = []
        actual_payment_amount = amount
        calculated_fee = 0.0

        sender_balance_info = await self.get_balance({"wallet_address": sender_address})

        if asset_id == 0:  # Sending Algos
            scaled_amount = algos_to_microalgos(amount)
            total_cost = scaled_amount + params.fee  # Include transaction fee for Algo
            if sender_balance_info["balance"] * 1_000_000 < total_cost:
                raise ValueError("Insufficient Algo balance")
            txn = PaymentTxn(
                sender=sender_address,
                receiver=receiver_address,
                amt=scaled_amount,
                sp=params,
            )
            signed_txns.append(txn.sign(sender_private_key))
        else:  # Sending a specific asset (stablecoin)
            asset_info = algod_client.asset_info(asset_id)
            if (
                asset_info
                and "params" in asset_info
                and "decimals" in asset_info["params"]
            ):
                decimals = asset_info["params"]["decimals"]
                scaled_amount = int(amount * (10**decimals))
                calculated_fee = self.calculate_transaction_fee(amount)
                scaled_fee = int(calculated_fee * (10**decimals))
                total_cost = scaled_amount + scaled_fee

                sender_asset_balance = sender_balance_info["assets"].get(asset_id, 0)

                if sender_asset_balance < amount + calculated_fee:
                    raise ValueError(f"Insufficient {asset_name} balance")

                print("About to create AssetTransferTxn...")
                txn = AssetTransferTxn(
                    sender=sender_address,
                    receiver=receiver_address,
                    amt=scaled_amount,
                    index=asset_id,
                    sp=params,
                )
                signed_txn = txn.sign(sender_private_key)
                signed_txns = [signed_txn]

                # Create both transactions first (unsigned)
                txn = AssetTransferTxn(
                    sender=sender_address,
                    receiver=receiver_address,
                    amt=scaled_amount,
                    index=asset_id,
                    sp=params,
                )

                if calculated_fee > 0:
                    fee_txn = AssetTransferTxn(
                        sender=sender_address,
                        receiver=self.admin_wallet_address,
                        amt=scaled_fee,
                        index=asset_id,
                        sp=params,
                    )

                    # Assign group ID before signing
                    txgroup = transaction.calculate_group_id([txn, fee_txn])
                    txn.group = txgroup
                    fee_txn.group = txgroup

                    # Now sign both
                    signed_txn = txn.sign(sender_private_key)
                    signed_fee_txn = fee_txn.sign(sender_private_key)

                    signed_txns = [signed_txn, signed_fee_txn]
                # else:
                #     signed_txn = txn.sign(sender_private_key)
                #     signed_txns = [signed_txn]

                else:
                    pass

                if signed_txns:
                    for i, stxn in enumerate(signed_txns):
                        print(f"Signed Transaction object: {stxn}")

        try:
            txid = algod_client.send_transactions(signed_txns)
            logger.info(f"Transaction(s) sent with ID: {txid}")
            pending_txn = transaction.wait_for_confirmation(algod_client, txid, 4)
            logger.info(
                f"Transaction(s) confirmed in round {pending_txn['confirmed-round']}"
            )
            return SendPaymentResponse(
                sender_wallet_address=sender_address,
                receiver_wallet_address=receiver_address,
                amount=amount,
                actual_payment_amount=amount,
                fee_amount=calculated_fee,
                params={
                    "fee": params.fee,
                    "first": params.first,
                    "last": params.last,
                    "ghash": params.gh,
                },
                asset_id=asset_id,
                admin_wallet_address=self.admin_wallet_address,  # Using ImaniPay address as admin for fees
                txid=txid,
            )
        except Exception as e:
            logger.error(f"Error sending transaction(s): {e}")
            raise

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

            wallet_address = user_wallet.get("wallet_address")
            if not wallet_address:
                return None

            # Decrypt the mnemonic
            decrypted_mnemonic = wallet_service._decrypt_mnemonic(encrypted_mnemonic)

            # Derive private key
            private_key = wallet_service.get_private_key_from_mnemonic(
                decrypted_mnemonic
            )

            return {"wallet_address": wallet_address, "private_key": private_key}
        except Exception as e:
            # You can add proper logging here
            print(f"Failed to retrieve wallet info: {e}")
            return None
