# /imanipay-blockchain-service/app/services/wallets.py
from algosdk import account, mnemonic
from algosdk.v2client import algod
from algosdk.transaction import  PaymentTxn, AssetTransferTxn, assign_group_id
from app.core.config import settings
from app.schemas import WalletResponse, BalanceResponse, BalanceRequest, ValidateWalletRequest, ValidateWalletResponse # Import the new schema
from typing import Dict
from cryptography.fernet import Fernet

headers = {
    "X-API-Key": settings.ALGORAND_API_KEY
}

class WalletService:
    def __init__(self, network: str = "testnet"):
        self.algod_client = algod.AlgodClient(
            settings.ALGORAND_API_KEY,
            settings.ALGORAND_NODE_URL,
            headers={"X-API-Key": settings.ALGORAND_API_KEY}
        )

        self.usdc_asset_id = int(settings.USDC_ASSET_ID)  # assumes it's a string in .env

        if not settings.FUNDER_MNEMONIC_KEY:
            raise ValueError("FUNDER_MNEMONIC environment variable is not set")
        
        self.funder_address = settings.IMANIPAY_WALLET_ADDRESS
        if not self.funder_address:
            raise ValueError("IMANIPAY_WALLET_ADDRESS environment variable is not set")

        self.network = network
        self.funder_mnemonic = settings.FUNDER_MNEMONIC_KEY
        self.fernet_key = settings.FERNET_KEY
        # self.fernet_key = "gVFGVJAqMGQxAXoPWiHIvEAaZlwjTU6qWo2itZqdLtc="

    def get_private_key_from_mnemonic(self, stored_mnemonic: str) -> str:
        """
        Derives the private key from a mnemonic phrase.
        """
        private_key = mnemonic.to_private_key(stored_mnemonic)
        return private_key

    def _encrypt_mnemonic(self, mnemonic_phrase: str) -> str:
        key = self.fernet_key
        print(f"FERNET_KEY: {key}")  # Log the key for debugging
        print(f"FERNET_KEY: {self.fernet_key}")
        if not key:
            raise ValueError("FERNET_KEY is not set in environment variables")
        fernet = Fernet(key.encode())
        encrypted = fernet.encrypt(mnemonic_phrase.encode())
        return encrypted.decode()

    def _decrypt_mnemonic(self, encrypted_mnemonic: str) -> str:
        key = self.fernet_key
        if not key:
            raise ValueError("FERNET_KEY is not set in environment variables")
        fernet = Fernet(key.encode())
        decrypted = fernet.decrypt(encrypted_mnemonic.encode())
        return decrypted.decode()


    async def wait_for_confirmation(self, txid):
        while True:
            tx_info = await self.algod_client.pending_transaction_info(txid)
            if tx_info.get("confirmed-round", 0) > 0:
                break
    async def get_balance(self, balance_in: dict) -> dict:
        """Retrieves the balance of a given Algorand wallet address with asset names."""
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
            asset_id = asset["asset-id"]
            asset_info = self.algod_client.asset_info(asset_id)
            if asset_info and "params" in asset_info:
                params = asset_info["params"]
                decimals = params.get("decimals", 0)
                name = params.get("name", f"Asset {asset_id}")
                scaled_balance = asset["amount"] / (10**decimals)
                asset_balances[asset_id] = {"balance": scaled_balance, "name": name}
            else:
                asset_balances[asset_id] = {"balance": asset["amount"], "name": f"Asset {asset_id}"}

        return {
            "wallet_address": wallet_address,
            "balance": balance,
            "assets": asset_balances,
        }
    async def validate_wallet(self, validate_request: ValidateWalletRequest) -> ValidateWalletResponse:
        """
        Validates if a given Algorand wallet address is valid and exists on the blockchain.
        """
        wallet_address = validate_request.wallet_address
        try:
            account_info = self.algod_client.account_info(wallet_address)
            # If the account_info is successfully fetched, the address exists.
            return ValidateWalletResponse(is_valid=True, wallet_address=wallet_address)
        except Exception as e:
            # Handle exceptions, specifically catching the case where the account doesn't exist.
            # The Algorand SDK might raise a specific error for non-existent accounts.  Check the SDK docs.
            if "account " in str(e) and "not found" in str(e): # Example: Check for a substring in the error message.
                return ValidateWalletResponse(is_valid=False, wallet_address=wallet_address)
            else:
                # For other errors (e.g., network issues), you might want to log them or raise an exception.
                return ValidateWalletResponse(is_valid=False, wallet_address=wallet_address) #Consider if you want to raise
                # raise Exception(f"Error validating wallet address: {e}") # Or raise.

    async def generate_and_opt_in_wallet(self, user_id: str) -> dict:
        """
        Generates a new Algorand wallet for a user, opts it into USDC, and funds it from the funder's wallet.
        """
        # Check if the user_id is valid (e.g., exists in your database)
        if not user_id:
            raise ValueError("Invalid user ID provided.")

        # Step 1: Generate new wallet for user
        user_private_key, user_address = account.generate_account()
        user_mnemonic_phrase = mnemonic.from_private_key(user_private_key)

        try:
            # Step 2: Derive funder's private key
            funder_private_key = self.get_private_key_from_mnemonic(self.funder_mnemonic)

            # Step 3: Get transaction parameters
            params = self.algod_client.suggested_params()

            # Step 4: Create funding transaction
            min_balance = 300_000  # 0.3 ALGO
            funding_txn = PaymentTxn(
                sender=self.funder_address,
                receiver=user_address,
                amt=min_balance,
                sp=params
            )

            # Step 5: Create opt-in transaction (0 amount transfer to self)
            opt_in_txn = AssetTransferTxn(
                sender=user_address,
                receiver=user_address,
                amt=0,
                index=self.usdc_asset_id,
                sp=params
            )

            # Step 6: Assign group ID to both transactions
            group = [funding_txn, opt_in_txn]
            assign_group_id(group)
            funding_txn, opt_in_txn = group  # update transactions with group ID

            # Step 7: Sign transactions
            signed_funding_txn = funding_txn.sign(funder_private_key)
            signed_optin_txn = opt_in_txn.sign(user_private_key)  # ✅ user signs their txn

            # Step 8: Send group
            txid = self.algod_client.send_transactions([signed_funding_txn, signed_optin_txn])

            print(f"Transactions sent with ID: {txid}")

            # Step 9: Wait for confirmation
            self.algod_client.pending_transaction_info(txid)
            encrypted = self._encrypt_mnemonic(user_mnemonic_phrase)

            return {
                "user_id": user_id,
                "wallet_address": user_address,
                "opted_in_usdc": True,
                "network": self.network,
                "encrypted_mnemonic_phrase": encrypted,
            }

        except Exception as e:
            print(f"Error generating and opting-in wallet for user {user_id}: {e}")
            return {
                "user_id": user_id,
                "wallet_address": None,
                "opted_in_usdc": False,
                "network": self.network,
                "mnemonic_phrase": None,
                "error": str(e),
            }