"""
File containing all clients to communicate with services
sqlite: database running locally
algod: SDK to interact with the Algorand blockchain
Reddit: API wrapper to communicate with reddit
"""

import os

import praw
from algosdk.v2client import algod
from rich.console import Console
import sqlite3
######################### Initialize sqlite connection #########################
con = sqlite3.connect('tips.db')
cur = con.cursor()

######################### Initialize Algod connection #########################

# Get API key from the environment variables and initialize the client
ALGOD_TOKEN = 'ADD TOKEN HERE'
NETWORK = 'testnet'

algod_address = f"https://{NETWORK}-algorand.api.purestake.io/ps2"

headers = {
    "x-api-key": ALGOD_TOKEN
}

algod = algod.AlgodClient(ALGOD_TOKEN, algod_address, headers)


######################### Initialize Reddit connection #########################

CLIENT_SECRET = 'ADD HERE'
CLIENT_ID = 'ADD HERE'
PASSWORD = 'ADD HERE'
USERNAME = 'ADD HERE
USER_AGENT = 'script'

# Fetches information from the praw.ini file
reddit = praw.Reddit(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            password=PASSWORD,
            username=USERNAME,
            user_agent=USER_AGENT
)

######################### Initialize Rich console #########################

console = Console()
