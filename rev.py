from binance.client import Client
import pandas as pd
import time
from tabulate import tabulate
import matplotlib.pyplot as plt

# Replace with your Binance API key and secret
API_KEY = 'wzdOesH8srd3wFp019ws3grCnbQuAczeJNW3Cy4egGTLDqsotnDbmaBxr3dbHdBo'
API_SECRET = 'IOvPNSHYSdftRJi3quUzjoJ2kX8rpIMNMxXVY8c9KVUQLvsg0WMmW5aKgSLvN4GD'

# Initialize Binance client
client = Client(API_KEY, API_SECRET)

# Parameters
SYMBOL = 'OMUSDT'  # Trading pair to analyze (USDT pairs only)
LARGE_ORDER_THRESHOLD = 10000  # Minimum USDT value to consider as a large order
TIME_WINDOW = 10  # Time window (in seconds) to refresh data
ORDER_BOOK_DEPTH = 200  # Number of bid/ask levels to analyze
HISTORICAL_TRADES_LIMIT = 1000000  # Number of historical trades to fetch for trend analysis

def format_number(number):
    """Format numbers in a human-readable way (e.g., 1000 -> 1k, 1000000 -> 1M)."""
    if number >= 1_000_000:
        return f"{number / 1_000_000:.2f}M"
    elif number >= 1_000:
        return f"{number / 1_000:.2f}k"
    else:
        return f"{number:,.2f}"

def fetch_order_book(symbol, depth):
    """Fetch the order book (bids and asks) for a given symbol."""
    order_book = client.get_order_book(symbol=symbol, limit=depth)
    return order_book

def fetch_historical_trades(symbol, limit):
    """Fetch historical trades for a given symbol."""
    trades = client.get_recent_trades(symbol=symbol, limit=limit)
    return trades

def analyze_order_flow(order_book):
    """Analyze order flow data from the order book."""
    bids = order_book['bids']  # List of buy orders (bids)
    asks = order_book['asks']  # List of sell orders (asks)

    # Calculate total bid and ask volume in USDT
    total_bid_volume = sum(float(bid[0]) * float(bid[1]) for bid in bids)  # Price * Quantity
    total_ask_volume = sum(float(ask[0]) * float(ask[1]) for ask in asks)  # Price * Quantity

    # Calculate bid/ask volume imbalance
    volume_imbalance = total_bid_volume - total_ask_volume

    # Detect large orders (whale activity) in USDT
    large_bids = [bid for bid in bids if float(bid[0]) * float(bid[1]) >= LARGE_ORDER_THRESHOLD]
    large_asks = [ask for ask in asks if float(ask[0]) * float(ask[1]) >= LARGE_ORDER_THRESHOLD]

    # Find price levels with high liquidity
    high_liquidity_bids = sorted(bids, key=lambda x: float(x[1]) * float(x[0]), reverse=True)[:5]
    high_liquidity_asks = sorted(asks, key=lambda x: float(x[1]) * float(x[0]), reverse=True)[:5]

    return {
        'total_bid_volume': total_bid_volume,
        'total_ask_volume': total_ask_volume,
        'volume_imbalance': volume_imbalance,
        'large_bids': large_bids,
        'large_asks': large_asks,
        'high_liquidity_bids': high_liquidity_bids,
        'high_liquidity_asks': high_liquidity_asks,
    }

def analyze_trend(historical_trades):
    """Analyze historical trades to detect market trends."""
    buy_volume = 0  # Total buy volume in USDT
    sell_volume = 0  # Total sell volume in USDT

    for trade in historical_trades:
        price = float(trade['price'])
        volume = float(trade['qty'])
        value = price * volume  # Calculate value in USDT

        if trade['isBuyerMaker']:  # Seller is aggressive (sell order)
            sell_volume += value
        else:  # Buyer is aggressive (buy order)
            buy_volume += value

    trend = "Bullish" if buy_volume > sell_volume else "Bearish"
    return trend, buy_volume, sell_volume

def plot_order_book(order_book):
    """Plot bid and ask volumes from the order book."""
    bids = order_book['bids']
    asks = order_book['asks']

    bid_prices = [float(bid[0]) for bid in bids]
    bid_volumes = [float(bid[0]) * float(bid[1]) for bid in bids]  # Volume in USDT
    ask_prices = [float(ask[0]) for ask in asks]
    ask_volumes = [float(ask[0]) * float(ask[1]) for ask in asks]  # Volume in USDT

    plt.figure(figsize=(10, 6))
    plt.barh(bid_prices, bid_volumes, color='green', label='Bid Volume (USDT)')
    plt.barh(ask_prices, ask_volumes, color='red', label='Ask Volume (USDT)')
    plt.xlabel('Volume (USDT)')
    plt.ylabel('Price (USDT)')
    plt.title('Order Book: Bid vs Ask Volume (USDT)')
    plt.legend()
    plt.show()

def display_results(order_flow_data, trend_data):
    """Display order flow analysis results in a readable format."""
    print("\n📊 Order Flow Analysis Results:")
    print(f"Total Bid Volume: {format_number(order_flow_data['total_bid_volume'])} USDT")
    print(f"Total Ask Volume: {format_number(order_flow_data['total_ask_volume'])} USDT")
    print(f"Volume Imbalance: {format_number(order_flow_data['volume_imbalance'])} USDT")

    # Display trend analysis
    trend, buy_volume, sell_volume = trend_data
    print(f"\n📈 Market Trend: {trend}")
    print(f"Buy Volume: {format_number(buy_volume)} USDT")
    print(f"Sell Volume: {format_number(sell_volume)} USDT")

    # Display large orders
    if order_flow_data['large_bids'] or order_flow_data['large_asks']:
        print("\n🚨 Large Orders (Whale Activity):")
        large_orders = []
        for bid in order_flow_data['large_bids']:
            large_orders.append({
                'Side': 'Buy',
                'Price (USDT)': format_number(float(bid[0])),
                'Volume (BTC)': format_number(float(bid[1])),
                'Value (USDT)': format_number(float(bid[0]) * float(bid[1])),
            })
        for ask in order_flow_data['large_asks']:
            large_orders.append({
                'Side': 'Sell',
                'Price (USDT)': float(ask[0]),
                'Volume (BTC)': format_number(float(ask[1])),
                'Value (USDT)': format_number(float(ask[0]) * float(ask[1])),
            })
        print(tabulate(large_orders, headers="keys", tablefmt="pretty"))

    # Display high liquidity levels
    print("\n💰 High Liquidity Levels:")
    high_liquidity = []
    for bid in order_flow_data['high_liquidity_bids']:
        high_liquidity.append({
            'Side': 'Buy',
            'Price (USDT)': float(bid[0]),
            'Volume (USDT)': format_number(float(bid[0]) * float(bid[1])),
        })
    for ask in order_flow_data['high_liquidity_asks']:
        high_liquidity.append({
            'Side': 'Sell',
            'Price (USDT)': float(ask[0]),
            'Volume (USDT)': format_number(float(ask[0]) * float(ask[1])),
        })
    print(tabulate(high_liquidity, headers="keys", tablefmt="pretty"))

def main():
    print(f"Starting Advanced Order Flow Analysis for {SYMBOL}...")
    while True:
        try:
            # Fetch order book data
            order_book = fetch_order_book(SYMBOL, ORDER_BOOK_DEPTH)

            # Fetch historical trades for trend analysis
            historical_trades = fetch_historical_trades(SYMBOL, HISTORICAL_TRADES_LIMIT)

            # Analyze order flow
            order_flow_data = analyze_order_flow(order_book)

            # Analyze market trend
            trend_data = analyze_trend(historical_trades)

            # Display results
            display_results(order_flow_data, trend_data)

            # Plot order book data
            plot_order_book(order_book)

            # Wait before the next iteration
            time.sleep(TIME_WINDOW)

        except Exception as e:
            print(f"Error: {e}")
            time.sleep(100)  # Wait before retrying

if __name__ == "__main__":
    main()