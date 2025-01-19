import asyncio
import platform
import sys
import requests
from statistics import median, mean
import aiohttp
import argparse
from typing import List, Dict, Any, Optional
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, BarColumn, TimeRemainingColumn, TextColumn
from datetime import datetime
from dataclasses import dataclass
import re

# Set the event loop policy for Windows
if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Initialize Rich Console
console = Console()

# Binance Spot API Constants
KLINES_URL = 'https://api.binance.com/api/v3/klines'

# Asynchronous semaphore to limit concurrent requests
MAX_CONCURRENCY = 20
SEMAPHORE = asyncio.Semaphore(MAX_CONCURRENCY)

# Predefined list of coins (replace with your list)
COINS = [
    'EOSUSDT', 'IOTAUSDT', 'XLMUSDT', 'ONTUSDT', 'ETCUSDT', 'ICXUSDT', 'NULSUSDT', 'VETUSDT', 'LINKUSDT', 'ONGUSDT',
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
    'VIDTUSDT', 'SYSUSDT', 'FIDAUSDT', 'AGLDUSDT', 'RADUSDT', 'RAREUSDT', 'ADXUSDT',  'MOVRUSDT', 'ENSUSDT',
    'POWRUSDT', 'JASMYUSDT', 'AMPUSDT', 'PYRUSDT', 'BICOUSDT', 'FLUXUSDT', 'VOXELUSDT', 'HIGHUSDT', 'PEOPLEUSDT',
    'ACHUSDT', 'GLMRUSDT', 'LOKAUSDT', 'SCRTUSDT', 'API3USDT', 'XNOUSDT', 'ALPINEUSDT', 'ASTRUSDT', 'GMTUSDT',
    'KDAUSDT', 'APEUSDT', 'STEEMUSDT', 'REIUSDT', 'OPUSDT', 'POLYXUSDT', 'APTUSDT', 'PHBUSDT', 'HOOKUSDT', 'MAGICUSDT',
    'GLMUSDT', 'PROMUSDT', 'QKCUSDT', 'IDUSDT', 'EDUUSDT', 'SUIUSDT', 'AERGOUSDT', 'SNTUSDT', 'COMBOUSDT', 'ARKMUSDT',
    'WLDUSDT', 'SEIUSDT', 'CYBERUSDT', 'ARKUSDT', 'IQUSDT', 'TIAUSDT', 'ORDIUSDT', 'BEAMXUSDT', 'PIVXUSDT', 'VICUSDT',
    'BLURUSDT', 'VANRYUSDT', '1000SATSUSDT', 'ACEUSDT', 'NFPUSDT',  'XAIUSDT', 'MANTAUSDT', 'ALTUSDT',
    'PYTHUSDT', 'DYMUSDT', 'PDAUSDT', 'AXLUSDT', 'METISUSDT', 'WUSDT', 'TNSRUSDT', 'SAGAUSDT', 'TAOUSDT', 'OMNIUSDT',
    'NOTUSDT', 'IOUSDT', 'ZKUSDT', 'ZROUSDT', 'GUSDT', 'BANANAUSDT', 'RENDERUSDT', 'TONUSDT', 'SLFUSDT', 'POLUSDT',
    'CATIUSDT', 'SCRUSDT', 'KAIAUSDT', 'ACXUSDT', 'MOVEUSDT', 'MEUSDT', 'VANAUSDT', 'BIOUSDT','AIXBTUSDT'
]

# Type Definitions
KlineData = List[List[Any]]


@dataclass
class SymbolAnalysisResult:
    symbol: str
    volume_change: float
    price_change: float
    last_candle_volume_usdt: float  # Volume in USDT
    last_candle_green: bool  # Indicates if the last candle is green
    price_change_last_two_candles: float  # Price change of the last two candles
    median_volume_previous_candles_usdt: float  # Median volume of previous candles in USDT (excluding last two)
    median_volume_last_two_candles_usdt: float  # Median volume of the last two candles in USDT
    side_taker: str  # Indicates if the last candle is buyer or seller dominated
    amount_bought: float  # Amount bought in USDT (from taker_buy_quote_asset_volume)
    amount_sold: float  # Amount sold in USDT (calculated as quote_asset_volume - taker_buy_quote_asset_volume)
    price_change_1d: float  # Price change of the current 1-day candle


def send_telegram_notification(title: str, coins: List[SymbolAnalysisResult]):
    # Replace with your Telegram bot token and chat ID
    bot_token = "7669206577:AAFkCNJGkclyHf1w3x82DdLOAQDXUZ1Zzp4"
    chat_id = "5959819558"
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    # Construct the message
    message = f"🚀 {title}\n\n 1d: \n"
    for coin in coins:
        message += (
            f"Coin: {coin.symbol}\n"
            f"Volume Change: {round(coin.volume_change)}%\n"
            f"Price Change: {coin.price_change:.2f}%\n"
            f"Price Change (Last 2): {coin.price_change_last_two_candles:.2f}%\n"
            f"Price Change (1d): {coin.price_change_1d:.2f}%\n"
            f"Last Candle Volume (USDT): {format_volume(coin.last_candle_volume_usdt)}\n"
            f"Median Volume (Prev) USDT: {format_volume(coin.median_volume_previous_candles_usdt)}\n"
            f"Side Taker: {coin.side_taker}\n"
            f"Amount Bought (USDT): {format_volume(coin.amount_bought)}\n"
            f"Amount Sold (USDT): {format_volume(coin.amount_sold)}\n\n"
        )

    # Send the message
    payload = {
        "chat_id": chat_id,
        "text": message
    }
    response = requests.post(url, json=payload)
    if response.status_code != 200:
        console.print(f"[red]Error sending Telegram notification: {response.text}[/red]")
        console.print(f"Message: {message}[/red]")


def convert_interval_to_minutes(interval: str) -> int:
    multipliers = {'m': 1, 'h': 60, 'd': 1440, 'w': 10080, 'M': 43200, 'y': 525600}
    return int(interval[:-1]) * multipliers.get(interval[-1], 0)


def make_more_human_readable_interval_label(label: str) -> str:
    transitions = {'m': ('h', 60), 'h': ('d', 24), 'd': ('M', 30)}
    while label[-1] in transitions:
        value, unit = int(label[:-1]), label[-1]
        new_unit, divisor = transitions[unit]
        if value % divisor == 0:
            label = f"{value // divisor}{new_unit}"
        else:
            break
    return label


def parse_percentage(pct_str: str) -> float:
    try:
        return float(pct_str.strip('%'))
    except ValueError:
        console.print("[red]Invalid percentage format. Using default 2%.[/red]")
        return 2.0


def parse_timeframe(timeframe: str) -> int:
    match = re.match(r'^(\d+)([mhdw])$', timeframe)  # Added 'w' for weeks
    if not match:
        raise ValueError(f"Invalid timeframe format: {timeframe}")
    value, unit = match.groups()
    multipliers = {'m': 1, 'h': 60, 'd': 1440, 'w': 10080}  # Added 'w' -> 10080 (7 * 1440)
    return int(value) * multipliers[unit]


def calculate_required_candles(total_time: str, candle_interval: str) -> int:
    total_minutes = parse_timeframe(total_time)
    candle_minutes = parse_timeframe(candle_interval)
    return max((total_minutes // candle_minutes) + 1, 1)


async def fetch_json(session: aiohttp.ClientSession, url: str, params: Dict[str, Any]) -> Any:
    try:
        async with SEMAPHORE:
            async with session.get(url, params=params, ssl=False, timeout=10) as response:
                if response.status != 200:
                    console.print(f"[red]Error fetching data for {params['symbol']}: HTTP {response.status}[/red]")
                    return None
                data = await response.json()
                console.print(f"[green]Fetched data for {params['symbol']}: {len(data)} candles[/green]")
                return data
    except Exception as e:
        console.print(f"[red]Error fetching data for {params['symbol']}: {e}[/red]")
        return None


def format_volume(volume: float) -> str:
    if volume >= 1_000_000:
        return f"{volume / 1_000_000:.1f}M"
    elif volume >= 1_000:
        return f"{volume / 1_000:.1f}K"
    else:
        return f"{volume:.2f}"


async def analyze_symbol(
        session: aiohttp.ClientSession,
        symbol: str,
        args: argparse.Namespace
) -> Optional[SymbolAnalysisResult]:
    try:
        interval_limit = calculate_required_candles(args.range, args.interval)
        current_data = await fetch_json(session, KLINES_URL, {
            'symbol': symbol,
            'interval': f'{args.interval}',
            'limit': f"{interval_limit}"
        })

        if not current_data or len(current_data) < 3:
            console.print(f"[yellow]Skipping {symbol}: Not enough data[/yellow]")
            return None

        # Ignore last item because it's not complete (volume and price are still forming)
        current_data = current_data[:-1]

        # Calculate volume in USDT for all candles
        volumes_usdt = [float(candle[5]) * float(candle[4]) for candle in current_data]  # Volume * Close Price

        if len(volumes_usdt) < 4:
            console.print(f"[yellow]Skipping {symbol}: Not enough volume data[/yellow]")
            return None

        # Take last 2 volumes for comparison
        volumes_last_usdt = volumes_usdt[-2:]

        # Calculate median of all volumes except the last 2
        volumes_for_median_usdt = volumes_usdt[:-2]
        volume_median_usdt = median(volumes_for_median_usdt)

        # Skip if median volume is zero to avoid division by zero
        if volume_median_usdt == 0:
            console.print(f"[yellow]Skipping {symbol}: Median volume is zero[/yellow]")
            return None

        volume_last_avg_usdt = mean(volumes_last_usdt)  # Calculate the average of the last 2 volumes
        volume_change = ((volume_last_avg_usdt - volume_median_usdt) / volume_median_usdt) * 100

        # Calculate price change
        prices = [float(candle[4]) for candle in current_data]  # Close prices (index 4)
        price_change = ((prices[-1] - prices[0]) / prices[0]) * 100

        # Calculate price change of the last two candles
        price_change_last_two_candles = ((prices[-1] - prices[-2]) / prices[-2]) * 100

        # Calculate median volume of previous candles (excluding last two)
        median_volume_previous_candles_usdt = median(volumes_for_median_usdt)

        # Calculate median volume of the last two candles
        median_volume_last_two_candles_usdt = median(volumes_last_usdt)

        # Get last candle details
        last_candle = current_data[-1]
        last_candle_close_price = float(last_candle[4])  # Closing price of the last candle
        last_candle_volume_usdt = float(last_candle[5]) * last_candle_close_price  # Volume in USDT

        # Check if the last candle is green (close > open)
        last_candle_green = float(last_candle[4]) > float(last_candle[1])

        # Calculate side taker (buyer or seller dominated)
        taker_buy_volume = float(last_candle[9])  # Taker buy base asset volume
        taker_sell_volume = float(last_candle[5]) - taker_buy_volume  # Total volume - taker buy volume
        side_taker = "Buyer" if taker_buy_volume > taker_sell_volume else "Seller"

        # Calculate amount bought and sold in USDT
        amount_bought = float(last_candle[10])  # Taker buy quote asset volume (amount bought in USDT)
        amount_sold = float(last_candle[7]) - amount_bought  # Amount sold in USDT (quote_asset_volume - taker_buy_quote_asset_volume)

        # Fetch 1-day candle data
        one_day_data = await fetch_json(session, KLINES_URL, {
            'symbol': symbol,
            'interval': '1d',
            'limit': 1
        })

        if not one_day_data or len(one_day_data) < 1:
            console.print(f"[yellow]Skipping {symbol}: No 1-day data available[/yellow]")
            return None

        # Calculate 1-day price change
        one_day_candle = one_day_data[-1]
        one_day_open_price = float(one_day_candle[1])
        one_day_close_price = float(one_day_candle[4])
        price_change_1d = ((one_day_close_price - one_day_open_price) / one_day_open_price) * 100

        # Check for volume spike
        is_valid_spike = volume_last_avg_usdt > volume_median_usdt and volume_change >= args.threshold

        if not is_valid_spike:
            console.print(f"[yellow]Skipping {symbol}: No valid volume spike (Change: {volume_change:.2f}%)[/yellow]")
            return None

        return SymbolAnalysisResult(
            symbol=symbol,
            volume_change=volume_change,
            price_change=price_change,
            last_candle_volume_usdt=last_candle_volume_usdt,
            last_candle_green=last_candle_green,
            price_change_last_two_candles=price_change_last_two_candles,
            median_volume_previous_candles_usdt=median_volume_previous_candles_usdt,
            median_volume_last_two_candles_usdt=median_volume_last_two_candles_usdt,
            side_taker=side_taker,
            amount_bought=amount_bought,  # Amount bought in USDT
            amount_sold=amount_sold,  # Amount sold in USDT
            price_change_1d=price_change_1d  # 1-day price change
        )
    except Exception as e:
        console.print(f"[red]Error analyzing symbol {symbol}: {e}[/red]")
        return None


def create_table(results: List[SymbolAnalysisResult], last_updated: str, args: argparse.Namespace) -> Table:
    top_count = args.count
    table = Table(title=f"Binance Top {top_count} Potential Pumps\nUpdated: {last_updated}")
    table.add_column("Symbol", style="cyan", no_wrap=True)
    table.add_column("Volume Change", style="magenta", no_wrap=True)
    table.add_column("Price Change", style="magenta", no_wrap=True)
    table.add_column("Price Change (Last 2)", style="magenta", no_wrap=True)
    table.add_column("Median Volume (Prev) USDT", style="magenta", no_wrap=True)
    table.add_column("Median Volume (Last 2) USDT", style="magenta", no_wrap=True)
    table.add_column("Last Candle Volume (USDT)", style="magenta", no_wrap=True)
    table.add_column("Green Candle", style="magenta", no_wrap=True)
    table.add_column("Side Taker", style="magenta", no_wrap=True)
    table.add_column("Amount Bought (USDT)", style="magenta", no_wrap=True)
    table.add_column("Amount Sold (USDT)", style="magenta", no_wrap=True)
    table.add_column("Price Change (1d)", style="magenta", no_wrap=True)  # New column

    for res in results:
        symbol = res.symbol
        volume_change = round(res.volume_change)
        price_change = res.price_change
        price_change_last_two_candles = res.price_change_last_two_candles
        median_volume_previous_candles_usdt = res.median_volume_previous_candles_usdt
        median_volume_last_two_candles_usdt = res.median_volume_last_two_candles_usdt
        last_candle_volume_usdt = res.last_candle_volume_usdt
        last_candle_green = res.last_candle_green
        side_taker = res.side_taker
        amount_bought = res.amount_bought  # Amount bought in USDT
        amount_sold = res.amount_sold  # Amount sold in USDT
        price_change_1d = res.price_change_1d  # 1-day price change

        # Color coding
        volume_display = f"[green]{volume_change}%[/green]" if volume_change > 0 else f"[red]{volume_change}%[/red]"
        price_display = f"[green]{price_change:.2f}%[/green]" if price_change > 0 else f"[red]{price_change:.2f}%[/red]"
        price_change_last_two_display = f"[green]{price_change_last_two_candles:.2f}%[/green]" if price_change_last_two_candles > 0 else f"[red]{price_change_last_two_candles:.2f}%[/red]"
        median_volume_previous_display = f"[green]{format_volume(median_volume_previous_candles_usdt)}[/green]" if median_volume_previous_candles_usdt > 100000 else f"{format_volume(median_volume_previous_candles_usdt)}"
        median_volume_last_two_display = f"[green]{format_volume(median_volume_last_two_candles_usdt)}[/green]" if median_volume_last_two_candles_usdt > 100000 else f"{format_volume(median_volume_last_two_candles_usdt)}"
        last_candle_volume_usdt_display = f"[green]{format_volume(last_candle_volume_usdt)}[/green]" if last_candle_volume_usdt > 100000 else f"{format_volume(last_candle_volume_usdt)}"
        last_candle_green_display = "[bright_green]Yes[/bright_green]" if last_candle_green else "[bright_red]No[/bright_red]"
        side_taker_display = f"[bright_green]{side_taker}[/bright_green]" if side_taker == "Buyer" else f"[bright_red]{side_taker}[/bright_red]"
        amount_bought_display = f"[green]{format_volume(amount_bought)}[/green]" if amount_bought > amount_sold else f"{format_volume(amount_bought)}"
        amount_sold_display = f"[red]{format_volume(amount_sold)}[/red]" if amount_sold > amount_bought else f"{format_volume(amount_sold)}"
        price_change_1d_display = f"[green]{price_change_1d:.2f}%[/green]" if price_change_1d > 0 else f"[red]{price_change_1d:.2f}%[/red]"

        table.add_row(
            symbol,
            volume_display,
            price_display,
            price_change_last_two_display,
            median_volume_previous_display,
            median_volume_last_two_display,
            last_candle_volume_usdt_display,
            last_candle_green_display,
            side_taker_display,
            amount_bought_display,
            amount_sold_display,
            price_change_1d_display  # New column
        )
    return table


async def main(args: argparse.Namespace):
    range = make_more_human_readable_interval_label(args.range)
    console.print(f"\nSearching for symbols. Analysing volume on [yellow]{args.interval}[/yellow] intervals of [yellow]{range}[/yellow] range. Looking for [magenta]{args.threshold}%[/magenta] spikes!\n")

    async with aiohttp.ClientSession() as session:
        while True:
            start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            tasks = [
                analyze_symbol(session, symbol, args)
                for symbol in COINS
            ]

            results = []

            with Progress(
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    "[progress.percentage]{task.percentage:>1.0f}%",
                    TimeRemainingColumn(),
                    console=console
            ) as progress:
                task = progress.add_task(f"Analyzing {len(COINS)} symbols...", total=len(tasks))
                for coro in asyncio.as_completed(tasks):
                    result = await coro
                    if result:
                        results.append(result)
                    progress.advance(task)

            # Filter results: Keep only coins with Volume Change or Price Change above 0.5% and Price Change >= 0
            filtered_results = [
                res for res in results
                if (abs(res.volume_change) > 0.5 or abs(res.price_change) > 0.5) and res.price_change >= 0
            ]

            # Sort results by Volume Change (descending) and Price Change (descending)
            sorted_results = sorted(
                filtered_results,
                key=lambda x: (-x.volume_change, -x.price_change)
            )

            # Trim the list to top N
            final_results = sorted_results[:args.count]

            # Clear the terminal before printing new results
            console.clear()

            # Create table
            table = create_table(final_results, start_time, args)
            console.print(table)

            # Filter coins with Price Change (Last 2) > 3% for notifications
            high_price_change_coins = [
                res for res in final_results
                if (
                    ((res.price_change > 2 and res.price_change_last_two_candles > 2) or res.price_change_last_two_candles > 2) and res.price_change_last_two_candles < 9
                    and res.volume_change > 300
                    #and res.last_candle_green  # Ensure the last candle is green
                    and res.last_candle_volume_usdt > 100000  # Ensure last candle volume is above 100,000 USDT
                )
            ]

            # Send push notification if any coin meets the condition
            if high_price_change_coins:
                send_telegram_notification(title="🚀 Pump Detected!", coins=high_price_change_coins)

            if not args.watch:
                break

            await asyncio.sleep(args.wait)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Analyze volume changes of USDT coins on Binance Spot.')
    parser.add_argument('--interval', type=str, default="3m", help='Timeframe for volume analysis (e.g. 15m, 1h, 4h, 1d)')
    parser.add_argument('--range', type=str, default="4h", help='Time range for volume analysis (e.g. 4h, 1d, 3d)')
    parser.add_argument('--watch', action='store_true', help='Continuous monitoring mode')
    parser.add_argument('--threshold', type=str, default="50%", help='Volume change threshold, by default filter everything without 50% spikes')
    parser.add_argument('--wait', type=int, default=180, help='Interval for continuous monitoring mode')
    parser.add_argument('--count', type=int, default=12, help='Number of top symbols to display')
    args = parser.parse_args()

    args.max_concurrency = MAX_CONCURRENCY
    args.interval = make_more_human_readable_interval_label(args.interval)
    args.threshold = parse_percentage(args.threshold)

    try:
        asyncio.run(main(args))
    except KeyboardInterrupt:
        console.print("[red]Program terminated by user.[/red]")