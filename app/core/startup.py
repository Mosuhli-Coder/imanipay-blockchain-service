# /imanipay-blockchain-service/app/core/startup.py
from fastapi import FastAPI
from app.core.config import settings
from app.api import wallets, transactions # escrow , mobile_money

def create_app() -> FastAPI:
    app = FastAPI(title=settings.PROJECT_NAME)
    app.include_router(wallets.router)    

    app.include_router(transactions.router)
    # app.include_router(escrow.router)
    # app.include_router(mobile_money.router)
    
    return app

app = create_app()