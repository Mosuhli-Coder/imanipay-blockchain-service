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
    async def get_balance(self, balance_request: BalanceRequest) -> BalanceResponse:
        """Retrieves the balance of a given Algorand wallet address directly from the blockchain."""
        wallet_address = balance_request.wallet_address
        try:
            account_info = self.algod_client.account_info(wallet_address)
            balances: Dict[int, float] = {0: account_info.get("amount", 0) / 1_000_000}

            for asset in account_info.get("assets", []):
                if "asset-id" in asset:
                    asset_id = asset["asset-id"]
                    asset_info = self.algod_client.asset_info(asset_id)
                    decimals = asset_info.get("params", {}).get("decimals", 0)
                    balances[asset_id] = asset.get("amount", 0) / (10 ** decimals)

            return BalanceResponse(wallet_address=wallet_address, balances=balances)
        except Exception as e:
            raise Exception(f"Failed to get balance for address '{wallet_address}': {e}")

    async def validate_wallet(self, validate_request: ValidateWalletRequest) -> ValidateWalletResponse:
        """
        Validates if a given Algorand wallet address is valid and exists on the blockchain.
        """
        print(f"Validating wallet address: {validate_request.wallet_address}")  # Log the wallet address for debugging
        print(f"Validating wallet address: {settings.ALGORAND_NODE_URL}")  # Log the wallet address for debugging
        wallet_address = validate_request.wallet_address
        try:
            account_info = self.algod_client.account_info(wallet_address)
            print(f"Account info for {wallet_address}: {account_info}")  # Log the account info for debugging
            # If the account_info is successfully fetched, the address exists.
            return ValidateWalletResponse(is_valid=True, wallet_address=wallet_address)
        except Exception as e:
            # Handle exceptions, specifically catching the case where the account doesn't exist.
            # The Algorand SDK might raise a specific error for non-existent accounts.  Check the SDK docs.
            if "account " in str(e) and "not found" in str(e): # Example: Check for a substring in the error message.
                return ValidateWalletResponse(is_valid=False, wallet_address=wallet_address)
            else:
                # For other errors (e.g., network issues), you might want to log them or raise an exception.
                print(f"Error validating wallet address: {e}") # Log the error
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
        print("User Address:", user_address)

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