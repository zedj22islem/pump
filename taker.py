import logging
from binance.client import Client
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from datetime import datetime

# Binance API credentials
BINANCE_API_KEY = 'wzdOesH8srd3wFp019ws3grCnbQuAczeJNW3Cy4egGTLDqsotnDbmaBxr3dbHdBo'
BINANCE_API_SECRET = 'IOvPNSHYSdftRJi3quUzjoJ2kX8rpIMNMxXVY8c9KVUQLvsg0WMmW5aKgSLvN4GD'

# Telegram bot token
TELEGRAM_BOT_TOKEN = '7720907389:AAHnt_GQZf3aaIJShRHXecocJOOWuug84lE'

# Initialize Binance client
client = Client(BINANCE_API_KEY, BINANCE_API_SECRET)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def format_number(number: float) -> str:
    """Format numbers to 10k or 1M format."""
    if number >= 1_000_000:
        return f"{number / 1_000_000:.1f}M"
    elif number >= 1_000:
        return f"{number / 1_000:.1f}k"
    else:
        return f"{number:.2f}"

def analyze_volume(coin_symbol: str) -> dict:
    """Fetch and analyze the last 1000 trades for a given coin."""
    try:
        # Fetch the last 1000 trades
        trades = client.get_recent_trades(
            symbol=coin_symbol.upper() + 'USDT',
            limit=1000
        )
        
        if not trades:
            return None
        
        # Initialize variables to track buy and sell volumes in USDT
        buy_volume_usdt = 0.0
        sell_volume_usdt = 0.0
        
        # Get the earliest and latest trade timestamps
        earliest_trade_time = datetime.fromtimestamp(int(trades[-1]['time']) / 1000)
        latest_trade_time = datetime.fromtimestamp(int(trades[0]['time']) / 1000)
        
        # Calculate the time taken for these 1000 trades (in seconds)
        time_taken_seconds = (latest_trade_time - earliest_trade_time).total_seconds()
        
        # Analyze trades
        for trade in trades:
            quantity = float(trade['qty'])  # Quantity in the base asset (e.g., BTC)
            price = float(trade['price'])   # Price in USDT
            trade_value_usdt = quantity * price  # Trade value in USDT
            
            if trade['isBuyerMaker']:
                sell_volume_usdt += trade_value_usdt  # Seller is the maker
            else:
                buy_volume_usdt += trade_value_usdt  # Buyer is the taker
        
        # Determine dominance
        if buy_volume_usdt > sell_volume_usdt:
            dominance = "Buyer Taker"
        elif sell_volume_usdt > buy_volume_usdt:
            dominance = "Seller Taker"
        else:
            dominance = "Neutral"
        
        return {
            'dominance': dominance,
            'buy_volume_usdt': buy_volume_usdt,
            'sell_volume_usdt': sell_volume_usdt,
            'time_taken_seconds': time_taken_seconds,
            'earliest_trade_time': earliest_trade_time,
            'latest_trade_time': latest_trade_time
        }
    
    except Exception as e:
        logger.error(f"Error fetching data for {coin_symbol}: {e}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the /start command is issued."""
    await update.message.reply_text(
        "Welcome! Send me a coin symbol (e.g., BTC, ETH) and I'll tell you the volume dominance, amounts bought/sold in USDT, and time taken for the last 1000 trades."
    )

async def analyze(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Analyze the last 1000 trades for the given coin symbol."""
    # Extract the coin symbol from the command arguments
    if not context.args:
        await update.message.reply_text("Please provide a coin symbol (e.g., /analyze BTC).")
        return
    
    coin_symbol = context.args[0].upper()
    
    result = analyze_volume(coin_symbol)
    
    if result:
        response = (
            f"Coin: {coin_symbol}\n"
            f"Last 1000 Trades Data:\n"
            f"Dominance: {result['dominance']}\n"
            f"Amount Bought (USDT): {format_number(result['buy_volume_usdt'])}\n"
            f"Amount Sold (USDT): {format_number(result['sell_volume_usdt'])}\n"
            f"Time Taken: {int(result['time_taken_seconds'])} seconds\n"
            f"Earliest Trade: {result['earliest_trade_time'].strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Latest Trade: {result['latest_trade_time'].strftime('%Y-%m-%d %H:%M:%S')}"
        )
    else:
        response = f"Could not fetch data for {coin_symbol}. Please check the symbol and try again."
    
    await update.message.reply_text(response)

def main() -> None:
    """Start the bot."""
    # Initialize the Telegram bot
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("analyze", analyze))
    
    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main()
'''

import logging
from binance.client import Client
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Binance API credentials
BINANCE_API_KEY = 'wzdOesH8srd3wFp019ws3grCnbQuAczeJNW3Cy4egGTLDqsotnDbmaBxr3dbHdBo'
BINANCE_API_SECRET = 'IOvPNSHYSdftRJi3quUzjoJ2kX8rpIMNMxXVY8c9KVUQLvsg0WMmW5aKgSLvN4GD'

# Telegram bot token
TELEGRAM_BOT_TOKEN = '7720907389:AAHnt_GQZf3aaIJShRHXecocJOOWuug84lE'

# Initialize Binance client
client = Client(BINANCE_API_KEY, BINANCE_API_SECRET)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def analyze_volume(coin_symbol: str) -> dict:
    """Fetch and analyze the current volume for a given coin."""
    try:
        # Fetch recent trades
        trades = client.get_recent_trades(symbol=coin_symbol.upper() + 'USDT')
        
        # Initialize variables to track buy and sell volumes
        buy_volume = 0.0
        sell_volume = 0.0
        
        for trade in trades:
            if trade['isBuyerMaker']:
                sell_volume += float(trade['qty'])
            else:
                buy_volume += float(trade['qty'])
        
        # Determine if the volume is dominated by buyers or sellers
        if buy_volume > sell_volume:
            dominance = "Buyer Taker"
        elif sell_volume > buy_volume:
            dominance = "Seller Taker"
        else:
            dominance = "Neutral"
        
        return {
            'dominance': dominance,
            'buy_volume': buy_volume,
            'sell_volume': sell_volume
        }
    
    except Exception as e:
        logger.error(f"Error fetching data for {coin_symbol}: {e}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the /start command is issued."""
    await update.message.reply_text(
        "Welcome! Send me a coin symbol (e.g., BTC, ETH) and I'll tell you the current volume dominance and amounts bought/sold."
    )

async def analyze(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Analyze the volume for the given coin symbol."""
    # Extract the coin symbol from the command arguments
    if not context.args:
        await update.message.reply_text("Please provide a coin symbol (e.g., /analyze BTC).")
        return
    
    coin_symbol = context.args[0].upper()
    
    result = analyze_volume(coin_symbol)
    
    if result:
        response = (
            f"Coin: {coin_symbol}\n"
            f"Dominance: {result['dominance']}\n"
            f"Amount Bought: {result['buy_volume']}\n"
            f"Amount Sold: {result['sell_volume']}"
        )
    else:
        response = f"Could not fetch data for {coin_symbol}. Please check the symbol and try again."
    
    await update.message.reply_text(response)

def main() -> None:
    """Start the bot."""
    # Initialize the Telegram bot
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("analyze", analyze))
    
    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main()

    '''