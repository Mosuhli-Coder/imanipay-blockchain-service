# ImaniPay Blockchain Service

## Description

The ImaniPay Blockchain Service is a Python-based API built using FastAPI, designed to facilitate secure and efficient interactions with the Algorand blockchain. This service is a crucial component of the ImaniPay platform, focusing on handling blockchain-related operations such as wallet management, balance inquiries, and transaction processing. It is designed to be consumed by a separate backend API, which manages the core application logic and user data.

## Features

* **Wallet Balance:** Retrieves the ALGO and ASA (Algorand Standard Asset) balances for a given wallet address.
* **Transaction Handling:** Supports sending payments (ALGO and ASAs) between Algorand wallets.
* **Escrow Management:** Implements escrow functionality using Algorand smart contracts, allowing for secure and conditional transactions.
* **Wallet Validation:** Validates the format and existence of an Algorand wallet address on the blockchain.
* **Wallet Creation:** Creates a new Algorand wallet address (for development purposes only).

## Architecture

The service follows a modular architecture, organized as follows:

imanipay-blockchain-service├── app│   ├── api             # FastAPI route endpoints│   │   ├── wallets.py│   │   ├── transactions.py│   │   └── escrow.py│   ├── core            # Core config and startup│   │   ├── config.py│   │   └── startup.py│   ├── contracts       # Smart contract logic and helpers│   │   ├── escrow.py│   │   └── helpers.py│   ├── services        # Business logic for blockchain interactions│   │   ├── wallets.py│   │   ├── transactions.py│   │   └── escrow.py│   ├── schemas         # Pydantic schemas for request and response data│   │   ├── init.py│   │   ├── ...│   └── utils             # Utility functions (if needed)├── main.py             # FastAPI application entry point├── Dockerfile          # (Optional) Docker configuration├── requirements.txt    # Project dependencies└── .env                # Environment variable configuration
## Prerequisites

Before setting up the project, ensure you have the following installed:

* Python 3.8+
* pip (Python package manager)
* An Algorand node URL and API key (for interacting with the Algorand network)

## Setup Instructions

1.  **Clone the Repository:**

    ```bash
    git clone <repository_url>
    cd imanipay-blockchain-service
    ```

2.  **Create a Virtual Environment (Recommended):**

    ```bash
    python -m venv venv
    source venv/bin/activate # On macOS/Linux
    venv\Scripts\activate # On Windows
    ```

3.  **Install Dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**

    * Create a `.env` file in the project root directory.
    * Add the following environment variables, replacing the placeholders with your actual values:

        ```
        ALGORAND_NODE_URL="YOUR_ALGORAND_NODE_URL"
        ALGORAND_API_KEY="YOUR_ALGORAND_API_KEY"
        ALGORAND_NETWORK="testnet" # or "mainnet"
        # Optionally, for escrow contract deployment:
        DEPLOYER_PRIVATE_KEY="YOUR_DEPLOYER_PRIVATE_KEY"
        # Main Backend API URL:
        MAIN_BACKEND_API_URL="YOUR_MAIN_BACKEND_API_URL" # Add this!
        ```

5.  **Run the Application:**

    ```bash
    uvicorn main:app --reload
    ```

    The `--reload` flag enables hot reloading, which automatically restarts the server when you make changes to the code.

## API Endpoints

The application exposes the following API endpoints:

### Wallets

* `POST /wallets/balance`
    * Retrieves the ALGO and ASA balances for a given wallet address.
    * Request:

        ```json
        {
            "wallet_address": "string"
        }
        ```
    * Response:

        ```json
        {
            "wallet_address": "string",
            "balances": {
                "0": number, # ALGO balance
                "ASA_ID_1": number, # ASA balance (if any)
                "...": number
            }
        }
        ```
* `POST /wallets/validate`
    * Validates if a given Algorand wallet address is valid and exists on the blockchain
    * Request:

        ```json
        {
            "wallet_address": "string"
        }
        ```
    * Response:

        ```json
        {
            "is_valid": true/false,
            "wallet_address": "string"
        }
        ```
* `POST /wallets/create`
    * Creates a new Algorand wallet.  For DEVELOPMENT PURPOSES ONLY.
    * Request:
        ```json
        {}
        ```
    * Response:
        ```json
        {
            "wallet_address": "string",
            "private_key": "string"
        }
        ```

### Transactions

* `POST /transactions/send`
    * Calculates the transaction details for sending a payment (ALGO or ASA) from one Algorand wallet to another, including fees.
    * Request:

        ```json
        {
            "sender_wallet_address": "string",
            "receiver_wallet_address": "string",
            "amount": number,
            "asset_id": number (default: 0 for ALGO)
        }
        ```
    * Response:

        ```json
        {
            "sender_wallet_address": "string",
            "receiver_wallet_address": "string",
            "amount": number,
            "actual_payment_amount": number,
            "fee_amount": number,
            "params": {
                "fee": number,
                "first": number,
                "last": number,
                "ghash": "string",
                "genesisID": "string",
                "genesisHash": "string"
            },
            "asset_id": number,
            "admin_wallet_address": "string"
        }
        ```

### Escrow

* `POST /escrow/create`
    * Creates a new escrow contract.
    * Request:

        ```json
        {
            "seller_wallet_address": "string",
            "buyer_wallet_address": "string",
            "payment_amount": number,
            "asset_id": number,
            "timeout": number (Unix timestamp)
        }
        ```
    * Response:

        ```json
        {
            "app_id": number,
            "transaction_id": "string"
        }
        ```

* `POST /escrow/{escrow_id}/release`
    * Releases funds from an escrow contract.
    * Request:

        ```json
        {
            "release_address": "string"
        }
        ```
    * Response:

        ```json
        {
            "app_id": number,
            "transaction_id": "string"
        }
        ```

## Important Notes

* **Security:** This service is designed to be consumed by your Main Backend API, not directly by the UI. The Main Backend API is responsible for secure storage of private keys and user authentication/authorization. This service assumes that the Main Backend API provides valid and authorized wallet addresses for transactions.
* **Error Handling:** The API includes error handling, but your Main Backend API should also implement robust error handling and logging to manage potential issues with blockchain interactions.
* **Asynchronous Operations:** The API uses `async` and `await` for non-blocking I/O operations, which is crucial for efficient blockchain communication.
* **Smart Contract Deployment:** The escrow functionality requires a pre-deployed Algorand smart contract. The application will attempt to deploy it if `DEPLOYER_PRIVATE_KEY` is provided, but in a production environment, you would typically deploy the contract separately and configure the application with the contract's application ID.
* **Main Backend Integration:** This service is designed to work in conjunction with a separate backend API. The Main Backend API is responsible for managing user data, authenticating requests, and calling the endpoints of this service to perform blockchain operations. The `MAIN_BACKEND_API_URL` variable in the `.env` file must be set to the correct URL of your Main Backend API.
* **Wallet Connect:** This service does not handle wallet connection. The Main Backend API is responsible for associating user IDs with wallet addresses, and should call the `/wallets/validate` endpoint to validate the address.
* **Wallet Creation:** The `/wallets/create` endpoint is for development and testing purposes ONLY.  Do NOT use it in a production environment.  Private key management should be handled securely by the Main Backend API.

## Docker (Optional)

A `Dockerfile` is provided for containerizing the application. You can build and run the Docker image using the following commands:

```bash
docker build -t imanipay-blockchain-service .
docker run -p 8000:8000 imanipay-blockchain-service
ContributingContributions