# /imanipay-blockchain-service/main.py
from fastapi import FastAPI
from app.core.startup import create_app
from dotenv import load_dotenv

load_dotenv()

app: FastAPI = create_app()
