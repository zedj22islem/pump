import ccxt
import time

# Initialize the exchange
exchange = ccxt.binance()  # You can change to another exchange like 'kraken', 'coinbasepro', etc.

def get_trade_data(coin, timeframe='1d', num_candles=2):
    """
    Fetch trade data for a specific coin, timeframe, and number of candles.
    
    :param coin: The cryptocurrency symbol (e.g., 'BTC').
    :param timeframe: The timeframe for candles (e.g., '1d', '4h', '1h').
    :param num_candles: The number of candles to analyze.
    :return: A dictionary containing buy/sell volume and net volume for each candle and totals.
    """
    # Construct the symbol (e.g., BTC/USDT)
    symbol = f'{coin}/USDT'  # Assuming trading against USDT
    
    # Fetch the historical candles to get the start and end times for the candles
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=num_candles + 1)
    
    # Ensure there are enough candles
    if len(ohlcv) < num_candles + 1:
        raise ValueError(f"Not enough candles fetched. Increase the 'limit' parameter or reduce 'num_candles'.")
    
    # Fetch trades for each candle
    def fetch_trades_for_candle(start_time, end_time):
        trades = []
        since = start_time
        while True:
            new_trades = exchange.fetch_trades(symbol, since=since)
            if not new_trades:
                break
            trades.extend(new_trades)
            since = new_trades[-1]['timestamp'] + 1
            if since >= end_time:
                break
            time.sleep(0.1)  # Rate limit to avoid being banned
        return [trade for trade in trades if start_time <= trade['timestamp'] < end_time]
    
    # Calculate buy and sell volume for each candle
    def calculate_buy_sell_volume(trades):
        buy_volume = 0
        sell_volume = 0
        for trade in trades:
            if trade['side'] == 'buy':
                buy_volume += trade['amount']
            elif trade['side'] == 'sell':
                sell_volume += trade['amount']
        return buy_volume, sell_volume
    
    # Analyze each candle
    results = {}
    total_buy_volume = 0
    total_sell_volume = 0
    total_net_volume = 0
    
    for i in range(num_candles):
        candle_start = ohlcv[-(i + 2)][0]  # Start time of the candle
        candle_end = ohlcv[-(i + 1)][0]    # End time of the candle
        
        # Fetch trades for the candle
        trades = fetch_trades_for_candle(candle_start, candle_end)
        
        # Calculate buy/sell volume
        buy_volume, sell_volume = calculate_buy_sell_volume(trades)
        net_volume = buy_volume - sell_volume
        
        # Update totals
        total_buy_volume += buy_volume
        total_sell_volume += sell_volume
        total_net_volume += net_volume
        
        # Store results for this candle
        results[f'candle_{i + 1}'] = {
            'buy_volume': buy_volume,
            'sell_volume': sell_volume,
            'net_volume': net_volume
        }
    
    # Add totals to the results
    results['totals'] = {
        'total_buy_volume': total_buy_volume,
        'total_sell_volume': total_sell_volume,
        'total_net_volume': total_net_volume
    }
    
    return results

# Customizable inputs
coin = input("Enter the coin symbol (e.g., BTC): ").strip().upper()
timeframe = input("Enter the timeframe (e.g., 1d, 4h, 1h): ").strip().lower()
num_candles = int(input("Enter the number of candles to analyze: "))

# Fetch and print the data
try:
    data = get_trade_data(coin, timeframe, num_candles)
    print(f"\nAnalysis for {coin} ({timeframe} timeframe):")
    
    # Print individual candle data
    for i in range(num_candles):
        candle_data = data[f'candle_{i + 1}']
        print(f"Candle {i + 1} - Buy Volume: {candle_data['buy_volume']}, Sell Volume: {candle_data['sell_volume']}, Net Volume: {candle_data['net_volume']}")
    
    # Print totals
    totals = data['totals']
    print(f"\nTotals for {num_candles} candles:")
    print(f"Total Buy Volume: {totals['total_buy_volume']}")
    print(f"Total Sell Volume: {totals['total_sell_volume']}")
    print(f"Total Net Volume: {totals['total_net_volume']}")
except Exception as e:
    print(f"Error: {e}")