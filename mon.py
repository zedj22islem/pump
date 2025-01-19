import requests
import time
import pandas as pd

# Binance API endpoints
BINANCE_API_URL = 'https://api.binance.com/api/v3'
SYMBOLS = [ 'EOSUSDT', 'IOTAUSDT', 'XLMUSDT', 'ONTUSDT', 'ETCUSDT', 'ICXUSDT', 'NULSUSDT', 'VETUSDT', 'LINKUSDT', 'ONGUSDT',
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
    'CATIUSDT', 'SCRUSDT', 'KAIAUSDT', 'ACXUSDT', 'MOVEUSDT', 'MEUSDT', 'VANAUSDT', 'BIOUSDT']  # Add more coins as needed

# Function to fetch order book data
def get_order_book(symbol, limit=100):
    url = f'{BINANCE_API_URL}/depth'
    params = {
        'symbol': symbol,
        'limit': limit,
    }
    response = requests.get(url, params=params)
    return response.json()

# Function to analyze buy orders for whale activity
def analyze_whale_activity(symbol, min_order_value=200000, threshold=0.10):  # min_order_value in USD, threshold as a percentage
    order_book = get_order_book(symbol)
    bids = order_book['bids']  # Buy orders

    # Calculate total buy order value
    total_buy_value = sum(float(bid[0]) * float(bid[1]) for bid in bids)
    
    # Identify large buy orders that meet both conditions
    whale_buy_orders = []
    for bid in bids:
        price, quantity = float(bid[0]), float(bid[1])
        order_value = price * quantity
        if order_value > min_order_value and order_value > threshold * total_buy_value:
            whale_buy_orders.append({
                'symbol': symbol,
                'price': price,
                'quantity': quantity,
                'order_value': order_value,
                'percentage_of_total': (order_value / total_buy_value) * 100,  # For reporting
            })
    
    return whale_buy_orders

# Main function to monitor whale buy orders
def monitor_whale_buy_orders():
    print("Monitoring whale buy orders (>$200k and >10% of total buy value)...")
    for symbol in SYMBOLS:
        print(f"\nAnalyzing {symbol}...")
        whale_orders = analyze_whale_activity(symbol)
        if whale_orders:
            print(f"🐋 Significant buy orders detected for {symbol}:")
            for order in whale_orders:
                print(f"  Price: {order['price']}, Quantity: {order['quantity']}, Value: ${order['order_value']:,.2f}, % of Total: {order['percentage_of_total']:.2f}%")
        else:
            print(f"No significant buy orders detected for {symbol}.")

# Run the monitor
if __name__ == "__main__":
    while True:
        monitor_whale_buy_orders()
        print("\nSleeping for 1 minute before next check...")
        time.sleep(60)  # Check every 1 minute