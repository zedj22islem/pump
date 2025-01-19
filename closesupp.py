from binance.client import Client
import pandas as pd
from tabulate import tabulate
import time

# Binance API keys (replace with your keys)
api_key = "wzdOesH8srd3wFp019ws3grCnbQuAczeJNW3Cy4egGTLDqsotnDbmaBxr3dbHdBo"
api_secret = "IOvPNSHYSdftRJi3quUzjoJ2kX8rpIMNMxXVY8c9KVUQLvsg0WMmW5aKgSLvN4GD"
client = Client(api_key, api_secret)

# Parameters
coins = [   'EOSUSDT', 'IOTAUSDT', 'XLMUSDT', 'ONTUSDT', 'ETCUSDT', 'ICXUSDT', 'NULSUSDT', 'VETUSDT', 'LINKUSDT', 'ONGUSDT',
    'HOTUSDT', 'ZILUSDT', 'FETUSDT', 'BATUSDT', 'ZECUSDT', 'IOSTUSDT', 'CELRUSDT', 'DASHUSDT', 'THETAUSDT', 'ENJUSDT',
    'ATOMUSDT', 'TFUELUSDT', 'ONEUSDT', 'FTMUSDT', 'ALGOUSDT', 'DUSKUSDT', 'ANKRUSDT', 'WINUSDT', 'COSUSDT', 'MTLUSDT',
    'DENTUSDT', 'CVCUSDT', 'CHZUSDT', 'BANDUSDT', 'XTZUSDT', 'RVNUSDT', 'HBARUSDT', 'NKNUSDT', 'STXUSDT', 'ARPAUSDT',
    'IOTXUSDT', 'RLCUSDT', 'CTXCUSDT', 'OGNUSDT', 'LSKUSDT', 'LTOUSDT', 'STPTUSDT', 'DATAUSDT', 'CTSIUSDT', 'HIVEUSDT',
    'CHRUSDT', 'ARDRUSDT', 'MDTUSDT', 'STMXUSDT', 'LRCUSDT', 'SCUSDT', 'ZENUSDT', 'VTHOUSDT', 'DGBUSDT', 'SXPUSDT',
    'DCRUSDT', 'STORJUSDT', 'MANAUSDT', 'KMDUSDT', 'SANDUSDT', 'DOTUSDT', 'RSRUSDT', 'TRBUSDT', 'KSMUSDT', 'EGLDUSDT',
    'DIAUSDT', 'RUNEUSDT', 'FIOUSDT', 'UMAUSDT', 'OXTUSDT', 'AVAXUSDT', 'UTKUSDT', 'NEARUSDT', 'FILUSDT', 'AXSUSDT',
    'STRAXUSDT', 'ROSEUSDT', 'AVAUSDT', 'SKLUSDT', 'GRTUSDT', 'ATMUSDT', 'ASRUSDT', 'CELOUSDT', 'RIFUSDT', 'CKBUSDT',
    'TWTUSDT', 'FIROUSDT', 'LITUSDT', 'SFPUSDT', 'ACMUSDT', 'OMUSDT', 'PONDUSDT', 'ALICEUSDT', 'SUPERUSDT', 'CFXUSDT',
    'PUNDIXUSDT', 'TLMUSDT', 'SLPUSDT', 'ICPUSDT', 'ARUSDT', 'MASKUSDT', 'LPTUSDT', 'XVGUSDT', 'ATAUSDT', 'GTCUSDT',
    'PHAUSDT', 'DEXEUSDT', 'CLVUSDT', 'QNTUSDT', 'FLOWUSDT', 'MINAUSDT', 'REQUSDT', 'WAXPUSDT', 'XECUSDT', 'ELFUSDT',
    'VIDTUSDT', 'SYSUSDT', 'FIDAUSDT', 'AGLDUSDT', 'RADUSDT', 'RAREUSDT', 'ADXUSDT', 'DARUSDT', 'MOVRUSDT', 'ENSUSDT',
    'POWRUSDT', 'JASMYUSDT', 'AMPUSDT', 'PYRUSDT', 'BICOUSDT', 'FLUXUSDT', 'VOXELUSDT', 'HIGHUSDT', 'PEOPLEUSDT',
    'ACHUSDT', 'GLMRUSDT', 'LOKAUSDT', 'SCRTUSDT', 'API3USDT', 'XNOUSDT', 'ALPINEUSDT', 'ASTRUSDT', 'GMTUSDT',
    'KDAUSDT', 'APEUSDT', 'STEEMUSDT', 'REIUSDT', 'OPUSDT', 'POLYXUSDT', 'APTUSDT', 'PHBUSDT', 'HOOKUSDT', 'MAGICUSDT',
    'GLMUSDT', 'PROMUSDT', 'QKCUSDT', 'IDUSDT', 'EDUUSDT', 'SUIUSDT', 'AERGOUSDT', 'SNTUSDT', 'COMBOUSDT', 'ARKMUSDT',
    'WLDUSDT', 'SEIUSDT', 'CYBERUSDT', 'ARKUSDT', 'IQUSDT', 'TIAUSDT', 'ORDIUSDT', 'BEAMXUSDT', 'PIVXUSDT', 'VICUSDT',
    'BLURUSDT', 'VANRYUSDT', '1000SATSUSDT', 'ACEUSDT', 'NFPUSDT',  'XAIUSDT', 'MANTAUSDT', 'ALTUSDT',
    'PYTHUSDT', 'DYMUSDT', 'PDAUSDT', 'AXLUSDT', 'METISUSDT', 'WUSDT', 'TNSRUSDT', 'SAGAUSDT', 'TAOUSDT', 'OMNIUSDT',
    'NOTUSDT', 'IOUSDT', 'ZKUSDT', 'ZROUSDT', 'GUSDT', 'BANANAUSDT', 'RENDERUSDT', 'TONUSDT', 'SLFUSDT', 'POLUSDT',
    'CATIUSDT', 'SCRUSDT', 'KAIAUSDT', 'ACXUSDT', 'MOVEUSDT', 'MEUSDT', 'VANAUSDT', 'BIOUSDT']  # Replace with your coin list (truncated for brevity)
lookback_days = 20  # Lookback period for price range and volume analysis
range_threshold = 0.4  # 40% range threshold
support_proximity_threshold = 0.035  # 1% threshold for proximity to support

def fetch_daily_data(symbol, lookback):
    """Fetch historical daily data for a given symbol."""
    klines = client.get_klines(symbol=symbol, interval='4h', limit=lookback)
    df = pd.DataFrame(klines, columns=[
        "timestamp", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "number_of_trades",
        "taker_buy_base", "taker_buy_quote", "ignore"
    ])
    
    # Convert relevant columns to numeric types
    numeric_columns = ["open", "high", "low", "close", "volume", "quote_asset_volume", "taker_buy_quote"]
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")  # Convert to numeric, coercing errors to NaN
    
    df["volume_usdt"] = df["volume"] * df["close"]  # Volume in USDT
    return df

def is_range_bound(df, range_threshold):
    """Check if price is range-bound within the threshold."""
    highest = df["high"].max()
    lowest = df["low"].min()
    range_ratio = (highest - lowest) / lowest
    return range_ratio <= range_threshold, lowest, highest

def format_number(n):
    """Format numbers above 1000 as 1k, 1M, etc."""
    if n >= 1e6:
        return f"{n / 1e6:.1f}M"
    elif n >= 1e3:
        return f"{n / 1e3:.1f}k"
    else:
        return f"{n:.2f}"

def analyze_volume(df):
    """Calculate dominance and percentage based on taker buy and sell volumes."""
    total_buy_volume = df["taker_buy_quote"].sum()  # Total taker buy volume in USDT
    total_sell_volume = df["volume_usdt"].sum() - total_buy_volume  # Total taker sell volume in USDT
    total_volume = total_buy_volume + total_sell_volume  # Total volume in USDT

    if total_volume == 0:
        return "Neutral", 0  # Handle division by zero

    buy_dominance_percentage = (total_buy_volume / total_volume) * 100
    sell_dominance_percentage = (total_sell_volume / total_volume) * 100

    if buy_dominance_percentage > sell_dominance_percentage:
        return "Buy Side", buy_dominance_percentage
    else:
        return "Sell Side", sell_dominance_percentage

def calculate_price_range_percentage(df):
    """Calculate price range percentage over the last 50 candles."""
    highest = df["high"].max()
    lowest = df["low"].min()
    price_range_percentage = ((highest - lowest) / lowest) * 100  # Percentage difference
    return price_range_percentage

def get_current_price(symbol):
    """Fetch the current price of a symbol."""
    ticker = client.get_symbol_ticker(symbol=symbol)
    return float(ticker["price"])

# Analyze coins
range_bound_coins = []
for coin in coins:
    try:
        df = fetch_daily_data(coin, lookback_days)
        range_condition, support, resistance = is_range_bound(df, range_threshold)
        if range_condition:
            price_range_percentage = calculate_price_range_percentage(df)
            dominance, dominance_percentage = analyze_volume(df)

            # Get the current price
            current_price = get_current_price(coin)

            # Check if the current price is close to support (within 1%)
            if current_price <= support * (1 + support_proximity_threshold):
                # Get the last candle's volume in USDT
                last_candle_volume = df.iloc[-2]["volume"]

                # Get the highest and lowest prices in the lookback period
                highest_price = df["high"].max()
                lowest_price = df["low"].min()

                # Add to the results
                range_bound_coins.append({
                    "Coin": coin,
                    "Price Range %": format_number(price_range_percentage),
                    "Support": support,
                    "Resistance": resistance,
                    "Dominance": dominance,
                    "Dominance %": f"{dominance_percentage:.2f}%",
                    "Last Candle Volume (USDT)": format_number(last_candle_volume),
                    "Highest Price": highest_price,
                    "Lowest Price": lowest_price,
                    "Current Price": current_price,
                })
        time.sleep(0.1)  # Avoid hitting API rate limits
    except Exception as e:
        print(f"Error analyzing {coin}: {e}")

# Output results in a table
if range_bound_coins:
    print("Coins likely bouncing in a range with Buy Side dominance and close to support:")
    print(tabulate(range_bound_coins, headers="keys", tablefmt="fancy_grid"))
else:
    print("No coins currently meet the criteria.")