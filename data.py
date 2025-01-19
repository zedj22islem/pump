import requests
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Binance API endpoint for klines (candlestick data)
BINANCE_API_URL = "https://api.binance.com/api/v3/klines"

# Function to format numbers (e.g., 1000 -> 1k)
def format_number(number: float) -> str:
    if number >= 1_000_000:
        return f"{number / 1_000_000:.2f}M"
    elif number >= 1_000:
        return f"{number / 1_000:.1f}k"
    else:
        return f"{number:.2f}"

# Function to fetch candle data for a specific symbol, interval, and timestamp
def fetch_candle_data(symbol: str, interval: str, timestamp: int):
    params = {
        "symbol": symbol,
        "interval": interval,
        "startTime": timestamp,  # Fetch the candle starting at the specified timestamp
        "limit": 1  # Fetch only one candle
    }
    response = requests.get(BINANCE_API_URL, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Error fetching data: {response.status_code} - {response.text}")

# Function to parse and format candle data
def format_candle_data(candle_data, symbol: str):
    # Extract candle data
    candle = candle_data[0]
    open_time = datetime.fromtimestamp(candle[0] / 1000).strftime('%Y-%m-%d %H:%M:%S')
    open_price = float(candle[1])
    high_price = float(candle[2])
    low_price = float(candle[3])
    close_price = float(candle[4])
    volume = float(candle[5])
    close_time = datetime.fromtimestamp(candle[6] / 1000).strftime('%Y-%m-%d %H:%M:%S')
    quote_asset_volume = float(candle[7])
    num_trades = int(candle[8])
    taker_buy_base_volume = float(candle[9])  # Amount bought (in base asset, e.g., SAGA)
    taker_buy_quote_volume = float(candle[10])  # Amount bought (in quote asset, e.g., USDT)

    # Calculate amount sold
    amount_sold_base = volume - taker_buy_base_volume  # Amount sold (in base asset)
    amount_sold_quote = quote_asset_volume - taker_buy_quote_volume  # Amount sold (in quote asset)

    # Determine the side (buyer or seller dominated)
    if taker_buy_base_volume > amount_sold_base:
        side = "Buyers dominated 🟢"
    else:
        side = "Sellers dominated 🔴"

    # Calculate price change
    price_change = close_price - open_price
    price_change_percent = (price_change / open_price) * 100 if open_price != 0 else 0

    # Determine if the price change is positive or negative
    if price_change > 0:
        price_change_str = f"+{price_change:.2f} (+{price_change_percent:.2f}%) 🟢"
    elif price_change < 0:
        price_change_str = f"{price_change:.2f} ({price_change_percent:.2f}%) 🔴"
    else:
        price_change_str = "0.00 (0.00%)"

    # Format the candle data into a readable string
    candle_info = (
        f"📊 *Candle Data for {symbol}*\n"
        f"⏰ Open Time: `{open_time}`\n"
        f"🟢 Open Price: `{open_price}`\n"
        f"🔴 Close Price: `{close_price}`\n"
        f"🔼 High Price: `{high_price}`\n"
        f"🔽 Low Price: `{low_price}`\n"
        f"📈 Volume: `{format_number(volume)}`\n"
        f"💹 USDT Volume: `{format_number(quote_asset_volume)}`\n"
        f"🔢 Number of Trades: `{num_trades}`\n"
        f"💰 Amount Bought ({symbol}): `{format_number(taker_buy_base_volume)}`\n"
        f"💰 Amount Bought (USDT): `{format_number(taker_buy_quote_volume)}`\n"
        f"💸 Amount Sold ({symbol}): `{format_number(amount_sold_base)}`\n"
        f"💸 Amount Sold (USDT): `{format_number(amount_sold_quote)}`\n"
        f"📉 Price Change: `{price_change_str}`\n"
        f"⚖️ Side: `{side}`\n"
    )
    return candle_info

# Command handler for the /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome! Use the /candle command to get candle data. "
        "Example: /candle SAGAUSDT 3m 2025-01-15 15:03:00"
    )

# Command handler for the /candle command
async def candle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Extract arguments from the command
        args = context.args
        if len(args) < 3:
            await update.message.reply_text(
                "Please provide the symbol, interval, and timestamp. "
                "Example: /candle SAGAUSDT 3m 2025-01-15 15:03:00"
            )
            return

        symbol = args[0].upper()  # Trading pair (e.g., SAGAUSDT)
        interval = args[1]  # Candle interval (e.g., 3m, 15m)
        timestamp_str = " ".join(args[2:])  # Timestamp (e.g., 2025-01-15 15:03:00)

        # Convert the timestamp to a Unix timestamp in milliseconds
        timestamp = int(datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S").timestamp() * 1000)

        # Fetch the candle data
        candle_data = fetch_candle_data(symbol, interval, timestamp)

        # Format and send the candle data
        candle_info = format_candle_data(candle_data, symbol)
        await update.message.reply_text(candle_info, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"An error occurred: {e}")

# Main function to start the bot
def main():
    # Replace 'YOUR_TELEGRAM_BOT_TOKEN' with your actual bot token
    application = Application.builder().token("7782535176:AAF60Jjv5trbmSAqScYEORhmNfuAEoqotuA").build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("candle", candle))

    # Start the bot
    application.run_polling()

if __name__ == "__main__":
    main()

'''
import requests
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Binance API endpoint for klines (candlestick data)
BINANCE_API_URL = "https://api.binance.com/api/v3/klines"

# Function to format numbers (e.g., 1000 -> 1k)
def format_number(number: float) -> str:
    if number >= 1_000_000:
        return f"{number / 1_000_000:.2f}M"
    elif number >= 1_000:
        return f"{number / 1_000:.1f}k"
    else:
        return f"{number:.2f}"

# Function to fetch candle data for a specific symbol, interval, and timestamp
def fetch_candle_data(symbol: str, interval: str, timestamp: int):
    params = {
        "symbol": symbol,
        "interval": interval,
        "startTime": timestamp,  # Fetch the candle starting at the specified timestamp
        "limit": 1  # Fetch only one candle
    }
    response = requests.get(BINANCE_API_URL, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Error fetching data: {response.status_code} - {response.text}")

# Function to parse and format candle data
def format_candle_data(candle_data, symbol: str):
    # Extract candle data
    candle = candle_data[0]
    open_time = datetime.fromtimestamp(candle[0] / 1000).strftime('%Y-%m-%d %H:%M:%S')
    open_price = float(candle[1])
    high_price = float(candle[2])
    low_price = float(candle[3])
    close_price = float(candle[4])
    volume = float(candle[5])
    close_time = datetime.fromtimestamp(candle[6] / 1000).strftime('%Y-%m-%d %H:%M:%S')
    quote_asset_volume = float(candle[7])
    num_trades = int(candle[8])
    taker_buy_base_volume = float(candle[9])  # Amount bought (in base asset, e.g., SAGA)
    taker_buy_quote_volume = float(candle[10])  # Amount bought (in quote asset, e.g., USDT)

    # Calculate amount sold
    amount_sold_base = volume - taker_buy_base_volume  # Amount sold (in base asset)
    amount_sold_quote = quote_asset_volume - taker_buy_quote_volume  # Amount sold (in quote asset)

    # Determine the side (buyer or seller dominated)
    if taker_buy_base_volume > amount_sold_base:
        side = "Buyers dominated 🟢"
    else:
        side = "Sellers dominated 🔴"

    # Format the candle data into a readable string
    candle_info = (
        f"📊 *Candle Data for {symbol}*\n"
        f"⏰ Open Time: `{open_time}`\n"
        f"🟢 Open Price: `{open_price}`\n"
        f"🔴 Close Price: `{close_price}`\n"
        f"🔼 High Price: `{high_price}`\n"
        f"🔽 Low Price: `{low_price}`\n"
        f"📈 Volume: `{format_number(volume)}`\n"
        f"💹 USDT Volume: `{format_number(quote_asset_volume)}`\n"
        f"🔢 Number of Trades: `{num_trades}`\n"
        f"💰 Amount Bought ({symbol}): `{format_number(taker_buy_base_volume)}`\n"
        f"💰 Amount Bought (USDT): `{format_number(taker_buy_quote_volume)}`\n"
        f"💸 Amount Sold ({symbol}): `{format_number(amount_sold_base)}`\n"
        f"💸 Amount Sold (USDT): `{format_number(amount_sold_quote)}`\n"
        f"⚖️ Side: `{side}`\n"
    )
    return candle_info

# Command handler for the /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome! Use the /candle command to get candle data. "
        "Example: /candle SAGAUSDT 3m 2025-01-15 15:03:00"
    )

# Command handler for the /candle command
async def candle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Extract arguments from the command
        args = context.args
        if len(args) < 3:
            await update.message.reply_text(
                "Please provide the symbol, interval, and timestamp. "
                "Example: /candle SAGAUSDT 3m 2025-01-15 15:03:00"
            )
            return

        symbol = args[0].upper()  # Trading pair (e.g., SAGAUSDT)
        interval = args[1]  # Candle interval (e.g., 3m, 15m)
        timestamp_str = " ".join(args[2:])  # Timestamp (e.g., 2025-01-15 15:03:00)

        # Convert the timestamp to a Unix timestamp in milliseconds
        timestamp = int(datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S").timestamp() * 1000)

        # Fetch the candle data
        candle_data = fetch_candle_data(symbol, interval, timestamp)

        # Format and send the candle data
        candle_info = format_candle_data(candle_data, symbol)
        await update.message.reply_text(candle_info, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"An error occurred: {e}")

# Main function to start the bot
def main():
    # Replace 'YOUR_TELEGRAM_BOT_TOKEN' with your actual bot token
    application = Application.builder().token("7782535176:AAF60Jjv5trbmSAqScYEORhmNfuAEoqotuA").build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("candle", candle))

    # Start the bot
    application.run_polling()

if __name__ == "__main__":
    main()
'''
'''
import requests
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Binance API endpoint for klines (candlestick data)
BINANCE_API_URL = "https://api.binance.com/api/v3/klines"

# Function to fetch candle data for a specific symbol, interval, and timestamp
def fetch_candle_data(symbol: str, interval: str, timestamp: int):
    params = {
        "symbol": symbol,
        "interval": interval,
        "startTime": timestamp,  # Fetch the candle starting at the specified timestamp
        "limit": 1  # Fetch only one candle
    }
    response = requests.get(BINANCE_API_URL, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Error fetching data: {response.status_code} - {response.text}")

# Function to parse and format candle data
def format_candle_data(candle_data):
    # Extract candle data
    candle = candle_data[0]
    open_time = datetime.fromtimestamp(candle[0] / 1000).strftime('%Y-%m-%d %H:%M:%S')
    open_price = float(candle[1])
    high_price = float(candle[2])
    low_price = float(candle[3])
    close_price = float(candle[4])
    volume = float(candle[5])
    close_time = datetime.fromtimestamp(candle[6] / 1000).strftime('%Y-%m-%d %H:%M:%S')
    quote_asset_volume = float(candle[7])
    num_trades = int(candle[8])
    taker_buy_base_volume = float(candle[9])  # Amount bought (in base asset, e.g., SAGA)
    taker_buy_quote_volume = float(candle[10])  # Amount bought (in quote asset, e.g., USDT)

    # Calculate amount sold
    amount_sold_base = volume - taker_buy_base_volume  # Amount sold (in base asset)
    amount_sold_quote = quote_asset_volume - taker_buy_quote_volume  # Amount sold (in quote asset)

    # Format the candle data into a readable string
    candle_info = (
        f"Open Time: {open_time}\n"
        f"Open Price: {open_price}\n"
        f"High Price: {high_price}\n"
        f"Low Price: {low_price}\n"
        f"Close Price: {close_price}\n"
        f"Volume: {volume}\n"
        f"Close Time: {close_time}\n"
        f"Quote Asset Volume: {quote_asset_volume}\n"
        f"Number of Trades: {num_trades}\n"
        f"Amount Bought (Base Asset): {taker_buy_base_volume}\n"
        f"Amount Bought (Quote Asset): {taker_buy_quote_volume}\n"
        f"Amount Sold (Base Asset): {amount_sold_base}\n"
        f"Amount Sold (Quote Asset): {amount_sold_quote}\n"
    )
    return candle_info

# Command handler for the /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome! Use the /candle command to get candle data. "
        "Example: /candle SAGAUSDT 3m 2025-01-15 15:03:00"
    )

# Command handler for the /candle command
async def candle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Extract arguments from the command
        args = context.args
        if len(args) < 3:
            await update.message.reply_text(
                "Please provide the symbol, interval, and timestamp. "
                "Example: /candle SAGAUSDT 3m 2025-01-15 15:03:00"
            )
            return

        symbol = args[0].upper()  # Trading pair (e.g., SAGAUSDT)
        interval = args[1]  # Candle interval (e.g., 3m, 15m)
        timestamp_str = " ".join(args[2:])  # Timestamp (e.g., 2025-01-15 15:03:00)

        # Convert the timestamp to a Unix timestamp in milliseconds
        timestamp = int(datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S").timestamp() * 1000)

        # Fetch the candle data
        candle_data = fetch_candle_data(symbol, interval, timestamp)

        # Format and send the candle data
        candle_info = format_candle_data(candle_data)
        await update.message.reply_text(candle_info)
    except Exception as e:
        await update.message.reply_text(f"An error occurred: {e}")

# Main function to start the bot
def main():
    # Replace 'YOUR_TELEGRAM_BOT_TOKEN' with your actual bot token
    application = Application.builder().token("7782535176:AAF60Jjv5trbmSAqScYEORhmNfuAEoqotuA").build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("candle", candle))

    # Start the bot
    application.run_polling()

if __name__ == "__main__":
    main()
'''

'''
import requests
from datetime import datetime

# Binance API endpoint for klines (candlestick data)
BINANCE_API_URL = "https://api.binance.com/api/v3/klines"

# Function to fetch candle data for a specific symbol, interval, and timestamp
def fetch_candle_data(symbol: str, interval: str, timestamp: int):
    params = {
        "symbol": symbol,
        "interval": interval,
        "startTime": timestamp,  # Fetch the candle starting at the specified timestamp
        "limit": 1  # Fetch only one candle
    }
    response = requests.get(BINANCE_API_URL, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Error fetching data: {response.status_code} - {response.text}")

# Function to parse and print candle data
def print_candle_data(candle_data):
    # Extract candle data
    candle = candle_data[0]
    open_time = datetime.fromtimestamp(candle[0] / 1000).strftime('%Y-%m-%d %H:%M:%S')
    open_price = float(candle[1])
    high_price = float(candle[2])
    low_price = float(candle[3])
    close_price = float(candle[4])
    volume = float(candle[5])
    close_time = datetime.fromtimestamp(candle[6] / 1000).strftime('%Y-%m-%d %H:%M:%S')
    quote_asset_volume = float(candle[7])
    num_trades = int(candle[8])
    taker_buy_base_volume = float(candle[9])  # Amount bought (in base asset, e.g., SAGA)
    taker_buy_quote_volume = float(candle[10])  # Amount bought (in quote asset, e.g., USDT)

    # Calculate amount sold
    amount_sold_base = volume - taker_buy_base_volume  # Amount sold (in base asset)
    amount_sold_quote = quote_asset_volume - taker_buy_quote_volume  # Amount sold (in quote asset)

    # Print candle data
    print(f"Open Time: {open_time}")
    print(f"Open Price: {open_price}")
    print(f"High Price: {high_price}")
    print(f"Low Price: {low_price}")
    print(f"Close Price: {close_price}")
    print(f"Volume: {volume}")
    print(f"Close Time: {close_time}")
    print(f"Quote Asset Volume: {quote_asset_volume}")
    print(f"Number of Trades: {num_trades}")
    print(f"Amount Bought (SAGA): {taker_buy_base_volume}")
    print(f"Amount Bought (USDT): {taker_buy_quote_volume}")
    print(f"Amount Sold (SAGA): {amount_sold_base}")
    print(f"Amount Sold (USDT): {amount_sold_quote}")

# Main function
def main():
    symbol = "SAGAUSDT"  # SAGA/USDT trading pair
    interval = "3m"  # 3-minute candle

    # Convert the human-readable timestamp to a Unix timestamp in milliseconds
    timestamp_str = "2025-01-15 15:03:00"  # Wed 15 Jan'25 14:30
    timestamp = int(datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S").timestamp() * 1000)

    try:
        # Fetch the specific 3m candle data
        candle_data = fetch_candle_data(symbol, interval, timestamp)
        
        # Print the candle data
        print_candle_data(candle_data)
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()


'''
