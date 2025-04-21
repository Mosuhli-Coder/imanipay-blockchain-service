# /imanipay-blockchain-service/app/core/config.py
import os
from dotenv import load_dotenv
from pathlib import Path

# Load the .env from root project directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent
dotenv_path = BASE_DIR / ".env"

# print(f"Loading .env file from: {dotenv_path}")
load_dotenv(dotenv_path=dotenv_path)

# Print raw env for debugging
# print("ALGORAND_NODE_URL from raw os.environ:", os.environ.get("ALGORAND_NODE_URL"))

class Settings:
    PROJECT_NAME: str = "ImaniPay Blockchain Service"
    ALGORAND_NODE_URL: str = os.getenv("ALGORAND_NODE_URL")
    ALGORAND_API_KEY: str = os.getenv("ALGORAND_API_KEY")
    ALGORAND_NETWORK: str = os.getenv("ALGORAND_NETWORK", "testnet")
    IMANIPAY_WALLET_ADDRESS: str = os.getenv("IMANIPAY_WALLET_ADDRESS")
    DEPLOYER_MNEMONIC_KEY: str = os.getenv("DEPLOYER_MNEMONIC_KEY")
    # IMANIPAY_WALLET_PRIVATE_KEY: str = os.getenv("IMANIPAY_WALLET_PRIVATE_KEY")

    # def print_debug(self):
    #     print("Debugging Settings:")
    #     print("ALGORAND_NODE_URL:", self.ALGORAND_NODE_URL)
    #     print("ALGORAND_API_KEY:", self.ALGORAND_API_KEY)
    #     print("ALGORAND_NETWORK:", self.ALGORAND_NETWORK)
    #     print("IMANIPAY_WALLET_ADDRESS:", self.IMANIPAY_WALLET_ADDRESS)

    #     print("PROJECT_NAME:", self.PROJECT_NAME)

    def validate(self):
        if not self.ALGORAND_NODE_URL:
            raise ValueError("ALGORAND_NODE_URL is not set. Please set it in your .env file.")

settings = Settings()
settings.validate()
# settings.print_debug()
