from pybit.unified_trading import HTTP
import csv
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Access the API key
api_key = os.getenv('Bybit_API_Key')
api_secret = os.getenv('Bybit_API_Secret')

# initait session
session = HTTP(
    api_key=api_key,
    api_secret=api_secret
)

##  Getting all available symbols from Derivatives market (like 'BTCUSDT', 'XRPUSDT', etc)

def get_tickers():
    try:
        # Assuming session.get_tickers() correctly fetches your data
        resp = session.get_tickers(category="linear")['result']['list']
        symbols = []
        for elem in resp:
            if 'USDT' in elem['symbol'] and 'USDC' not in elem['symbol']:
                symbols.append(elem['symbol'])

        # Writing symbols to a CSV file
        with open('tickers.csv', mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Symbol'])  # Writing header
            for symbol in symbols:
                writer.writerow([symbol])  # Writing each symbol

        return symbols
    except Exception as err:
        print(err)
    
get_tickers()

