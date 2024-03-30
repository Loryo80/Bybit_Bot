from pybit.unified_trading import HTTP
from datetime import datetime
from time import sleep
import pandas as pd
import csv
import schedule
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
import concurrent.futures

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


risk_exposion = 0.2
THRESHOLD = 0.1
mode = 1

# get server time
def get_server_time():
        session = HTTP(testnet=True)
        response = session.get_server_time()
        # Extract the timestamp (in seconds) and convert it to an integer
        timestamp_seconds = int(response['result']['timeSecond'])
        # Convert the timestamp to a datetime object
        time_obj = datetime.utcfromtimestamp(timestamp_seconds)
        # Format the datetime object to display time in hours, minutes, and seconds
        formatted_time = time_obj.strftime('%H:%M:%S')
        return formatted_time
    
# Getting balance on Bybit Derivatrives Asset (in USDT)
def get_balance():
    try:
        # Fetch wallet balance for the unified account
        response = session.get_wallet_balance(accountType="UNIFIED", coin="USDT")
        usdt_info = next((item for item in response['result']['list'][0]['coin'] if item['coin'] == 'USDT'), None)
        if usdt_info:
            balance = usdt_info.get('walletBalance', '0')
            return float(balance)
        else:
            print("USDT information not found.")
            return None
    except Exception as err:
        print("Error:", err)
        return None
    
def get_funding_rate(symbol):
    """
    Fetch the latest funding rate for a given symbol.
    """
    try:
        funding_rate = session.get_funding_rate_history(
            category="linear",
            symbol=symbol,
            limit=1,
        )
        symbol = funding_rate["result"]["list"][0]['symbol']
        funding_rate = funding_rate["result"]["list"][0]['fundingRate']
        funding_rate = 100 * float(funding_rate)
        return symbol, funding_rate
    except Exception as e:
        print(f"Error fetching funding rate for {symbol}: {e}")
        return symbol, None

def find_extreme_funding_rates(symbols):
    """
    Finds the symbols with the highest and lowest funding rates.
    """
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_symbol = {executor.submit(get_funding_rate, symbol): symbol for symbol in symbols}
        highest_rate = -float('inf')
        lowest_rate = float('inf')
        symbol_highest, symbol_lowest = '', ''

        for future in concurrent.futures.as_completed(future_to_symbol):
            symbol, rate = future.result()
            if rate is None:  # Skip if error occurred
                continue
            if rate > highest_rate:
                highest_rate, symbol_highest = rate, symbol
            if rate < lowest_rate:
                lowest_rate, symbol_lowest = rate, symbol

    return symbol_highest, highest_rate, symbol_lowest, lowest_rate

def load_symbols_from_csv(file_path='tickers.csv'):
    """
    Loads symbols from a CSV file.
    """
    symbols = []
    with open(file_path, mode='r') as file:
        reader = csv.reader(file)
        next(reader)  # Skip the header if there is one
        for row in reader:
            symbols.append(row[0])
    return symbols
   
# compare rates to find highest absolute value
def best_funding_rate(symbol_highest, highest_rate, symbol_lowest, lowest_rate):
    """
    Compare the absolute values of the highest and lowest funding rates to find the best rate.
    Return the symbol with the best rate and the rate itself.
    """
    # Compare absolute values of highest and lowest rates
    if abs(highest_rate) > abs(lowest_rate):
        return symbol_highest, highest_rate
    else:
        return symbol_lowest, lowest_rate

# enlever le %
def percent_to_float(percent_str):
    # Remove the '%' sign and convert to float
    return float(percent_str.replace('%', ''))

# get symbol info
def get_symbol_info(symbol):
    """
    Fetches information for the given symbol from the trading session.
    """
    info = session.get_instruments_info(
        category="linear",  # Could be "spot", "option", or "linear"
        symbol=symbol,
    )
    return info

# get market price
def market_price(symbol):  
    mark_price = session.get_tickers(
        category='linear',
        symbol=symbol
    )['result']['list'][0]['markPrice']
    mark_price = float(mark_price)
    return mark_price
  
# calculate quantity to buy/sell
def calculate_amount(capital, market_price):
    if market_price is None:
        print("Market price is None. Cannot calculate amount.")
        return 0  # or handle it in another appropriate way
    amount = capital / market_price
    # amount = round(amount, precision)
    return amount

def calculate_quantity(amount, max_leverage, qty_precision):
    quantity = amount * max_leverage
    quantity = round(quantity, qty_precision)
    return quantity

#calculate TP and SL
def sell_tp_sl_calcul(market_price, capital, max_leverage, funding_rate, feess):
    tafriqa = capital * max_leverage * funding_rate / 100
    print(f"tafriqa : {tafriqa}")
    TP = float(market_price * ((-1 * ((tafriqa + feess) * 100) / (100 * capital * max_leverage)) + 1))
    SL = float(market_price * (((tafriqa - feess) * 100) / (100 * capital * max_leverage) + 1))
    return TP, SL

def buy_tp_sl_calcul(market_price, capital, max_leverage, funding_rate, feess):
    tafriqa = abs(capital * max_leverage * funding_rate / 100)
    print(f"tafriqa : {tafriqa}")
    TP = float(market_price * (((tafriqa + feess) * 100) / (100 * capital * max_leverage) + 1))
    SL = float(market_price * ((-1 * ((tafriqa - feess) * 100) / (100 * capital * max_leverage)) + 1))

    return TP, SL

# Getting number of decimal digits for price and qty
def get_precisions(symbol):
    try:
        resp = session.get_instruments_info(
            category='linear',
            symbol=symbol
        )['result']['list'][0]
        price_precision = len(str(resp['priceFilter']['tickSize']).split('.')[-1]) if '.' in str(resp['priceFilter']['tickSize']) else 0
        qty_precision = len(str(resp['lotSizeFilter']['qtyStep']).split('.')[-1]) if '.' in str(resp['lotSizeFilter']['qtyStep']) else 0

        return price_precision, qty_precision
    except Exception as err:
        print(err)
        return 0, 0  # Default return in case of an error

# Placing order with Market price. Placing TP and SL as well
def place_market_order(symbol, side, capital, max_leverage, best_rate):
    price_precision, qty_precision = get_precisions(symbol)
    mark_price = float(market_price(symbol))
    amount = float(calculate_amount(capital, mark_price))
    order_qty = calculate_quantity(amount, max_leverage, qty_precision)
    feess = max_leverage * capital * 0.02 / 100
    
    print(f'Placing {side} order for {symbol} at Mark price: {mark_price}')
    print(f"Order quantity: {order_qty}")
    print("feess: ", feess)
    # order_qty = round(qty/mark_price, qty_precision) => calculate the quantity without max_levrage
    sleep(2)
    if side == 'buy':
        TP, SL = buy_tp_sl_calcul(mark_price, capital, max_leverage, best_rate, feess)
        tp_price = round(TP, price_precision)
        sl_price = round(SL, price_precision)
        print(f"TakeProfit price : {tp_price}")
        print(f"StopLoss price : {sl_price}")
        try:
            response = session.place_order(
                category='linear',
                symbol=symbol,
                side='Buy',
                orderType='Market',
                qty=order_qty,
                takeProfit=tp_price,
                stopLoss=sl_price,
                tpTriggerBy='Market',
                slTriggerBy='Market'
            )
            
            # Check if the response is successful
            if response['ret_code'] == 0:  # Assuming '0' is a successful code
                order_details = {
                    "orderId": response['result']['order_id'],
                    "symbol": response['result']['symbol'],
                    "side": response['result']['side'],
                    "entryPrice": float(response['result']['price']),
                    "quantity": float(response['result']['qty']),
                    "filledQuantity": float(response['result']['cum_exec_qty']),
                    "status": response['result']['order_status'],
                    "fees": float(response['result'].get('exec_fee', '0')),    
                    # Assuming take profit and stop loss are set in the same response
                    # If TP and SL are not available in this response, they may need to be fetched separately or managed differently
                    # "takeProfit": "Not Provided",
                    # "stopLoss": "Not Provided",
                }
                print(f"Order placed successfully: {order_details}")
                return order_details
            else:
                print(f"Order placement failed with code {response['ret_code']}: {response['ret_msg']}")
                return None
        except Exception as e:
            print(f"An exception occurred while placing the order: {str(e)}")
            return None
    

    if side == 'sell':
        TP, SL = sell_tp_sl_calcul(mark_price, capital, max_leverage, best_rate, feess)
        sl_price = round(SL, price_precision)
        tp_price = round(TP, price_precision)
        print(f"TakeProfit price : {tp_price}")
        print(f"StopLoss price : {sl_price}")
        try:
            resp = session.place_order(
                category='linear',
                symbol=symbol,
                side='Sell',
                orderType='Market',
                qty=order_qty,
                takeProfit=tp_price,
                stopLoss=sl_price,
                tpTriggerBy='Market',
                slTriggerBy='Market'
            )
            # Check if the response is successful
            if response['ret_code'] == 0:  # Assuming '0' is a successful code
                order_details = {
                    "orderId": response['result']['order_id'],
                    "symbol": response['result']['symbol'],
                    "side": response['result']['side'],
                    "entryPrice": float(response['result']['price']),
                    "quantity": float(response['result']['qty']),
                    "filledQuantity": float(response['result']['cum_exec_qty']),
                    "status": response['result']['order_status'],
                    "fees": float(response['result'].get('exec_fee', '0')),    
                    # Assuming take profit and stop loss are set in the same response
                    # If TP and SL are not available in this response, they may need to be fetched separately or managed differently
                    # "takeProfit": "Not Provided",
                    # "stopLoss": "Not Provided",
                }
                print(f"Order placed successfully: {order_details}")
                return order_details
            else:
                print(f"Order placement failed with code {response['ret_code']}: {response['ret_msg']}")
                return None
        except Exception as e:
            print(f"An exception occurred while placing the order: {str(e)}")
            return None
            

            

def job():
    server_time = get_server_time()
    print(server_time)
    start_time = datetime.now()
    usdt_balance = get_balance()
    print('------------------  Let''s print money with Bybit Fundrate Bot  ------------------')
    print('Initial Balance is : ', usdt_balance)
    print('---------------------------------------------------------------------------')
    """Scheduled job to perform trading actions based on funding rates."""
    # symbol_highest, highest_rate, symbol_lowest, lowest_rate = find_extreme_funding_rates()
    # print(f"highest funding rate  {highest_rate}  symbol is {symbol_highest}")
    # print(f"lowest funding rate {lowest_rate} symbol is {symbol_lowest}")
    
    symbols = load_symbols_from_csv()
    symbol_highest, highest_rate, symbol_lowest, lowest_rate = find_extreme_funding_rates(symbols)
    highest_rate = float(highest_rate)
    lowest_rate = float(lowest_rate)
    print(f"Highest: {symbol_highest} with rate {highest_rate}")
    print(f"Lowest: {symbol_lowest} with rate {lowest_rate}")
          
    best_symbol, best_rate = best_funding_rate(symbol_highest, highest_rate, symbol_lowest, lowest_rate)
    
    print(f"the symbol {best_symbol} has the best funding rate {best_rate}.")

    # capital = usdt_balance * risk_exposion
    capital = 1000


    if best_rate >THRESHOLD:
        symbol = best_symbol
        order_side = "sell"  
        instrument_info = get_symbol_info(symbol)['result']['list'][0]
        max_leverage = int(float(instrument_info["leverageFilter"]["maxLeverage"]))
        print("maximum leverage :",max_leverage)
        rate = float(best_rate)
        order_details = place_market_order(symbol, order_side, capital, max_leverage, rate)
        
        
    if best_rate < -THRESHOLD:
        symbol = best_symbol
        order_side = "buy"
        instrument_info = get_symbol_info(symbol)['result']['list'][0]
        max_leverage = int(float(instrument_info["leverageFilter"]["maxLeverage"]))
        print("maximum leverage :",max_leverage)
        rate = float(best_rate)
        order_details = place_market_order(symbol, order_side, capital, max_leverage, rate)


    end_time = datetime.now()  # Record end time of the job
    execution_time = end_time - start_time  # Calculate duration
    print(f"Job execution time: {execution_time}")

if __name__ == "__main__":
    schedule.every().day.at("15:31:00").do(job)
    # schedule.every().day.at("22:54:00").do(job)
    # schedule.every().day.at("22:55:00").do(job)

    while True:
        schedule.run_pending()
        time.sleep(1)
