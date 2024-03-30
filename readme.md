Based on your script, here's a comprehensive README that you might consider for your project:

---

# Bybit Unified Trading Bot

This trading bot is designed to automate trading actions on the Bybit exchange, specifically focusing on exploiting funding rate discrepancies across different cryptocurrency contracts. It employs the `pybit.unified_trading` API to interact with the Bybit exchange, fetching real-time funding rates, server time, and account balances, and placing trades based on calculated metrics.

## Features

- Fetches real-time server time from Bybit.
- Retrieves account balance in USDT (Tether).
- Determines the latest funding rates for specified symbols.
- Identifies symbols with the highest and lowest funding rates.
- Places market orders with calculated quantities, including setting take profit (TP) and stop loss (SL) levels.
- Schedules trading actions to execute at specific times each day.

## Requirements

- Python 3.6 or higher.
- `pybit` - For interacting with Bybit's API.
- `pandas` - For data manipulation and analysis.
- `python-dotenv` - For loading environment variables from a `.env` file.
- `concurrent.futures` - For parallel execution of tasks.
- A `.env` file containing your Bybit API key and secret.

## Installation

1. Clone this repository to your local machine.
2. Install required Python packages:

```bash
pip install pybit pandas python-dotenv
```

3. Create a `.env` file in the root directory of the project, and add your Bybit API key and secret as follows:

```plaintext
Bybit_API_Key=your_api_key_here
Bybit_API_Secret=your_api_secret_here
```

## Usage

1. Ensure your `.env` file with API credentials is set up.
2. Run the script:

```bash
python <script_name>.py
```

3. The bot will start and follow the scheduled times for executing the trading strategy.

## Strategy Overview

- The bot calculates the risk exposure based on a predefined threshold and the account balance.
- It fetches the current funding rates for symbols listed in a specified CSV file.
- Based on the funding rates, it identifies the symbols with the most extreme rates (highest and lowest).
- Orders are placed on the symbol with the best (highest absolute value) funding rate, considering risk management by setting TP and SL levels.
- The bot is scheduled to run these checks and trades at specific times daily.

## Contributions

Contributions are welcome. Please open an issue or pull request if you have suggestions or improvements.

## Disclaimer

This trading bot is provided as-is, and it comes with no guarantees or warranties. Trading cryptocurrencies carries a high level of risk, and you should only trade with money you can afford to lose. The developers are not responsible for any trading losses incurred using this software.

