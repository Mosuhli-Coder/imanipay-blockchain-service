# /imanipay-blockchain-service/app/services/wallets.py
from algosdk import account, mnemonic
from algosdk.v2client import algod
from app.core.config import settings
from app.schemas import WalletResponse, BalanceResponse, BalanceRequest, ValidateWalletRequest, ValidateWalletResponse # Import the new schema
from typing import Dict

headers = {
    "X-API-Key": settings.ALGORAND_API_KEY
}

class WalletService:
    def __init__(self):
        self.algod_client = algod.AlgodClient(settings.ALGORAND_API_KEY, settings.ALGORAND_NODE_URL, headers=headers)

    async def get_balance(self, balance_request: BalanceRequest) -> BalanceResponse:
        """Retrieves the balance of a given Algorand wallet address directly from the blockchain."""
        wallet_address = balance_request.wallet_address
        try:
            account_info = self.algod_client.account_info(wallet_address)
            balances: Dict[int, float] = {0: account_info.get("amount", 0) / 1_000_000}

            for asset in account_info.get("assets", []):
                if "asset-id" in asset:
                    asset_id = asset["asset-id"]
                    asset_info = await self.algod_client.asset_info(asset_id).do()
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

    async def create_wallet(self) -> WalletResponse:
        """Creates a new Algorand wallet and returns the address and private key.  For development only."""
        # private_key, address = account.generate_account()
        # IMPORTANT:  In a real application, you would NEVER return the private key directly.
        # This is ONLY for development and testing.  You would typically store the private key
        # securely and associate it with a user in your main backend's database.
        private_key, address = account.generate_account()
        mnemonic_phrase = mnemonic.from_private_key(private_key)

        print("Address:", address)
        print("Private Key:", private_key)
        print("Mnemonic:", mnemonic_phrase)  # This is the one you must save securely.
        return WalletResponse(wallet_address=address, private_key=private_key, user_id="cm9mmryqn0000iiacyvegcftm") # Include private_key in the response

