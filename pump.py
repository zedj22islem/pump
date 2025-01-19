import asyncio
import platform
import sys
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
    'VIDTUSDT', 'SYSUSDT', 'FIDAUSDT', 'AGLDUSDT', 'RADUSDT', 'RAREUSDT', 'ADXUSDT', 'DARUSDT', 'MOVRUSDT', 'ENSUSDT',
    'POWRUSDT', 'JASMYUSDT', 'AMPUSDT', 'PYRUSDT', 'BICOUSDT', 'FLUXUSDT', 'VOXELUSDT', 'HIGHUSDT', 'PEOPLEUSDT',
    'ACHUSDT', 'GLMRUSDT', 'LOKAUSDT', 'SCRTUSDT', 'API3USDT', 'XNOUSDT', 'ALPINEUSDT', 'ASTRUSDT', 'GMTUSDT',
    'KDAUSDT', 'APEUSDT', 'STEEMUSDT', 'REIUSDT', 'OPUSDT', 'POLYXUSDT', 'APTUSDT', 'PHBUSDT', 'HOOKUSDT', 'MAGICUSDT',
    'GLMUSDT', 'PROMUSDT', 'QKCUSDT', 'IDUSDT', 'EDUUSDT', 'SUIUSDT', 'AERGOUSDT', 'SNTUSDT', 'COMBOUSDT', 'ARKMUSDT',
    'WLDUSDT', 'SEIUSDT', 'CYBERUSDT', 'ARKUSDT', 'IQUSDT', 'TIAUSDT', 'ORDIUSDT', 'BEAMXUSDT', 'PIVXUSDT', 'VICUSDT',
    'BLURUSDT', 'VANRYUSDT', '1000SATSUSDT', 'ACEUSDT', 'NFPUSDT', 'AIUSDT', 'XAIUSDT', 'MANTAUSDT', 'ALTUSDT',
    'PYTHUSDT', 'DYMUSDT', 'PDAUSDT', 'AXLUSDT', 'METISUSDT', 'WUSDT', 'TNSRUSDT', 'SAGAUSDT', 'TAOUSDT', 'OMNIUSDT',
    'NOTUSDT', 'IOUSDT', 'ZKUSDT', 'ZROUSDT', 'GUSDT', 'BANANAUSDT', 'RENDERUSDT', 'TONUSDT', 'SLFUSDT', 'POLUSDT',
    'CATIUSDT', 'SCRUSDT', 'KAIAUSDT', 'ACXUSDT', 'MOVEUSDT', 'MEUSDT', 'VANAUSDT', 'BIOUSDT'
]

# Type Definitions
KlineData = List[List[Any]]


@dataclass
class SymbolAnalysisResult:
    symbol: str
    volume_change: float
    price_change: float
    last_candle_volume_coin: float  # Volume in the coin
    last_candle_volume_usdt: float  # Volume in USDT
    sustained_volume_growth: bool = False
    sustained_price_growth: bool = False
    last_candle_green: bool = False  # New field to indicate if the last candle is green


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
    match = re.match(r'^(\d+)([mhd])$', timeframe)
    if not match:
        raise ValueError(f"Invalid timeframe format: {timeframe}")
    value, unit = match.groups()
    multipliers = {'m': 1, 'h': 60, 'd': 1440}  # m -> 1, h -> 60, d -> 1440 (24 * 60)
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


def find_sustained_growth(data, threshold=0.5, consecutive=2):
    count = 0  # Keeps track of consecutive growth periods
    for i in range(1, len(data)):
        # Calculate relative growth between consecutive items
        relative_change = (data[i] - data[i - 1]) / data[i - 1]

        # Check if the growth exceeds the threshold
        if relative_change > threshold:
            count += 1  # Increment if there's a growth above the threshold
            # If sustained growth occurs for the required number of consecutive periods
            if count >= consecutive:
                return i - consecutive + 1  # Return the start of the sustained growth
        else:
            count = 0  # Reset count if growth is interrupted
    return -1  # Return -1 if no sustained growth is found


def find_sustained_price_growth(prices, threshold=0.002, consecutive=2):
    count = 0  # Keeps track of consecutive growth periods
    for i in range(1, len(prices)):
        # Calculate relative growth between consecutive items
        relative_change = (prices[i] - prices[i - 1]) / prices[i - 1]

        # Check if the growth exceeds the threshold
        if relative_change > threshold:
            count += 1  # Increment if there's a growth above the threshold
            # If sustained growth occurs for the required number of consecutive periods
            if count >= consecutive:
                return i - consecutive + 1  # Return the start of the sustained growth
        else:
            count = 0  # Reset count if growth is interrupted
    return -1  # Return -1 if no sustained growth is found


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

        # Calculate volume change
        volumes = [float(candle[5]) for candle in current_data]  # Volume is the 6th element (index 5)
        if len(volumes) < 4:
            console.print(f"[yellow]Skipping {symbol}: Not enough volume data[/yellow]")
            return None

        # Take last 2 volumes for comparison
        volumes_last = volumes[-2:]

        # Calculate median of all volumes except the last 2
        volumes_for_median = volumes[:-2]
        volume_median = median(volumes_for_median)

        # Skip if median volume is zero to avoid division by zero
        if volume_median == 0:
            console.print(f"[yellow]Skipping {symbol}: Median volume is zero[/yellow]")
            return None

        volume_last_avg = mean(volumes_last)  # Calculate the average of the last 2 volumes
        volume_change = ((volume_last_avg - volume_median) / volume_median) * 100

        # Calculate price change
        prices = [float(candle[4]) for candle in current_data]  # Close prices (index 4)
        price_change = ((prices[-1] - prices[0]) / prices[0]) * 100

        # Get last candle details
        last_candle = current_data[-1]
        last_candle_volume_coin = float(last_candle[5])  # Volume in the coin
        last_candle_close_price = float(last_candle[4])  # Closing price of the last candle
        last_candle_volume_usdt = last_candle_volume_coin * last_candle_close_price  # Volume in USDT

        # Check if the last candle is green (close > open)
        last_candle_green = float(last_candle[4]) > float(last_candle[1])

        # Check for volume spike
        is_valid_spike = volume_last_avg > volume_median and volume_change >= args.threshold

        if not is_valid_spike:
            console.print(f"[yellow]Skipping {symbol}: No valid volume spike (Change: {volume_change:.2f}%)[/yellow]")
            return None

        # Check for sustained growth in volume and price
        sustained_volume_growth = find_sustained_growth(volumes, threshold=args.threshold / 100, consecutive=3) != -1
        sustained_price_growth = find_sustained_price_growth(prices, threshold=0.004, consecutive=3) != -1

        return SymbolAnalysisResult(
            symbol=symbol,
            volume_change=volume_change,
            price_change=price_change,
            last_candle_volume_coin=last_candle_volume_coin,
            last_candle_volume_usdt=last_candle_volume_usdt,
            sustained_volume_growth=sustained_volume_growth,
            sustained_price_growth=sustained_price_growth,
            last_candle_green=last_candle_green  # Add the new field
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
    table.add_column("Last Candle Volume (Coin)", style="magenta", no_wrap=True)
    table.add_column("Last Candle Volume (USDT)", style="magenta", no_wrap=True)
    table.add_column("Sustained Volume Growth", style="magenta", no_wrap=True)
    table.add_column("Sustained Price Growth", style="magenta", no_wrap=True)
    table.add_column("Green Candle", style="magenta", no_wrap=True)  # New column

    for res in results:
        symbol = res.symbol
        volume_change = round(res.volume_change)
        price_change = res.price_change
        last_candle_volume_coin = res.last_candle_volume_coin
        last_candle_volume_usdt = res.last_candle_volume_usdt
        sustained_volume_growth = res.sustained_volume_growth
        sustained_price_growth = res.sustained_price_growth
        last_candle_green = res.last_candle_green  # New field

        # Color coding
        volume_display = f"[green]{volume_change}%[/green]" if volume_change > 0 else f"[red]{volume_change}%[/red]"
        price_display = f"[green]{price_change:.2f}%[/green]" if price_change > 0 else f"[red]{price_change:.2f}%[/red]"
        last_candle_volume_coin_display = f"{last_candle_volume_coin:,.2f}"
        last_candle_volume_usdt_display = f"[green]{format_volume(last_candle_volume_usdt)}[/green]" if last_candle_volume_usdt > 100000 else f"{format_volume(last_candle_volume_usdt)}"
        sustained_volume_growth_display = "[bright_green]Yes[/bright_green]" if sustained_volume_growth else "[bright_red]No[/bright_red]"
        sustained_price_growth_display = "[bright_green]Yes[/bright_green]" if sustained_price_growth else "[bright_red]No[/bright_red]"
        last_candle_green_display = "[bright_green]Yes[/bright_green]" if last_candle_green else "[bright_red]No[/bright_red]"  # New display

        table.add_row(
            symbol,
            volume_display,
            price_display,
            last_candle_volume_coin_display,
            last_candle_volume_usdt_display,
            sustained_volume_growth_display,
            sustained_price_growth_display,
            last_candle_green_display  # Add the new column
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

            if not args.watch:
                break

            await asyncio.sleep(args.wait)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Analyze volume changes of USDT coins on Binance Spot.')
    parser.add_argument('--interval', type=str, default="15m", help='Timeframe for volume analysis (e.g. 15m, 1h, 4h, 1d)')
    parser.add_argument('--range', type=str, default="6h", help='Time range for volume analysis (e.g. 4h, 1d, 3d)')
    parser.add_argument('--watch', action='store_true', help='Continuous monitoring mode')
    parser.add_argument('--threshold', type=str, default="50%", help='Volume change threshold, by default filter everything without 50% spikes')
    parser.add_argument('--wait', type=int, default=60, help='Interval for continuous monitoring mode')
    parser.add_argument('--count', type=int, default=12, help='Number of top symbols to display')
    args = parser.parse_args()

    args.max_concurrency = MAX_CONCURRENCY
    args.interval = make_more_human_readable_interval_label(args.interval)
    args.threshold = parse_percentage(args.threshold)

    try:
        asyncio.run(main(args))
    except KeyboardInterrupt:
        console.print("[red]Program terminated by user.[/red]")

'''

import asyncio
import platform
import sys
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


   'EOSUSDT',  'IOTAUSDT', 'XLMUSDT', 'ONTUSDT',  'ETCUSDT', 'ICXUSDT', 'NULSUSDT', 'VETUSDT',  'LINKUSDT', 'ONGUSDT',
   'HOTUSDT', 'ZILUSDT',  'FETUSDT', 'BATUSDT', 'ZECUSDT', 'IOSTUSDT', 'CELRUSDT', 'DASHUSDT', 'THETAUSDT', 'ENJUSDT', 'ATOMUSDT',
     'TFUELUSDT', 'ONEUSDT', 'FTMUSDT', 'ALGOUSDT',  'DUSKUSDT', 'ANKRUSDT', 'WINUSDT', 'COSUSDT', 'MTLUSDT', 'DENTUSDT',   'CVCUSDT', 
     'CHZUSDT', 'BANDUSDT', 'XTZUSDT', 'RVNUSDT', 'HBARUSDT', 'NKNUSDT', 'STXUSDT',  'ARPAUSDT', 'IOTXUSDT', 'RLCUSDT', 'CTXCUSDT', 
    'OGNUSDT', 'LSKUSDT',  'LTOUSDT',   'STPTUSDT',  'DATAUSDT',  'CTSIUSDT', 'HIVEUSDT', 'CHRUSDT', 'ARDRUSDT', 'MDTUSDT',
    'STMXUSDT',  'LRCUSDT',   'SCUSDT', 'ZENUSDT',  'VTHOUSDT', 'DGBUSDT', 'SXPUSDT',  'DCRUSDT', 'STORJUSDT', 'MANAUSDT',   'KMDUSDT',
    'SANDUSDT',  'DOTUSDT',  'RSRUSDT',  'TRBUSDT',  'KSMUSDT', 'EGLDUSDT', 'DIAUSDT', 'RUNEUSDT', 'FIOUSDT', 'UMAUSDT', 
     'OXTUSDT',  'AVAXUSDT',  'UTKUSDT',   'NEARUSDT', 'FILUSDT',   'AXSUSDT', 'STRAXUSDT', 'ROSEUSDT', 'AVAUSDT', 'SKLUSDT', 'GRTUSDT', 
    'ATMUSDT', 'ASRUSDT', 'CELOUSDT', 'RIFUSDT',  'CKBUSDT', 'TWTUSDT', 'FIROUSDT', 'LITUSDT', 'SFPUSDT',
    'ACMUSDT',  'OMUSDT', 'PONDUSDT',  'ALICEUSDT', 'SUPERUSDT', 'CFXUSDT',  'PUNDIXUSDT', 'TLMUSDT',  'SLPUSDT',  'ICPUSDT', 'ARUSDT', 'MASKUSDT', 
    'LPTUSDT', 'XVGUSDT', 'ATAUSDT', 'GTCUSDT',  'PHAUSDT',  'DEXEUSDT',  'CLVUSDT', 'QNTUSDT', 'FLOWUSDT', 'MINAUSDT',   'REQUSDT',  'WAXPUSDT',  'XECUSDT',
    'ELFUSDT', 'VIDTUSDT',   'SYSUSDT',  'FIDAUSDT', 'AGLDUSDT', 'RADUSDT',  'RAREUSDT',   'ADXUSDT',  'DARUSDT',  'MOVRUSDT',  'ENSUSDT',   'POWRUSDT', 
    'JASMYUSDT', 'AMPUSDT', 'PYRUSDT',  'BICOUSDT', 'FLUXUSDT',  'VOXELUSDT', 'HIGHUSDT',  'PEOPLEUSDT',   'ACHUSDT',  'GLMRUSDT', 'LOKAUSDT', 'SCRTUSDT',
    'API3USDT',   'XNOUSDT',  'ALPINEUSDT',  'ASTRUSDT', 'GMTUSDT', 'KDAUSDT', 'APEUSDT',   'STEEMUSDT',  'REIUSDT',  'OPUSDT',    'POLYXUSDT',
    'APTUSDT',  'PHBUSDT', 'HOOKUSDT', 'MAGICUSDT', 'GLMUSDT','PROMUSDT', 'QKCUSDT', 'IDUSDT', 'EDUUSDT', 'SUIUSDT', 'AERGOUSDT',  'SNTUSDT', 'COMBOUSDT',  
    'ARKMUSDT', 'WLDUSDT',  'SEIUSDT', 'CYBERUSDT', 'ARKUSDT', 'IQUSDT',   'TIAUSDT', 'ORDIUSDT', 'BEAMXUSDT', 'PIVXUSDT', 'VICUSDT', 'BLURUSDT', 'VANRYUSDT', 
    '1000SATSUSDT', 'ACEUSDT', 'NFPUSDT', 'AIUSDT', 'XAIUSDT', 'MANTAUSDT', 'ALTUSDT', 'PYTHUSDT', 'DYMUSDT',    'PDAUSDT', 'AXLUSDT',  'METISUSDT',    'WUSDT', 
    'TNSRUSDT', 'SAGAUSDT',   'TAOUSDT', 'OMNIUSDT',   'NOTUSDT',  'IOUSDT', 'ZKUSDT',  'ZROUSDT', 'GUSDT', 
 'BANANAUSDT', 'RENDERUSDT', 'TONUSDT',  'SLFUSDT', 'POLUSDT',  'CATIUSDT',   'SCRUSDT' , 'KAIAUSDT',  'ACXUSDT','MOVEUSDT', 'MEUSDT',  'VANAUSDT',   'BIOUSDT'
 ]

# Type Definitions
KlineData = List[List[Any]]


@dataclass
class SymbolAnalysisResult:
    symbol: str
    volume_change: float
    price_change: float
    last_candle_volume_coin: float  # Volume in the coin
    last_candle_volume_usdt: float  # Volume in USDT
    sustained_volume_growth: bool = False
    sustained_price_growth: bool = False


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
    match = re.match(r'^(\d+)([mhd])$', timeframe)
    if not match:
        raise ValueError(f"Invalid timeframe format: {timeframe}")
    value, unit = match.groups()
    multipliers = {'m': 1, 'h': 60, 'd': 1440}  # m -> 1, h -> 60, d -> 1440 (24 * 60)
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


def find_sustained_growth(data, threshold=0.5, consecutive=2):
    count = 0  # Keeps track of consecutive growth periods
    for i in range(1, len(data)):
        # Calculate relative growth between consecutive items
        relative_change = (data[i] - data[i - 1]) / data[i - 1]

        # Check if the growth exceeds the threshold
        if relative_change > threshold:
            count += 1  # Increment if there's a growth above the threshold
            # If sustained growth occurs for the required number of consecutive periods
            if count >= consecutive:
                return i - consecutive + 1  # Return the start of the sustained growth
        else:
            count = 0  # Reset count if growth is interrupted
    return -1  # Return -1 if no sustained growth is found


def find_sustained_price_growth(prices, threshold=0.002, consecutive=2):
    count = 0  # Keeps track of consecutive growth periods
    for i in range(1, len(prices)):
        # Calculate relative growth between consecutive items
        relative_change = (prices[i] - prices[i - 1]) / prices[i - 1]

        # Check if the growth exceeds the threshold
        if relative_change > threshold:
            count += 1  # Increment if there's a growth above the threshold
            # If sustained growth occurs for the required number of consecutive periods
            if count >= consecutive:
                return i - consecutive + 1  # Return the start of the sustained growth
        else:
            count = 0  # Reset count if growth is interrupted
    return -1  # Return -1 if no sustained growth is found


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

        # Calculate volume change
        volumes = [float(candle[5]) for candle in current_data]  # Volume is the 6th element (index 5)
        if len(volumes) < 4:
            console.print(f"[yellow]Skipping {symbol}: Not enough volume data[/yellow]")
            return None

        # Take last 2 volumes for comparison
        volumes_last = volumes[-2:]

        # Calculate median of all volumes except the last 2
        volumes_for_median = volumes[:-2]
        volume_median = median(volumes_for_median)

        # Skip if median volume is zero to avoid division by zero
        if volume_median == 0:
            console.print(f"[yellow]Skipping {symbol}: Median volume is zero[/yellow]")
            return None

        volume_last_avg = mean(volumes_last)  # Calculate the average of the last 2 volumes
        volume_change = ((volume_last_avg - volume_median) / volume_median) * 100

        # Calculate price change
        prices = [float(candle[4]) for candle in current_data]  # Close prices (index 4)
        price_change = ((prices[-1] - prices[0]) / prices[0]) * 100

        # Get last candle details
        last_candle = current_data[-1]
        last_candle_volume_coin = float(last_candle[5])  # Volume in the coin
        last_candle_close_price = float(last_candle[4])  # Closing price of the last candle
        last_candle_volume_usdt = last_candle_volume_coin * last_candle_close_price  # Volume in USDT

        # Check for volume spike
        is_valid_spike = volume_last_avg > volume_median and volume_change >= args.threshold

        if not is_valid_spike:
            console.print(f"[yellow]Skipping {symbol}: No valid volume spike (Change: {volume_change:.2f}%)[/yellow]")
            return None

        # Check for sustained growth in volume and price
        sustained_volume_growth = find_sustained_growth(volumes, threshold=args.threshold / 100, consecutive=3) != -1
        sustained_price_growth = find_sustained_price_growth(prices, threshold=0.004, consecutive=3) != -1

        return SymbolAnalysisResult(
            symbol=symbol,
            volume_change=volume_change,
            price_change=price_change,
            last_candle_volume_coin=last_candle_volume_coin,
            last_candle_volume_usdt=last_candle_volume_usdt,
            sustained_volume_growth=sustained_volume_growth,
            sustained_price_growth=sustained_price_growth
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
    table.add_column("Last Candle Volume (Coin)", style="magenta", no_wrap=True)
    table.add_column("Last Candle Volume (USDT)", style="magenta", no_wrap=True)
    table.add_column("Sustained Volume Growth", style="magenta", no_wrap=True)
    table.add_column("Sustained Price Growth", style="magenta", no_wrap=True)

    for res in results:
        symbol = res.symbol
        volume_change = round(res.volume_change)
        price_change = res.price_change
        last_candle_volume_coin = res.last_candle_volume_coin
        last_candle_volume_usdt = res.last_candle_volume_usdt
        sustained_volume_growth = res.sustained_volume_growth
        sustained_price_growth = res.sustained_price_growth

        # Color coding
        volume_display = f"[green]{volume_change}%[/green]" if volume_change > 0 else f"[red]{volume_change}%[/red]"
        price_display = f"[green]{price_change:.2f}%[/green]" if price_change > 0 else f"[red]{price_change:.2f}%[/red]"
        last_candle_volume_coin_display = f"{last_candle_volume_coin:,.2f}"
        last_candle_volume_usdt_display = f"[green]{format_volume(last_candle_volume_usdt)}[/green]" if last_candle_volume_usdt > 100000 else f"{format_volume(last_candle_volume_usdt)}"
        sustained_volume_growth_display = "[bright_green]Yes[/bright_green]" if sustained_volume_growth else "[bright_red]No[/bright_red]"
        sustained_price_growth_display = "[bright_green]Yes[/bright_green]" if sustained_price_growth else "[bright_red]No[/bright_red]"

        table.add_row(
            symbol,
            volume_display,
            price_display,
            last_candle_volume_coin_display,
            last_candle_volume_usdt_display,
            sustained_volume_growth_display,
            sustained_price_growth_display
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

            if not args.watch:
                break

            await asyncio.sleep(args.wait)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Analyze volume changes of USDT coins on Binance Spot.')
    parser.add_argument('--interval', type=str, default="15m", help='Timeframe for volume analysis (e.g. 15m, 1h, 4h, 1d)')
    parser.add_argument('--range', type=str, default="6h", help='Time range for volume analysis (e.g. 4h, 1d, 3d)')
    parser.add_argument('--watch', action='store_true', help='Continuous monitoring mode')
    parser.add_argument('--threshold', type=str, default="50%", help='Volume change threshold, by default filter everything without 50% spikes')
    parser.add_argument('--wait', type=int, default=60, help='Interval for continuous monitoring mode')
    parser.add_argument('--count', type=int, default=12, help='Number of top symbols to display')
    args = parser.parse_args()

    args.max_concurrency = MAX_CONCURRENCY
    args.interval = make_more_human_readable_interval_label(args.interval)
    args.threshold = parse_percentage(args.threshold)

    try:
        asyncio.run(main(args))
    except KeyboardInterrupt:
        console.print("[red]Program terminated by user.[/red]")
'''

'''

import asyncio
import platform
import sys
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
 'EOSUSDT',  'IOTAUSDT',  'ONTUSDT', 'ICXUSDT',
'NULSUSDT', 'VETUSDT',  'LINKUSDT', 'ONGUSDT', 'ZILUSDT', 'FETUSDT',  'ZECUSDT', 'IOSTUSDT', 'CELRUSDT', 
'THETAUSDT',  'ATOMUSDT', 'TFUELUSDT', 'ONEUSDT',  'ALGOUSDT','DUSKUSDT',   'COSUSDT', 'MTLUSDT',   'WANUSDT',
'CVCUSDT',  'BANDUSDT', 'XTZUSDT',  'RVNUSDT', 'HBARUSDT', 'NKNUSDT', 'STXUSDT', 'KAVAUSDT', 'ARPAUSDT', 'IOTXUSDT', 
'RLCUSDT', 'CTXCUSDT','VITEUSDT',   'OGNUSDT',  'LSKUSDT', 'BNTUSDT', 'LTOUSDT',  'COTIUSDT','STPTUSDT', 'DATAUSDT',
'CTSIUSDT', 'HIVEUSDT', 'CHRUSDT', 'ARDRUSDT', 'MDTUSDT', 'STMXUSDT', 'KNCUSDT', 'SCUSDT', 'ZENUSDT', 'VTHOUSDT',
'DGBUSDT', 'SXPUSDT', 'DCRUSDT', 'STORJUSDT', 'BLZUSDT', 'KMDUSDT',  'NMRUSDT',  'RSRUSDT',  'TRBUSDT',
'EGLDUSDT', 'DIAUSDT', 'FIOUSDT', 'UMAUSDT',    'OXTUSDT', 'UTKUSDT', 'NEARUSDT', 'FILUSDT',  'CTKUSDT',  'AXSUSDT',
'STRAXUSDT', 'ROSEUSDT', 'AVAUSDT', 'SKLUSDT', 'GRTUSDT',    'CELOUSDT', 'RIFUSDT',  'CKBUSDT','FIROUSDT', 'LITUSDT',
'SFPUSDT',   'FISUSDT', 'OMUSDT', 'PONDUSDT', 'ALICEUSDT',   'SUPERUSDT', 'CFXUSDT',  'PUNDIXUSDT', 'TLMUSDT',  'FORTHUSDT', 
'BURGERUSDT','ICPUSDT', 'ARUSDT',  'LPTUSDT', 'XVGUSDT', 'ATAUSDT', 'GTCUSDT', 'ERNUSDT', 'PHAUSDT', 'MLNUSDT', 
'C98USDT', 'CLVUSDT', 'QNTUSDT', 'FLOWUSDT', 'MINAUSDT',  'FARMUSDT',    'REQUSDT', 'GHSTUSDT','WAXPUSDT', 'GNOUSDT', 
'XECUSDT', 'ELFUSDT',  'VIDTUSDT',  'GALAUSDT',   'SYSUSDT','DFUSDT', 'FIDAUSDT', 'AGLDUSDT', 'RADUSDT', 'BETAUSDT',
'RAREUSDT', 'LAZIOUSDT',  'ADXUSDT', 'AUCTIONUSDT', 'DARUSDT', 'MOVRUSDT',  'ENSUSDT',    'JASMYUSDT', 'AMPUSDT', 'PYRUSDT',
'BICOUSDT','FLUXUSDT',  'VOXELUSDT',    'ACHUSDT', 'IMXUSDT', 'GLMRUSDT', 'SCRTUSDT', 'API3USDT',   'XNOUSDT',  'ALPINEUSDT',
'TUSDT', 'ASTRUSDT', 'GMTUSDT', 'KDAUSDT','STEEMUSDT',  'REIUSDT',  'OPUSDT',  'STGUSDT',   'POLYXUSDT','APTUSDT', 
'PHBUSDT', 'HOOKUSDT', 'MAGICUSDT',   'PROSUSDT',  'SSVUSDT',  'AMBUSDT',  'GASUSDT', 'GLMUSDT',  'QKCUSDT',  'IDUSDT',
'EDUUSDT', 'SUIUSDT', 'AERGOUSDT',   'ASTUSDT', 'SNTUSDT', 'COMBOUSDT', 'MAVUSDT', 'PENDLEUSDT', 'ARKMUSDT','WLDUSDT',
'CYBERUSDT', 'ARKUSDT',  'IQUSDT', 'NTRNUSDT', 'TIAUSDT','BEAMXUSDT', 'PIVXUSDT', 'VICUSDT', 'BLURUSDT', 'VANRYUSDT',
'JTOUSDT',  'ACEUSDT', 'NFPUSDT', 'AIUSDT','XAIUSDT', 'MANTAUSDT', 'ALTUSDT',  'PYTHUSDT', 'RONINUSDT', 'DYMUSDT',
'PIXELUSDT',  'PORTALUSDT', 'PDAUSDT', 'AXLUSDT','METISUSDT',    'ENAUSDT', 'WUSDT', 'TNSRUSDT', 'SAGAUSDT', 'TAOUSDT',
'REZUSDT','NOTUSDT', 'IOUSDT', 'ZKUSDT',  'ZROUSDT',  'RENDERUSDT',   'POLUSDT',      'EIGENUSDT', 'SCRUSDT',
'LUMIAUSDT', 'KAIAUSDT',  'ACTUSDT',  'ACXUSDT',

]

# Type Definitions
KlineData = List[List[Any]]


@dataclass
class SymbolAnalysisResult:
    symbol: str
    volume_change: float
    price_change: float
    last_candle_volume_coin: float  # Volume in the coin
    last_candle_volume_usdt: float  # Volume in USDT
    sum_volumes_except_last_two: float  # Sum of volumes except the last two
    sum_volumes_last_two: float  # Sum of volumes of the last two
    sustained_volume_growth: bool = False
    sustained_price_growth: bool = False


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
    match = re.match(r'^(\d+)([mhd])$', timeframe)
    if not match:
        raise ValueError(f"Invalid timeframe format: {timeframe}")
    value, unit = match.groups()
    multipliers = {'m': 1, 'h': 60, 'd': 1440}  # m -> 1, h -> 60, d -> 1440 (24 * 60)
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


def find_sustained_growth(data, threshold=0.5, consecutive=2):
    count = 0  # Keeps track of consecutive growth periods
    for i in range(1, len(data)):
        # Calculate relative growth between consecutive items
        relative_change = (data[i] - data[i - 1]) / data[i - 1]

        # Check if the growth exceeds the threshold
        if relative_change > threshold:
            count += 1  # Increment if there's a growth above the threshold
            # If sustained growth occurs for the required number of consecutive periods
            if count >= consecutive:
                return i - consecutive + 1  # Return the start of the sustained growth
        else:
            count = 0  # Reset count if growth is interrupted
    return -1  # Return -1 if no sustained growth is found


def find_sustained_price_growth(prices, threshold=0.004, consecutive=2):
    count = 0  # Keeps track of consecutive growth periods
    for i in range(1, len(prices)):
        # Calculate relative growth between consecutive items
        relative_change = (prices[i] - prices[i - 1]) / prices[i - 1]

        # Check if the growth exceeds the threshold
        if relative_change > threshold:
            count += 1  # Increment if there's a growth above the threshold
            # If sustained growth occurs for the required number of consecutive periods
            if count >= consecutive:
                return i - consecutive + 1  # Return the start of the sustained growth
        else:
            count = 0  # Reset count if growth is interrupted
    return -1  # Return -1 if no sustained growth is found


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

        # Calculate volume change
        volumes = [float(candle[5]) for candle in current_data]  # Volume is the 6th element (index 5)
        if len(volumes) < 4:
            console.print(f"[yellow]Skipping {symbol}: Not enough volume data[/yellow]")
            return None

        # Take last 2 volumes for comparison
        volumes_last = volumes[-2:]

        # Calculate median of all volumes except the last 2
        volumes_for_median = volumes[:-2]
        volume_median = median(volumes_for_median)

        # Skip if median volume is zero to avoid division by zero
        if volume_median == 0:
            console.print(f"[yellow]Skipping {symbol}: Median volume is zero[/yellow]")
            return None

        volume_last_avg = mean(volumes_last)  # Calculate the average of the last 2 volumes
        volume_change = ((volume_last_avg - volume_median) / volume_median) * 100

        # Calculate price change
        prices = [float(candle[4]) for candle in current_data]  # Close prices (index 4)
        price_change = ((prices[-1] - prices[0]) / prices[0]) * 100

        # Get last candle details
        last_candle = current_data[-1]
        last_candle_volume_coin = float(last_candle[5])  # Volume in the coin
        last_candle_close_price = float(last_candle[4])  # Closing price of the last candle
        last_candle_volume_usdt = last_candle_volume_coin * last_candle_close_price  # Volume in USDT

        # Calculate sum of volumes except the last two
        sum_volumes_except_last_two = sum(volumes[:-2])

        # Calculate sum of volumes of the last two
        sum_volumes_last_two = sum(volumes[-2:])

        # Check for volume spike
        is_valid_spike = volume_last_avg > volume_median and volume_change >= args.threshold

        if not is_valid_spike:
            console.print(f"[yellow]Skipping {symbol}: No valid volume spike (Change: {volume_change:.2f}%)[/yellow]")
            return None

        # Check for sustained growth in volume and price
        sustained_volume_growth = find_sustained_growth(volumes, threshold=args.threshold / 100, consecutive=3) != -1
        sustained_price_growth = find_sustained_price_growth(prices, threshold=0.004, consecutive=3) != -1

        return SymbolAnalysisResult(
            symbol=symbol,
            volume_change=volume_change,
            price_change=price_change,
            last_candle_volume_coin=last_candle_volume_coin,
            last_candle_volume_usdt=last_candle_volume_usdt,
            sum_volumes_except_last_two=sum_volumes_except_last_two,
            sum_volumes_last_two=sum_volumes_last_two,
            sustained_volume_growth=sustained_volume_growth,
            sustained_price_growth=sustained_price_growth
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
    table.add_column("Last Candle Volume (Coin)", style="magenta", no_wrap=True)
    table.add_column("Last Candle Volume (USDT)", style="magenta", no_wrap=True)
    table.add_column("Sum Volumes Except Last 2", style="magenta", no_wrap=True)
    table.add_column("Sum Volumes Last 2", style="magenta", no_wrap=True)
    table.add_column("Sustained Volume Growth", style="magenta", no_wrap=True)
    table.add_column("Sustained Price Growth", style="magenta", no_wrap=True)

    for res in results:
        symbol = res.symbol
        volume_change = round(res.volume_change)
        price_change = res.price_change
        last_candle_volume_coin = res.last_candle_volume_coin
        last_candle_volume_usdt = res.last_candle_volume_usdt
        sum_volumes_except_last_two = res.sum_volumes_except_last_two
        sum_volumes_last_two = res.sum_volumes_last_two
        sustained_volume_growth = res.sustained_volume_growth
        sustained_price_growth = res.sustained_price_growth

        # Color coding
        volume_display = f"[green]{volume_change}%[/green]" if volume_change > 0 else f"[red]{volume_change}%[/red]"
        price_display = f"[green]{price_change:.2f}%[/green]" if price_change > 0 else f"[red]{price_change:.2f}%[/red]"
        last_candle_volume_coin_display = f"{last_candle_volume_coin:,.2f}"
        last_candle_volume_usdt_display = f"[green]{format_volume(last_candle_volume_usdt)}[/green]" if last_candle_volume_usdt > 100000 else f"{format_volume(last_candle_volume_usdt)}"
        sum_volumes_except_last_two_display = format_volume(sum_volumes_except_last_two)
        sum_volumes_last_two_display = f"[green]{format_volume(sum_volumes_last_two)}[/green]" if sum_volumes_last_two > 100000 else f"{format_volume(sum_volumes_last_two)}"
        sustained_volume_growth_display = "[bright_green]Yes[/bright_green]" if sustained_volume_growth else "[bright_red]No[/bright_red]"
        sustained_price_growth_display = "[bright_green]Yes[/bright_green]" if sustained_price_growth else "[bright_red]No[/bright_red]"

        table.add_row(
            symbol,
            volume_display,
            price_display,
            last_candle_volume_coin_display,
            last_candle_volume_usdt_display,
            sum_volumes_except_last_two_display,
            sum_volumes_last_two_display,
            sustained_volume_growth_display,
            sustained_price_growth_display
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

            if not args.watch:
                break

            await asyncio.sleep(args.wait)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Analyze volume changes of USDT coins on Binance Spot.')
    parser.add_argument('--interval', type=str, default="15m", help='Timeframe for volume analysis (e.g. 15m, 1h, 4h, 1d)')
    parser.add_argument('--range', type=str, default="6h", help='Time range for volume analysis (e.g. 4h, 1d, 3d)')
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
'''
'''
import asyncio
import platform
import sys
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
  'EOSUSDT',  'IOTAUSDT',  'ONTUSDT', 'ICXUSDT',
'NULSUSDT', 'VETUSDT',  'LINKUSDT', 'ONGUSDT', 'ZILUSDT', 'FETUSDT',  'ZECUSDT', 'IOSTUSDT', 'CELRUSDT', 
'THETAUSDT',  'ATOMUSDT', 'TFUELUSDT', 'ONEUSDT',  'ALGOUSDT','DUSKUSDT',   'COSUSDT', 'MTLUSDT',   'WANUSDT',
'CVCUSDT',  'BANDUSDT', 'XTZUSDT',  'RVNUSDT', 'HBARUSDT', 'NKNUSDT', 'STXUSDT', 'KAVAUSDT', 'ARPAUSDT', 'IOTXUSDT', 
'RLCUSDT', 'CTXCUSDT','VITEUSDT',   'OGNUSDT',  'LSKUSDT', 'BNTUSDT', 'LTOUSDT',  'COTIUSDT','STPTUSDT', 'DATAUSDT',
'CTSIUSDT', 'HIVEUSDT', 'CHRUSDT', 'ARDRUSDT', 'MDTUSDT', 'STMXUSDT', 'KNCUSDT', 'SCUSDT', 'ZENUSDT', 'VTHOUSDT',
'DGBUSDT', 'SXPUSDT', 'DCRUSDT', 'STORJUSDT', 'BLZUSDT', 'KMDUSDT',  'NMRUSDT',  'RSRUSDT',  'TRBUSDT',
'EGLDUSDT', 'DIAUSDT', 'FIOUSDT', 'UMAUSDT',    'OXTUSDT', 'UTKUSDT', 'NEARUSDT', 'FILUSDT',  'CTKUSDT',  'AXSUSDT',
'STRAXUSDT', 'ROSEUSDT', 'AVAUSDT', 'SKLUSDT', 'GRTUSDT',    'CELOUSDT', 'RIFUSDT',  'CKBUSDT','FIROUSDT', 'LITUSDT',
'SFPUSDT',   'FISUSDT', 'OMUSDT', 'PONDUSDT', 'ALICEUSDT',   'SUPERUSDT', 'CFXUSDT',  'PUNDIXUSDT', 'TLMUSDT',  'FORTHUSDT', 
'BURGERUSDT','ICPUSDT', 'ARUSDT',  'LPTUSDT', 'XVGUSDT', 'ATAUSDT', 'GTCUSDT', 'ERNUSDT', 'PHAUSDT', 'MLNUSDT', 
'C98USDT', 'CLVUSDT', 'QNTUSDT', 'FLOWUSDT', 'MINAUSDT',  'FARMUSDT',    'REQUSDT', 'GHSTUSDT','WAXPUSDT', 'GNOUSDT', 
'XECUSDT', 'ELFUSDT',  'VIDTUSDT',  'GALAUSDT',   'SYSUSDT','DFUSDT', 'FIDAUSDT', 'AGLDUSDT', 'RADUSDT', 'BETAUSDT',
'RAREUSDT', 'LAZIOUSDT',  'ADXUSDT', 'AUCTIONUSDT', 'DARUSDT', 'MOVRUSDT',  'ENSUSDT',    'JASMYUSDT', 'AMPUSDT', 'PYRUSDT',
'BICOUSDT','FLUXUSDT',  'VOXELUSDT',    'ACHUSDT', 'IMXUSDT', 'GLMRUSDT', 'SCRTUSDT', 'API3USDT',   'XNOUSDT',  'ALPINEUSDT',
'TUSDT', 'ASTRUSDT', 'GMTUSDT', 'KDAUSDT','STEEMUSDT',  'REIUSDT',  'OPUSDT',  'STGUSDT',   'POLYXUSDT','APTUSDT', 
'PHBUSDT', 'HOOKUSDT', 'MAGICUSDT',   'PROSUSDT',  'SSVUSDT',  'AMBUSDT',  'GASUSDT', 'GLMUSDT',  'QKCUSDT',  'IDUSDT',
'EDUUSDT', 'SUIUSDT', 'AERGOUSDT',   'ASTUSDT', 'SNTUSDT', 'COMBOUSDT', 'MAVUSDT', 'PENDLEUSDT', 'ARKMUSDT','WLDUSDT',
'CYBERUSDT', 'ARKUSDT',  'IQUSDT', 'NTRNUSDT', 'TIAUSDT','BEAMXUSDT', 'PIVXUSDT', 'VICUSDT', 'BLURUSDT', 'VANRYUSDT',
'JTOUSDT',  'ACEUSDT', 'NFPUSDT', 'AIUSDT','XAIUSDT', 'MANTAUSDT', 'ALTUSDT',  'PYTHUSDT', 'RONINUSDT', 'DYMUSDT',
'PIXELUSDT',  'PORTALUSDT', 'PDAUSDT', 'AXLUSDT','METISUSDT',    'ENAUSDT', 'WUSDT', 'TNSRUSDT', 'SAGAUSDT', 'TAOUSDT',
'REZUSDT','NOTUSDT', 'IOUSDT', 'ZKUSDT',  'ZROUSDT',  'RENDERUSDT',   'POLUSDT',      'EIGENUSDT', 'SCRUSDT',
'LUMIAUSDT', 'KAIAUSDT',  'ACTUSDT',  'ACXUSDT',

]

# Type Definitions
KlineData = List[List[Any]]


@dataclass
class SymbolAnalysisResult:
    symbol: str
    volume_change: float
    price_change: float
    last_candle_volume_coin: float  # Volume in the coin
    last_candle_volume_usdt: float  # Volume in USDT
    sustained_volume_growth: bool = False
    sustained_price_growth: bool = False


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
    match = re.match(r'^(\d+)([mhd])$', timeframe)
    if not match:
        raise ValueError(f"Invalid timeframe format: {timeframe}")
    value, unit = match.groups()
    multipliers = {'m': 1, 'h': 60, 'd': 1440}  # m -> 1, h -> 60, d -> 1440 (24 * 60)
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


def find_sustained_growth(data, threshold=0.5, consecutive=2):
    count = 0  # Keeps track of consecutive growth periods
    for i in range(1, len(data)):
        # Calculate relative growth between consecutive items
        relative_change = (data[i] - data[i - 1]) / data[i - 1]

        # Check if the growth exceeds the threshold
        if relative_change > threshold:
            count += 1  # Increment if there's a growth above the threshold
            # If sustained growth occurs for the required number of consecutive periods
            if count >= consecutive:
                return i - consecutive + 1  # Return the start of the sustained growth
        else:
            count = 0  # Reset count if growth is interrupted
    return -1  # Return -1 if no sustained growth is found


def find_sustained_price_growth(prices, threshold=0.004, consecutive=2):
    count = 0  # Keeps track of consecutive growth periods
    for i in range(1, len(prices)):
        # Calculate relative growth between consecutive items
        relative_change = (prices[i] - prices[i - 1]) / prices[i - 1]

        # Check if the growth exceeds the threshold
        if relative_change > threshold:
            count += 1  # Increment if there's a growth above the threshold
            # If sustained growth occurs for the required number of consecutive periods
            if count >= consecutive:
                return i - consecutive + 1  # Return the start of the sustained growth
        else:
            count = 0  # Reset count if growth is interrupted
    return -1  # Return -1 if no sustained growth is found


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

        # Calculate volume change
        volumes = [float(candle[5]) for candle in current_data]  # Volume is the 6th element (index 5)
        if len(volumes) < 4:
            console.print(f"[yellow]Skipping {symbol}: Not enough volume data[/yellow]")
            return None

        # Take last 2 volumes for comparison
        volumes_last = volumes[-2:]

        # Calculate median of all volumes except the last 2
        volumes_for_median = volumes[:-2]
        volume_median = median(volumes_for_median)

        # Skip if median volume is zero to avoid division by zero
        if volume_median == 0:
            console.print(f"[yellow]Skipping {symbol}: Median volume is zero[/yellow]")
            return None

        volume_last_avg = mean(volumes_last)  # Calculate the average of the last 2 volumes
        volume_change = ((volume_last_avg - volume_median) / volume_median) * 100

        # Calculate price change
        prices = [float(candle[4]) for candle in current_data]  # Close prices (index 4)
        price_change = ((prices[-1] - prices[0]) / prices[0]) * 100

        # Get last candle details
        last_candle = current_data[-1]
        last_candle_volume_coin = float(last_candle[5])  # Volume in the coin
        last_candle_close_price = float(last_candle[4])  # Closing price of the last candle
        last_candle_volume_usdt = last_candle_volume_coin * last_candle_close_price  # Volume in USDT

        # Check for volume spike
        is_valid_spike = volume_last_avg > volume_median and volume_change >= args.threshold

        if not is_valid_spike:
            console.print(f"[yellow]Skipping {symbol}: No valid volume spike (Change: {volume_change:.2f}%)[/yellow]")
            return None

        # Check for sustained growth in volume and price
        sustained_volume_growth = find_sustained_growth(volumes, threshold=args.threshold / 100, consecutive=3) != -1
        sustained_price_growth = find_sustained_price_growth(prices, threshold=0.004, consecutive=3) != -1

        return SymbolAnalysisResult(
            symbol=symbol,
            volume_change=volume_change,
            price_change=price_change,
            last_candle_volume_coin=last_candle_volume_coin,
            last_candle_volume_usdt=last_candle_volume_usdt,
            sustained_volume_growth=sustained_volume_growth,
            sustained_price_growth=sustained_price_growth
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
    table.add_column("Last Candle Volume (Coin)", style="magenta", no_wrap=True)
    table.add_column("Last Candle Volume (USDT)", style="magenta", no_wrap=True)
    table.add_column("Sustained Volume Growth", style="magenta", no_wrap=True)
    table.add_column("Sustained Price Growth", style="magenta", no_wrap=True)

    for res in results:
        symbol = res.symbol
        volume_change = round(res.volume_change)
        price_change = res.price_change
        last_candle_volume_coin = res.last_candle_volume_coin
        last_candle_volume_usdt = res.last_candle_volume_usdt
        sustained_volume_growth = res.sustained_volume_growth
        sustained_price_growth = res.sustained_price_growth

        # Color coding
        volume_display = f"[green]{volume_change}%[/green]" if volume_change > 0 else f"[red]{volume_change}%[/red]"
        price_display = f"[green]{price_change:.2f}%[/green]" if price_change > 0 else f"[red]{price_change:.2f}%[/red]"
        last_candle_volume_coin_display = f"{last_candle_volume_coin:,.2f}"
        last_candle_volume_usdt_display = f"[green]{format_volume(last_candle_volume_usdt)}[/green]" if last_candle_volume_usdt > 100000 else f"{format_volume(last_candle_volume_usdt)}"
        sustained_volume_growth_display = "[bright_green]Yes[/bright_green]" if sustained_volume_growth else "[bright_red]No[/bright_red]"
        sustained_price_growth_display = "[bright_green]Yes[/bright_green]" if sustained_price_growth else "[bright_red]No[/bright_red]"

        table.add_row(
            symbol,
            volume_display,
            price_display,
            last_candle_volume_coin_display,
            last_candle_volume_usdt_display,
            sustained_volume_growth_display,
            sustained_price_growth_display
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

            if not args.watch:
                break

            await asyncio.sleep(args.wait)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Analyze volume changes of USDT coins on Binance Spot.')
    parser.add_argument('--interval', type=str, default="15m", help='Timeframe for volume analysis (e.g. 15m, 1h, 4h, 1d)')
    parser.add_argument('--range', type=str, default="6h", help='Time range for volume analysis (e.g. 4h, 1d, 3d)')
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
'''
'''
import asyncio
import platform
import sys
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
'EOSUSDT',  'IOTAUSDT',  'ONTUSDT', 'ICXUSDT',
'NULSUSDT', 'VETUSDT',  'LINKUSDT', 'ONGUSDT', 'ZILUSDT', 'FETUSDT',  'ZECUSDT', 'IOSTUSDT', 'CELRUSDT', 
'THETAUSDT',  'ATOMUSDT', 'TFUELUSDT', 'ONEUSDT',  'ALGOUSDT','DUSKUSDT',   'COSUSDT', 'MTLUSDT',   'WANUSDT',
'CVCUSDT',  'BANDUSDT', 'XTZUSDT',  'RVNUSDT', 'HBARUSDT', 'NKNUSDT', 'STXUSDT', 'KAVAUSDT', 'ARPAUSDT', 'IOTXUSDT', 
'RLCUSDT', 'CTXCUSDT','VITEUSDT',   'OGNUSDT',  'LSKUSDT', 'BNTUSDT', 'LTOUSDT',  'COTIUSDT','STPTUSDT', 'DATAUSDT',
'CTSIUSDT', 'HIVEUSDT', 'CHRUSDT', 'ARDRUSDT', 'MDTUSDT', 'STMXUSDT', 'KNCUSDT', 'SCUSDT', 'ZENUSDT', 'VTHOUSDT',
'DGBUSDT', 'SXPUSDT', 'DCRUSDT', 'STORJUSDT', 'BLZUSDT', 'KMDUSDT',  'NMRUSDT',  'RSRUSDT',  'TRBUSDT',
'EGLDUSDT', 'DIAUSDT', 'FIOUSDT', 'UMAUSDT',    'OXTUSDT', 'UTKUSDT', 'NEARUSDT', 'FILUSDT',  'CTKUSDT',  'AXSUSDT',
'STRAXUSDT', 'ROSEUSDT', 'AVAUSDT', 'SKLUSDT', 'GRTUSDT',    'CELOUSDT', 'RIFUSDT',  'CKBUSDT','FIROUSDT', 'LITUSDT',
'SFPUSDT',   'FISUSDT', 'OMUSDT', 'PONDUSDT', 'ALICEUSDT',   'SUPERUSDT', 'CFXUSDT',  'PUNDIXUSDT', 'TLMUSDT',  'FORTHUSDT', 
'BURGERUSDT','ICPUSDT', 'ARUSDT',  'LPTUSDT', 'XVGUSDT', 'ATAUSDT', 'GTCUSDT', 'ERNUSDT', 'PHAUSDT', 'MLNUSDT', 
'C98USDT', 'CLVUSDT', 'QNTUSDT', 'FLOWUSDT', 'MINAUSDT',  'FARMUSDT',    'REQUSDT', 'GHSTUSDT','WAXPUSDT', 'GNOUSDT', 
'XECUSDT', 'ELFUSDT',  'VIDTUSDT',  'GALAUSDT',   'SYSUSDT','DFUSDT', 'FIDAUSDT', 'AGLDUSDT', 'RADUSDT', 'BETAUSDT',
'RAREUSDT', 'LAZIOUSDT',  'ADXUSDT', 'AUCTIONUSDT', 'DARUSDT', 'MOVRUSDT',  'ENSUSDT',    'JASMYUSDT', 'AMPUSDT', 'PYRUSDT',
'BICOUSDT','FLUXUSDT',  'VOXELUSDT',    'ACHUSDT', 'IMXUSDT', 'GLMRUSDT', 'SCRTUSDT', 'API3USDT',   'XNOUSDT',  'ALPINEUSDT',
'TUSDT', 'ASTRUSDT', 'GMTUSDT', 'KDAUSDT','STEEMUSDT',  'REIUSDT',  'OPUSDT',  'STGUSDT',   'POLYXUSDT','APTUSDT', 
'PHBUSDT', 'HOOKUSDT', 'MAGICUSDT',   'PROSUSDT',  'SSVUSDT',  'AMBUSDT',  'GASUSDT', 'GLMUSDT',  'QKCUSDT',  'IDUSDT',
'EDUUSDT', 'SUIUSDT', 'AERGOUSDT',   'ASTUSDT', 'SNTUSDT', 'COMBOUSDT', 'MAVUSDT', 'PENDLEUSDT', 'ARKMUSDT','WLDUSDT',
'CYBERUSDT', 'ARKUSDT',  'IQUSDT', 'NTRNUSDT', 'TIAUSDT','BEAMXUSDT', 'PIVXUSDT', 'VICUSDT', 'BLURUSDT', 'VANRYUSDT',
'JTOUSDT',  'ACEUSDT', 'NFPUSDT', 'AIUSDT','XAIUSDT', 'MANTAUSDT', 'ALTUSDT',  'PYTHUSDT', 'RONINUSDT', 'DYMUSDT',
'PIXELUSDT',  'PORTALUSDT', 'PDAUSDT', 'AXLUSDT','METISUSDT',    'ENAUSDT', 'WUSDT', 'TNSRUSDT', 'SAGAUSDT', 'TAOUSDT',
'REZUSDT','NOTUSDT', 'IOUSDT', 'ZKUSDT',  'ZROUSDT',  'RENDERUSDT',   'POLUSDT',      'EIGENUSDT', 'SCRUSDT',
'LUMIAUSDT', 'KAIAUSDT',  'ACTUSDT',  'ACXUSDT',

]

# Type Definitions
KlineData = List[List[Any]]


@dataclass
class SymbolAnalysisResult:
    symbol: str
    volume_change: float
    price_change: float
    last_candle_volume_coin: float  # Volume in the coin
    last_candle_volume_usdt: float  # Volume in USDT
    sustained_volume_growth: bool = False
    sustained_price_growth: bool = False


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
    match = re.match(r'^(\d+)([mhd])$', timeframe)
    if not match:
        raise ValueError(f"Invalid timeframe format: {timeframe}")
    value, unit = match.groups()
    multipliers = {'m': 1, 'h': 60, 'd': 1440}  # m -> 1, h -> 60, d -> 1440 (24 * 60)
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


def find_sustained_growth(data, threshold=0.5, consecutive=2):
    count = 0  # Keeps track of consecutive growth periods
    for i in range(1, len(data)):
        # Calculate relative growth between consecutive items
        relative_change = (data[i] - data[i - 1]) / data[i - 1]

        # Check if the growth exceeds the threshold
        if relative_change > threshold:
            count += 1  # Increment if there's a growth above the threshold
            # If sustained growth occurs for the required number of consecutive periods
            if count >= consecutive:
                return i - consecutive + 1  # Return the start of the sustained growth
        else:
            count = 0  # Reset count if growth is interrupted
    return -1  # Return -1 if no sustained growth is found


def find_sustained_price_growth(prices, threshold=0.004, consecutive=2):
    count = 0  # Keeps track of consecutive growth periods
    for i in range(1, len(prices)):
        # Calculate relative growth between consecutive items
        relative_change = (prices[i] - prices[i - 1]) / prices[i - 1]

        # Check if the growth exceeds the threshold
        if relative_change > threshold:
            count += 1  # Increment if there's a growth above the threshold
            # If sustained growth occurs for the required number of consecutive periods
            if count >= consecutive:
                return i - consecutive + 1  # Return the start of the sustained growth
        else:
            count = 0  # Reset count if growth is interrupted
    return -1  # Return -1 if no sustained growth is found


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

        # Calculate volume change
        volumes = [float(candle[5]) for candle in current_data]  # Volume is the 6th element (index 5)
        if len(volumes) < 4:
            console.print(f"[yellow]Skipping {symbol}: Not enough volume data[/yellow]")
            return None

        # Take last 2 volumes for comparison
        volumes_last = volumes[-2:]

        # Calculate median of all volumes except the last 2
        volumes_for_median = volumes[:-2]
        volume_median = median(volumes_for_median)

        # Skip if median volume is zero to avoid division by zero
        if volume_median == 0:
            console.print(f"[yellow]Skipping {symbol}: Median volume is zero[/yellow]")
            return None

        volume_last_avg = mean(volumes_last)  # Calculate the average of the last 2 volumes
        volume_change = ((volume_last_avg - volume_median) / volume_median) * 100

        # Calculate price change
        prices = [float(candle[4]) for candle in current_data]  # Close prices (index 4)
        price_change = ((prices[-1] - prices[0]) / prices[0]) * 100

        # Get last candle details
        last_candle = current_data[-1]
        last_candle_volume_coin = float(last_candle[5])  # Volume in the coin
        last_candle_close_price = float(last_candle[4])  # Closing price of the last candle
        last_candle_volume_usdt = last_candle_volume_coin * last_candle_close_price  # Volume in USDT

        # Check for volume spike
        is_valid_spike = volume_last_avg > volume_median and volume_change >= args.threshold

        if not is_valid_spike:
            console.print(f"[yellow]Skipping {symbol}: No valid volume spike (Change: {volume_change:.2f}%)[/yellow]")
            return None

        # Check for sustained growth in volume and price
        sustained_volume_growth = find_sustained_growth(volumes, threshold=args.threshold / 100, consecutive=3) != -1
        sustained_price_growth = find_sustained_price_growth(prices, threshold=0.004, consecutive=3) != -1

        return SymbolAnalysisResult(
            symbol=symbol,
            volume_change=volume_change,
            price_change=price_change,
            last_candle_volume_coin=last_candle_volume_coin,
            last_candle_volume_usdt=last_candle_volume_usdt,
            sustained_volume_growth=sustained_volume_growth,
            sustained_price_growth=sustained_price_growth
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
    table.add_column("Last Candle Volume (Coin)", style="magenta", no_wrap=True)
    table.add_column("Last Candle Volume (USDT)", style="magenta", no_wrap=True)
    table.add_column("Sustained Volume Growth", style="magenta", no_wrap=True)
    table.add_column("Sustained Price Growth", style="magenta", no_wrap=True)

    for res in results:
        symbol = res.symbol
        volume_change = round(res.volume_change)
        price_change = res.price_change
        last_candle_volume_coin = res.last_candle_volume_coin
        last_candle_volume_usdt = res.last_candle_volume_usdt
        sustained_volume_growth = res.sustained_volume_growth
        sustained_price_growth = res.sustained_price_growth

        # Color coding
        volume_display = f"[green]{volume_change}%[/green]" if volume_change > 0 else f"[red]{volume_change}%[/red]"
        price_display = f"[green]{price_change:.2f}%[/green]" if price_change > 0 else f"[red]{price_change:.2f}%[/red]"
        last_candle_volume_coin_display = f"{last_candle_volume_coin:,.2f}"
        last_candle_volume_usdt_display = format_volume(last_candle_volume_usdt)
        sustained_volume_growth_display = "[bright_green]Yes[/bright_green]" if sustained_volume_growth else "[bright_red]No[/bright_red]"
        sustained_price_growth_display = "[bright_green]Yes[/bright_green]" if sustained_price_growth else "[bright_red]No[/bright_red]"

        table.add_row(
            symbol,
            volume_display,
            price_display,
            last_candle_volume_coin_display,
            last_candle_volume_usdt_display,
            sustained_volume_growth_display,
            sustained_price_growth_display
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

            if not args.watch:
                break

            await asyncio.sleep(args.wait)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Analyze volume changes of USDT coins on Binance Spot.')
    parser.add_argument('--interval', type=str, default="15m", help='Timeframe for volume analysis (e.g. 15m, 1h, 4h, 1d)')
    parser.add_argument('--range', type=str, default="6h", help='Time range for volume analysis (e.g. 4h, 1d, 3d)')
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

'''
'''
import asyncio
import platform
import sys
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
   'EOSUSDT',  'IOTAUSDT',  'ONTUSDT', 'ICXUSDT',
'NULSUSDT', 'VETUSDT',  'LINKUSDT', 'ONGUSDT', 'ZILUSDT', 'FETUSDT',  'ZECUSDT', 'IOSTUSDT', 'CELRUSDT', 
'THETAUSDT',  'ATOMUSDT', 'TFUELUSDT', 'ONEUSDT',  'ALGOUSDT','DUSKUSDT',   'COSUSDT', 'MTLUSDT',   'WANUSDT',
'CVCUSDT',  'BANDUSDT', 'XTZUSDT',  'RVNUSDT', 'HBARUSDT', 'NKNUSDT', 'STXUSDT', 'KAVAUSDT', 'ARPAUSDT', 'IOTXUSDT', 
'RLCUSDT', 'CTXCUSDT','VITEUSDT',   'OGNUSDT',  'LSKUSDT', 'BNTUSDT', 'LTOUSDT',  'COTIUSDT','STPTUSDT', 'DATAUSDT',
'CTSIUSDT', 'HIVEUSDT', 'CHRUSDT', 'ARDRUSDT', 'MDTUSDT', 'STMXUSDT', 'KNCUSDT', 'SCUSDT', 'ZENUSDT', 'VTHOUSDT',
'DGBUSDT', 'SXPUSDT', 'DCRUSDT', 'STORJUSDT', 'BLZUSDT', 'KMDUSDT',  'NMRUSDT',  'RSRUSDT',  'TRBUSDT',
'EGLDUSDT', 'DIAUSDT', 'FIOUSDT', 'UMAUSDT',    'OXTUSDT', 'UTKUSDT', 'NEARUSDT', 'FILUSDT',  'CTKUSDT',  'AXSUSDT',
'STRAXUSDT', 'ROSEUSDT', 'AVAUSDT', 'SKLUSDT', 'GRTUSDT',    'CELOUSDT', 'RIFUSDT',  'CKBUSDT','FIROUSDT', 'LITUSDT',
'SFPUSDT',   'FISUSDT', 'OMUSDT', 'PONDUSDT', 'ALICEUSDT',   'SUPERUSDT', 'CFXUSDT',  'PUNDIXUSDT', 'TLMUSDT',  'FORTHUSDT', 
'BURGERUSDT','ICPUSDT', 'ARUSDT',  'LPTUSDT', 'XVGUSDT', 'ATAUSDT', 'GTCUSDT', 'ERNUSDT', 'PHAUSDT', 'MLNUSDT', 
'C98USDT', 'CLVUSDT', 'QNTUSDT', 'FLOWUSDT', 'MINAUSDT',  'FARMUSDT',    'REQUSDT', 'GHSTUSDT','WAXPUSDT', 'GNOUSDT', 
'XECUSDT', 'ELFUSDT',  'VIDTUSDT',  'GALAUSDT',   'SYSUSDT','DFUSDT', 'FIDAUSDT', 'AGLDUSDT', 'RADUSDT', 'BETAUSDT',
'RAREUSDT', 'LAZIOUSDT',  'ADXUSDT', 'AUCTIONUSDT', 'DARUSDT', 'MOVRUSDT',  'ENSUSDT',    'JASMYUSDT', 'AMPUSDT', 'PYRUSDT',
'BICOUSDT','FLUXUSDT',  'VOXELUSDT',    'ACHUSDT', 'IMXUSDT', 'GLMRUSDT', 'SCRTUSDT', 'API3USDT',   'XNOUSDT',  'ALPINEUSDT',
'TUSDT', 'ASTRUSDT', 'GMTUSDT', 'KDAUSDT','STEEMUSDT',  'REIUSDT',  'OPUSDT',  'STGUSDT',   'POLYXUSDT','APTUSDT', 
'PHBUSDT', 'HOOKUSDT', 'MAGICUSDT',   'PROSUSDT',  'SSVUSDT',  'AMBUSDT',  'GASUSDT', 'GLMUSDT',  'QKCUSDT',  'IDUSDT',
'EDUUSDT', 'SUIUSDT', 'AERGOUSDT',   'ASTUSDT', 'SNTUSDT', 'COMBOUSDT', 'MAVUSDT', 'PENDLEUSDT', 'ARKMUSDT','WLDUSDT',
'CYBERUSDT', 'ARKUSDT',  'IQUSDT', 'NTRNUSDT', 'TIAUSDT','BEAMXUSDT', 'PIVXUSDT', 'VICUSDT', 'BLURUSDT', 'VANRYUSDT',
'JTOUSDT',  'ACEUSDT', 'NFPUSDT', 'AIUSDT','XAIUSDT', 'MANTAUSDT', 'ALTUSDT',  'PYTHUSDT', 'RONINUSDT', 'DYMUSDT',
'PIXELUSDT',  'PORTALUSDT', 'PDAUSDT', 'AXLUSDT','METISUSDT',    'ENAUSDT', 'WUSDT', 'TNSRUSDT', 'SAGAUSDT', 'TAOUSDT',
'REZUSDT','NOTUSDT', 'IOUSDT', 'ZKUSDT',  'ZROUSDT',  'RENDERUSDT',   'POLUSDT',      'EIGENUSDT', 'SCRUSDT',
'LUMIAUSDT', 'KAIAUSDT',  'ACTUSDT',  'ACXUSDT',

]

# Type Definitions
KlineData = List[List[Any]]


@dataclass
class SymbolAnalysisResult:
    symbol: str
    volume_change: float
    price_change: float
    last_candle_volume_coin: float  # Volume in the coin
    last_candle_volume_usdt: float  # Volume in USDT
    sustained_volume_growth: bool = False
    sustained_price_growth: bool = False


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
    match = re.match(r'^(\d+)([mhd])$', timeframe)
    if not match:
        raise ValueError(f"Invalid timeframe format: {timeframe}")
    value, unit = match.groups()
    multipliers = {'m': 1, 'h': 60, 'd': 1440}  # m -> 1, h -> 60, d -> 1440 (24 * 60)
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

        # Calculate volume change
        volumes = [float(candle[5]) for candle in current_data]  # Volume is the 6th element (index 5)
        if len(volumes) < 4:
            console.print(f"[yellow]Skipping {symbol}: Not enough volume data[/yellow]")
            return None

        # Take last 2 volumes for comparison
        volumes_last = volumes[-2:]

        # Calculate median of all volumes except the last 2
        volumes_for_median = volumes[:-2]
        volume_median = median(volumes_for_median)

        # Skip if median volume is zero to avoid division by zero
        if volume_median == 0:
            console.print(f"[yellow]Skipping {symbol}: Median volume is zero[/yellow]")
            return None

        volume_last_avg = mean(volumes_last)  # Calculate the average of the last 2 volumes
        volume_change = ((volume_last_avg - volume_median) / volume_median) * 100

        # Calculate price change
        prices = [float(candle[4]) for candle in current_data]  # Close prices (index 4)
        price_change = ((prices[-1] - prices[0]) / prices[0]) * 100

        # Get last candle details
        last_candle = current_data[-1]
        last_candle_volume_coin = float(last_candle[5])  # Volume in the coin
        last_candle_close_price = float(last_candle[4])  # Closing price of the last candle
        last_candle_volume_usdt = last_candle_volume_coin * last_candle_close_price  # Volume in USDT

        # Check for volume spike
        is_valid_spike = volume_last_avg > volume_median and volume_change >= args.threshold

        if not is_valid_spike:
            console.print(f"[yellow]Skipping {symbol}: No valid volume spike (Change: {volume_change:.2f}%)[/yellow]")
            return None

        # Check for sustained growth in volume and price
        sustained_volume_growth = find_sustained_growth(volumes, threshold=args.threshold / 100, consecutive=3) != -1
        sustained_price_growth = find_sustained_growth(prices, threshold=args.threshold / 100, consecutive=3) != -1

        return SymbolAnalysisResult(
            symbol=symbol,
            volume_change=volume_change,
            price_change=price_change,
            last_candle_volume_coin=last_candle_volume_coin,
            last_candle_volume_usdt=last_candle_volume_usdt,
            sustained_volume_growth=sustained_volume_growth,
            sustained_price_growth=sustained_price_growth
        )
    except Exception as e:
        console.print(f"[red]Error analyzing symbol {symbol}: {e}[/red]")
        return None


def find_sustained_growth(data, threshold=0.5, consecutive=2):
    count = 0  # Keeps track of consecutive growth periods
    for i in range(1, len(data)):
        # Calculate relative growth between consecutive items
        relative_change = (data[i] - data[i - 1]) / data[i - 1]

        # Check if the growth exceeds the threshold
        if relative_change > threshold:
            count += 1  # Increment if there's a growth above the threshold
            # If sustained growth occurs for the required number of consecutive periods
            if count >= consecutive:
                return i - consecutive + 1  # Return the start of the sustained growth
        else:
            count = 0  # Reset count if growth is interrupted
    return -1  # Return -1 if no sustained growth is found


def create_table(results: List[SymbolAnalysisResult], last_updated: str, args: argparse.Namespace) -> Table:
    top_count = args.count
    table = Table(title=f"Binance Top {top_count} Potential Pumps\nUpdated: {last_updated}")
    table.add_column("Symbol", style="cyan", no_wrap=True)
    table.add_column("Volume Change", style="magenta", no_wrap=True)
    table.add_column("Price Change", style="magenta", no_wrap=True)
    table.add_column("Last Candle Volume (Coin)", style="magenta", no_wrap=True)
    table.add_column("Last Candle Volume (USDT)", style="magenta", no_wrap=True)
    table.add_column("Sustained Volume Growth", style="magenta", no_wrap=True)
    table.add_column("Sustained Price Growth", style="magenta", no_wrap=True)

    for res in results:
        symbol = res.symbol
        volume_change = round(res.volume_change)
        price_change = res.price_change
        last_candle_volume_coin = res.last_candle_volume_coin
        last_candle_volume_usdt = res.last_candle_volume_usdt
        sustained_volume_growth = res.sustained_volume_growth
        sustained_price_growth = res.sustained_price_growth

        # Color coding
        volume_display = f"[green]{volume_change}%[/green]" if volume_change > 0 else f"[red]{volume_change}%[/red]"
        price_display = f"[green]{price_change:.2f}%[/green]" if price_change > 0 else f"[red]{price_change:.2f}%[/red]"
        last_candle_volume_coin_display = f"{last_candle_volume_coin:,.2f}"
        last_candle_volume_usdt_display = format_volume(last_candle_volume_usdt)
        sustained_volume_growth_display = "[bright_green]Yes[/bright_green]" if sustained_volume_growth else "[bright_red]No[/bright_red]"
        sustained_price_growth_display = "[bright_green]Yes[/bright_green]" if sustained_price_growth else "[bright_red]No[/bright_red]"

        table.add_row(
            symbol,
            volume_display,
            price_display,
            last_candle_volume_coin_display,
            last_candle_volume_usdt_display,
            sustained_volume_growth_display,
            sustained_price_growth_display
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

            if not args.watch:
                break

            await asyncio.sleep(args.wait)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Analyze volume changes of USDT coins on Binance Spot.')
    parser.add_argument('--interval', type=str, default="15m", help='Timeframe for volume analysis (e.g. 15m, 1h, 4h, 1d)')
    parser.add_argument('--range', type=str, default="6h", help='Time range for volume analysis (e.g. 4h, 1d, 3d)')
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
'''
'''
import asyncio
import platform
import sys
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
  'EOSUSDT',  'IOTAUSDT',  'ONTUSDT', 'ICXUSDT',
'NULSUSDT', 'VETUSDT',  'LINKUSDT', 'ONGUSDT', 'ZILUSDT', 'FETUSDT',  'ZECUSDT', 'IOSTUSDT', 'CELRUSDT', 
'THETAUSDT',  'ATOMUSDT', 'TFUELUSDT', 'ONEUSDT',  'ALGOUSDT','DUSKUSDT',   'COSUSDT', 'MTLUSDT',   'WANUSDT',
'CVCUSDT',  'BANDUSDT', 'XTZUSDT',  'RVNUSDT', 'HBARUSDT', 'NKNUSDT', 'STXUSDT', 'KAVAUSDT', 'ARPAUSDT', 'IOTXUSDT', 
'RLCUSDT', 'CTXCUSDT','VITEUSDT',   'OGNUSDT',  'LSKUSDT', 'BNTUSDT', 'LTOUSDT',  'COTIUSDT','STPTUSDT', 'DATAUSDT',
'CTSIUSDT', 'HIVEUSDT', 'CHRUSDT', 'ARDRUSDT', 'MDTUSDT', 'STMXUSDT', 'KNCUSDT', 'SCUSDT', 'ZENUSDT', 'VTHOUSDT',
'DGBUSDT', 'SXPUSDT', 'DCRUSDT', 'STORJUSDT', 'BLZUSDT', 'KMDUSDT',  'NMRUSDT',  'RSRUSDT',  'TRBUSDT',
'EGLDUSDT', 'DIAUSDT', 'FIOUSDT', 'UMAUSDT',    'OXTUSDT', 'UTKUSDT', 'NEARUSDT', 'FILUSDT',  'CTKUSDT',  'AXSUSDT',
'STRAXUSDT', 'ROSEUSDT', 'AVAUSDT', 'SKLUSDT', 'GRTUSDT',    'CELOUSDT', 'RIFUSDT',  'CKBUSDT','FIROUSDT', 'LITUSDT',
'SFPUSDT',   'FISUSDT', 'OMUSDT', 'PONDUSDT', 'ALICEUSDT',   'SUPERUSDT', 'CFXUSDT',  'PUNDIXUSDT', 'TLMUSDT',  'FORTHUSDT', 
'BURGERUSDT','ICPUSDT', 'ARUSDT',  'LPTUSDT', 'XVGUSDT', 'ATAUSDT', 'GTCUSDT', 'ERNUSDT', 'PHAUSDT', 'MLNUSDT', 
'C98USDT', 'CLVUSDT', 'QNTUSDT', 'FLOWUSDT', 'MINAUSDT',  'FARMUSDT',    'REQUSDT', 'GHSTUSDT','WAXPUSDT', 'GNOUSDT', 
'XECUSDT', 'ELFUSDT',  'VIDTUSDT',  'GALAUSDT',   'SYSUSDT','DFUSDT', 'FIDAUSDT', 'AGLDUSDT', 'RADUSDT', 'BETAUSDT',
'RAREUSDT', 'LAZIOUSDT',  'ADXUSDT', 'AUCTIONUSDT', 'DARUSDT', 'MOVRUSDT',  'ENSUSDT',    'JASMYUSDT', 'AMPUSDT', 'PYRUSDT',
'BICOUSDT','FLUXUSDT',  'VOXELUSDT',    'ACHUSDT', 'IMXUSDT', 'GLMRUSDT', 'SCRTUSDT', 'API3USDT',   'XNOUSDT',  'ALPINEUSDT',
'TUSDT', 'ASTRUSDT', 'GMTUSDT', 'KDAUSDT','STEEMUSDT',  'REIUSDT',  'OPUSDT',  'STGUSDT',   'POLYXUSDT','APTUSDT', 
'PHBUSDT', 'HOOKUSDT', 'MAGICUSDT',   'PROSUSDT',  'SSVUSDT',  'AMBUSDT',  'GASUSDT', 'GLMUSDT',  'QKCUSDT',  'IDUSDT',
'EDUUSDT', 'SUIUSDT', 'AERGOUSDT',   'ASTUSDT', 'SNTUSDT', 'COMBOUSDT', 'MAVUSDT', 'PENDLEUSDT', 'ARKMUSDT','WLDUSDT',
'CYBERUSDT', 'ARKUSDT',  'IQUSDT', 'NTRNUSDT', 'TIAUSDT','BEAMXUSDT', 'PIVXUSDT', 'VICUSDT', 'BLURUSDT', 'VANRYUSDT',
'JTOUSDT',  'ACEUSDT', 'NFPUSDT', 'AIUSDT','XAIUSDT', 'MANTAUSDT', 'ALTUSDT',  'PYTHUSDT', 'RONINUSDT', 'DYMUSDT',
'PIXELUSDT',  'PORTALUSDT', 'PDAUSDT', 'AXLUSDT','METISUSDT',    'ENAUSDT', 'WUSDT', 'TNSRUSDT', 'SAGAUSDT', 'TAOUSDT',
'REZUSDT','NOTUSDT', 'IOUSDT', 'ZKUSDT',  'ZROUSDT',  'RENDERUSDT',   'POLUSDT',      'EIGENUSDT', 'SCRUSDT',
'LUMIAUSDT', 'KAIAUSDT',  'ACTUSDT',  'ACXUSDT',

]

# Type Definitions
KlineData = List[List[Any]]


@dataclass
class SymbolAnalysisResult:
    symbol: str
    volume_change: float
    price_change: float
    last_candle_volume_coin: float  # Volume in the coin
    min_passed: int = 0
    is_price_spike: bool = False
    sustained_volume_growth: bool = False  # New field
    sustained_price_growth: bool = False  # New field


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
    match = re.match(r'^(\d+)([mhd])$', timeframe)
    if not match:
        raise ValueError(f"Invalid timeframe format: {timeframe}")
    value, unit = match.groups()
    multipliers = {'m': 1, 'h': 60, 'd': 1440}  # m -> 1, h -> 60, d -> 1440 (24 * 60)
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

        # Calculate volume change
        volumes = [float(candle[5]) for candle in current_data]  # Volume is the 6th element (index 5)
        if len(volumes) < 4:
            console.print(f"[yellow]Skipping {symbol}: Not enough volume data[/yellow]")
            return None

        # Take last 2 volumes for comparison
        volumes_last = volumes[-2:]

        # Calculate median of all volumes except the last 2
        volumes_for_median = volumes[:-2]
        volume_median = median(volumes_for_median)

        # Skip if median volume is zero to avoid division by zero
        if volume_median == 0:
            console.print(f"[yellow]Skipping {symbol}: Median volume is zero[/yellow]")
            return None

        volume_last_avg = mean(volumes_last)  # Calculate the average of the last 2 volumes
        volume_change = ((volume_last_avg - volume_median) / volume_median) * 100

        # Calculate price change
        prices = [float(candle[4]) for candle in current_data]  # Close prices (index 4)
        price_change = ((prices[-1] - prices[0]) / prices[0]) * 100

        # Get last candle details
        last_candle = current_data[-1]
        last_candle_volume_coin = float(last_candle[5])  # Volume in the coin

        # Check for volume spike
        is_valid_spike = volume_last_avg > volume_median and volume_change >= args.threshold

        if not is_valid_spike:
            console.print(f"[yellow]Skipping {symbol}: No valid volume spike (Change: {volume_change:.2f}%)[/yellow]")
            return None

        # Check for sustained growth in volume and price
        min_passed = 0
        is_price_spike = False
        sustained_volume_growth = find_sustained_growth(volumes, threshold=args.threshold / 100, consecutive=3) != -1
        sustained_price_growth = find_sustained_growth(prices, threshold=args.threshold / 100, consecutive=3) != -1

        sustained_growth_index = find_sustained_growth(volumes, threshold=args.threshold / 100, consecutive=3)
        if sustained_growth_index != -1:
            # Count items from this index to the end
            count_items_after = len(volumes) - sustained_growth_index
            min_passed = count_items_after * convert_interval_to_minutes(args.interval)
            # Average diff between max and min of prices
            avg_minmax_before_list = [abs(float(candle[2]) - float(candle[3])) for candle in current_data[:sustained_growth_index]]
            avg_minmax_after_list = [abs(float(candle[2]) - float(candle[3])) for candle in current_data[sustained_growth_index:]]
            avg_minmax_before, avg_minmax_after = mean(avg_minmax_before_list), mean(avg_minmax_after_list)
            price_change_threshold_ratio = 0.25
            is_price_spike = avg_minmax_after > avg_minmax_before * price_change_threshold_ratio

        return SymbolAnalysisResult(
            symbol=symbol,
            volume_change=volume_change,
            price_change=price_change,
            last_candle_volume_coin=last_candle_volume_coin,
            min_passed=min_passed,
            is_price_spike=is_price_spike,
            sustained_volume_growth=sustained_volume_growth,  # New field
            sustained_price_growth=sustained_price_growth  # New field
        )
    except Exception as e:
        console.print(f"[red]Error analyzing symbol {symbol}: {e}[/red]")
        return None


def find_sustained_growth(data, threshold=0.5, consecutive=2):
    count = 0  # Keeps track of consecutive growth periods
    for i in range(1, len(data)):
        # Calculate relative growth between consecutive items
        relative_change = (data[i] - data[i - 1]) / data[i - 1]

        # Check if the growth exceeds the threshold
        if relative_change > threshold:
            count += 1  # Increment if there's a growth above the threshold
            # If sustained growth occurs for the required number of consecutive periods
            if count >= consecutive:
                return i - consecutive + 1  # Return the start of the sustained growth
        else:
            count = 0  # Reset count if growth is interrupted
    return -1  # Return -1 if no sustained growth is found


def create_table(results: List[SymbolAnalysisResult], last_updated: str, args: argparse.Namespace) -> Table:
    top_count = args.count
    table = Table(title=f"Binance Top {top_count} Potential Pumps\nUpdated: {last_updated}")
    table.add_column("Symbol", style="cyan", no_wrap=True)
    table.add_column("Volume Change", style="magenta", no_wrap=True)
    table.add_column("Price Change", style="magenta", no_wrap=True)
    table.add_column("Last Candle Volume (Coin)", style="magenta", no_wrap=True)
    table.add_column("Time Since Spike", style="magenta", no_wrap=True)
    table.add_column("Price Spike", style="magenta", no_wrap=True)
    table.add_column("Sustained Volume Growth", style="magenta", no_wrap=True)  # New column
    table.add_column("Sustained Price Growth", style="magenta", no_wrap=True)  # New column

    for res in results:
        symbol = res.symbol
        volume_change = round(res.volume_change)
        price_change = res.price_change
        last_candle_volume_coin = res.last_candle_volume_coin
        min_passed = res.min_passed
        time_passed = minutes_to_human_readable(min_passed)
        is_price_spike = res.is_price_spike
        sustained_volume_growth = res.sustained_volume_growth
        sustained_price_growth = res.sustained_price_growth

        # Color coding
        volume_display = f"[green]{volume_change}%[/green]" if volume_change > 0 else f"[red]{volume_change}%[/red]"
        price_display = f"[green]{price_change:.2f}%[/green]" if price_change > 0 else f"[red]{price_change:.2f}%[/red]"
        last_candle_volume_coin_display = f"[bright_green]{last_candle_volume_coin:,.2f}[/bright_green]" if last_candle_volume_coin > 1000000 else f"{last_candle_volume_coin:,.2f}"
        time_passed_display = f"[bright_yellow]{time_passed}[/bright_yellow]" if min_passed < 60 else f"[red]{time_passed}[/red]"
        price_spike_display = "[bright_red]Yes[/bright_red]" if is_price_spike else "[bright_green]No[/bright_green]"
        sustained_volume_growth_display = "[bright_green]Yes[/bright_green]" if sustained_volume_growth else "[bright_red]No[/bright_red]"
        sustained_price_growth_display = "[bright_green]Yes[/bright_green]" if sustained_price_growth else "[bright_red]No[/bright_red]"

        table.add_row(
            symbol,
            volume_display,
            price_display,
            last_candle_volume_coin_display,
            time_passed_display,
            price_spike_display,
            sustained_volume_growth_display,
            sustained_price_growth_display
        )
    return table


def minutes_to_human_readable(minutes):
    d, minutes = divmod(minutes, 1440)
    h, m = divmod(minutes, 60)
    return f"{d}d " * (d > 0) + f"{h}h " * (h > 0) + f"{m}m" * (m > 0) or "0m"


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

            if not args.watch:
                break

            await asyncio.sleep(args.wait)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Analyze volume changes of USDT coins on Binance Spot.')
    parser.add_argument('--interval', type=str, default="15m", help='Timeframe for volume analysis (e.g. 15m, 1h, 4h, 1d)')
    parser.add_argument('--range', type=str, default="6h", help='Time range for volume analysis (e.g. 4h, 1d, 3d)')
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
'''
'''
import asyncio
import platform
import sys
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
  'EOSUSDT',  'IOTAUSDT',  'ONTUSDT', 'ICXUSDT',
'NULSUSDT', 'VETUSDT',  'LINKUSDT', 'ONGUSDT', 'ZILUSDT', 'FETUSDT',  'ZECUSDT', 'IOSTUSDT', 'CELRUSDT', 
'THETAUSDT',  'ATOMUSDT', 'TFUELUSDT', 'ONEUSDT',  'ALGOUSDT','DUSKUSDT',   'COSUSDT', 'MTLUSDT',   'WANUSDT',
'CVCUSDT',  'BANDUSDT', 'XTZUSDT',  'RVNUSDT', 'HBARUSDT', 'NKNUSDT', 'STXUSDT', 'KAVAUSDT', 'ARPAUSDT', 'IOTXUSDT', 
'RLCUSDT', 'CTXCUSDT','VITEUSDT',   'OGNUSDT',  'LSKUSDT', 'BNTUSDT', 'LTOUSDT',  'COTIUSDT','STPTUSDT', 'DATAUSDT',
'CTSIUSDT', 'HIVEUSDT', 'CHRUSDT', 'ARDRUSDT', 'MDTUSDT', 'STMXUSDT', 'KNCUSDT', 'SCUSDT', 'ZENUSDT', 'VTHOUSDT',
'DGBUSDT', 'SXPUSDT', 'DCRUSDT', 'STORJUSDT', 'BLZUSDT', 'KMDUSDT',  'NMRUSDT',  'RSRUSDT',  'TRBUSDT',
'EGLDUSDT', 'DIAUSDT', 'FIOUSDT', 'UMAUSDT',    'OXTUSDT', 'UTKUSDT', 'NEARUSDT', 'FILUSDT',  'CTKUSDT',  'AXSUSDT',
'STRAXUSDT', 'ROSEUSDT', 'AVAUSDT', 'SKLUSDT', 'GRTUSDT',    'CELOUSDT', 'RIFUSDT',  'CKBUSDT','FIROUSDT', 'LITUSDT',
'SFPUSDT',   'FISUSDT', 'OMUSDT', 'PONDUSDT', 'ALICEUSDT',   'SUPERUSDT', 'CFXUSDT',  'PUNDIXUSDT', 'TLMUSDT',  'FORTHUSDT', 
'BURGERUSDT','ICPUSDT', 'ARUSDT',  'LPTUSDT', 'XVGUSDT', 'ATAUSDT', 'GTCUSDT', 'ERNUSDT', 'PHAUSDT', 'MLNUSDT', 
'C98USDT', 'CLVUSDT', 'QNTUSDT', 'FLOWUSDT', 'MINAUSDT',  'FARMUSDT',    'REQUSDT', 'GHSTUSDT','WAXPUSDT', 'GNOUSDT', 
'XECUSDT', 'ELFUSDT',  'VIDTUSDT',  'GALAUSDT',   'SYSUSDT','DFUSDT', 'FIDAUSDT', 'AGLDUSDT', 'RADUSDT', 'BETAUSDT',
'RAREUSDT', 'LAZIOUSDT',  'ADXUSDT', 'AUCTIONUSDT', 'DARUSDT', 'MOVRUSDT',  'ENSUSDT',    'JASMYUSDT', 'AMPUSDT', 'PYRUSDT',
'BICOUSDT','FLUXUSDT',  'VOXELUSDT',    'ACHUSDT', 'IMXUSDT', 'GLMRUSDT', 'SCRTUSDT', 'API3USDT',   'XNOUSDT',  'ALPINEUSDT',
'TUSDT', 'ASTRUSDT', 'GMTUSDT', 'KDAUSDT','STEEMUSDT',  'REIUSDT',  'OPUSDT',  'STGUSDT',   'POLYXUSDT','APTUSDT', 
'PHBUSDT', 'HOOKUSDT', 'MAGICUSDT',   'PROSUSDT',  'SSVUSDT',  'AMBUSDT',  'GASUSDT', 'GLMUSDT',  'QKCUSDT',  'IDUSDT',
'EDUUSDT', 'SUIUSDT', 'AERGOUSDT',   'ASTUSDT', 'SNTUSDT', 'COMBOUSDT', 'MAVUSDT', 'PENDLEUSDT', 'ARKMUSDT','WLDUSDT',
'CYBERUSDT', 'ARKUSDT',  'IQUSDT', 'NTRNUSDT', 'TIAUSDT','BEAMXUSDT', 'PIVXUSDT', 'VICUSDT', 'BLURUSDT', 'VANRYUSDT',
'JTOUSDT',  'ACEUSDT', 'NFPUSDT', 'AIUSDT','XAIUSDT', 'MANTAUSDT', 'ALTUSDT',  'PYTHUSDT', 'RONINUSDT', 'DYMUSDT',
'PIXELUSDT',  'PORTALUSDT', 'PDAUSDT', 'AXLUSDT','METISUSDT',    'ENAUSDT', 'WUSDT', 'TNSRUSDT', 'SAGAUSDT', 'TAOUSDT',
'REZUSDT','NOTUSDT', 'IOUSDT', 'ZKUSDT',  'ZROUSDT',  'RENDERUSDT',   'POLUSDT',      'EIGENUSDT', 'SCRUSDT',
'LUMIAUSDT', 'KAIAUSDT',  'ACTUSDT',  'ACXUSDT',

]

# Type Definitions
KlineData = List[List[Any]]


@dataclass
class SymbolAnalysisResult:
    symbol: str
    volume_change: float
    price_change: float
    last_candle_volume_coin: float  # Volume in the coin
    min_passed: int = 0
    is_price_spike: bool = False


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
    match = re.match(r'^(\d+)([mhd])$', timeframe)
    if not match:
        raise ValueError(f"Invalid timeframe format: {timeframe}")
    value, unit = match.groups()
    multipliers = {'m': 1, 'h': 60, 'd': 1440}  # m -> 1, h -> 60, d -> 1440 (24 * 60)
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

        # Calculate volume change
        volumes = [float(candle[5]) for candle in current_data]  # Volume is the 6th element (index 5)
        if len(volumes) < 4:
            console.print(f"[yellow]Skipping {symbol}: Not enough volume data[/yellow]")
            return None

        # Take last 2 volumes for comparison
        volumes_last = volumes[-2:]

        # Calculate median of all volumes except the last 2
        volumes_for_median = volumes[:-2]
        volume_median = median(volumes_for_median)

        # Skip if median volume is zero to avoid division by zero
        if volume_median == 0:
            console.print(f"[yellow]Skipping {symbol}: Median volume is zero[/yellow]")
            return None

        volume_last_avg = mean(volumes_last)  # Calculate the average of the last 2 volumes
        volume_change = ((volume_last_avg - volume_median) / volume_median) * 100

        # Calculate price change
        prices = [float(candle[4]) for candle in current_data]  # Close prices (index 4)
        price_change = ((prices[-1] - prices[0]) / prices[0]) * 100

        # Get last candle details
        last_candle = current_data[-1]
        last_candle_volume_coin = float(last_candle[5])  # Volume in the coin

        # Check for volume spike
        is_valid_spike = volume_last_avg > volume_median and volume_change >= args.threshold

        if not is_valid_spike:
            console.print(f"[yellow]Skipping {symbol}: No valid volume spike (Change: {volume_change:.2f}%)[/yellow]")
            return None

        # Check for sustained growth and price spike
        min_passed = 0
        is_price_spike = False
        sustained_growth_index = find_sustained_growth(volumes, threshold=args.threshold / 100, consecutive=3)
        if sustained_growth_index != -1:
            # Count items from this index to the end
            count_items_after = len(volumes) - sustained_growth_index
            min_passed = count_items_after * convert_interval_to_minutes(args.interval)
            # Average diff between max and min of prices
            avg_minmax_before_list = [abs(float(candle[2]) - float(candle[3])) for candle in current_data[:sustained_growth_index]]
            avg_minmax_after_list = [abs(float(candle[2]) - float(candle[3])) for candle in current_data[sustained_growth_index:]]
            avg_minmax_before, avg_minmax_after = mean(avg_minmax_before_list), mean(avg_minmax_after_list)
            price_change_threshold_ratio = 0.25
            is_price_spike = avg_minmax_after > avg_minmax_before * price_change_threshold_ratio

        return SymbolAnalysisResult(
            symbol=symbol,
            volume_change=volume_change,
            price_change=price_change,
            last_candle_volume_coin=last_candle_volume_coin,
            min_passed=min_passed,
            is_price_spike=is_price_spike
        )
    except Exception as e:
        console.print(f"[red]Error analyzing symbol {symbol}: {e}[/red]")
        return None


def find_sustained_growth(data, threshold=0.5, consecutive=2):
    count = 0  # Keeps track of consecutive growth periods
    for i in range(1, len(data)):
        # Calculate relative growth between consecutive items
        relative_change = (data[i] - data[i - 1]) / data[i - 1]

        # Check if the growth exceeds the threshold
        if relative_change > threshold:
            count += 1  # Increment if there's a growth above the threshold
            # If sustained growth occurs for the required number of consecutive periods
            if count >= consecutive:
                return i - consecutive + 1  # Return the start of the sustained growth
        else:
            count = 0  # Reset count if growth is interrupted
    return -1  # Return -1 if no sustained growth is found


def create_table(results: List[SymbolAnalysisResult], last_updated: str, args: argparse.Namespace) -> Table:
    top_count = args.count
    table = Table(title=f"Binance Top {top_count} Potential Pumps\nUpdated: {last_updated}")
    table.add_column("Symbol", style="cyan", no_wrap=True)
    table.add_column("Volume Change", style="magenta", no_wrap=True)
    table.add_column("Price Change", style="magenta", no_wrap=True)
    table.add_column("Last Candle Volume (Coin)", style="magenta", no_wrap=True)
    table.add_column("Time Since Spike", style="magenta", no_wrap=True)
    table.add_column("Price Spike", style="magenta", no_wrap=True)

    for res in results:
        symbol = res.symbol
        volume_change = round(res.volume_change)
        price_change = res.price_change
        last_candle_volume_coin = res.last_candle_volume_coin
        min_passed = res.min_passed
        time_passed = minutes_to_human_readable(min_passed)
        is_price_spike = res.is_price_spike

        # Color coding
        volume_display = f"[green]{volume_change}%[/green]" if volume_change > 0 else f"[red]{volume_change}%[/red]"
        price_display = f"[green]{price_change:.2f}%[/green]" if price_change > 0 else f"[red]{price_change:.2f}%[/red]"
        last_candle_volume_coin_display = f"[bright_green]{last_candle_volume_coin:,.2f}[/bright_green]" if last_candle_volume_coin > 1000000 else f"{last_candle_volume_coin:,.2f}"
        time_passed_display = f"[bright_yellow]{time_passed}[/bright_yellow]" if min_passed < 60 else f"[red]{time_passed}[/red]"
        price_spike_display = "[bright_red]Yes[/bright_red]" if is_price_spike else "[bright_green]No[/bright_green]"

        table.add_row(
            symbol,
            volume_display,
            price_display,
            last_candle_volume_coin_display,
            time_passed_display,
            price_spike_display
        )
    return table


def minutes_to_human_readable(minutes):
    d, minutes = divmod(minutes, 1440)
    h, m = divmod(minutes, 60)
    return f"{d}d " * (d > 0) + f"{h}h " * (h > 0) + f"{m}m" * (m > 0) or "0m"


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

            if not args.watch:
                break

            await asyncio.sleep(args.wait)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Analyze volume changes of USDT coins on Binance Spot.')
    parser.add_argument('--interval', type=str, default="15m", help='Timeframe for volume analysis (e.g. 15m, 1h, 4h, 1d)')
    parser.add_argument('--range', type=str, default="6h", help='Time range for volume analysis (e.g. 4h, 1d, 3d)')
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
'''
'''
import asyncio
import platform
import sys
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
    'EOSUSDT', 'IOTAUSDT', 'ONTUSDT', 'ICXUSDT', 'NULSUSDT', 'VETUSDT', 'LINKUSDT', 'ONGUSDT', 'ZILUSDT', 'FETUSDT',
    'ZECUSDT', 'IOSTUSDT', 'CELRUSDT', 'THETAUSDT', 'ATOMUSDT', 'TFUELUSDT', 'ONEUSDT', 'ALGOUSDT', 'DUSKUSDT',
    'COSUSDT', 'MTLUSDT', 'WANUSDT', 'CVCUSDT', 'BANDUSDT', 'XTZUSDT', 'RVNUSDT', 'HBARUSDT', 'NKNUSDT', 'STXUSDT',
    'KAVAUSDT', 'ARPAUSDT', 'IOTXUSDT', 'RLCUSDT', 'CTXCUSDT', 'VITEUSDT', 'OGNUSDT', 'LSKUSDT', 'BNTUSDT', 'LTOUSDT',
    'COTIUSDT', 'STPTUSDT', 'DATAUSDT', 'CTSIUSDT', 'HIVEUSDT', 'CHRUSDT', 'ARDRUSDT', 'MDTUSDT', 'STMXUSDT', 'KNCUSDT',
    'SCUSDT', 'ZENUSDT', 'VTHOUSDT', 'DGBUSDT', 'SXPUSDT', 'DCRUSDT', 'STORJUSDT', 'BLZUSDT', 'KMDUSDT', 'NMRUSDT',
    'RSRUSDT', 'TRBUSDT', 'EGLDUSDT', 'DIAUSDT', 'FIOUSDT', 'UMAUSDT', 'OXTUSDT', 'UTKUSDT', 'NEARUSDT', 'FILUSDT',
    'CTKUSDT', 'AXSUSDT', 'STRAXUSDT', 'ROSEUSDT', 'AVAUSDT', 'SKLUSDT', 'GRTUSDT', 'CELOUSDT', 'RIFUSDT', 'CKBUSDT',
    'FIROUSDT', 'LITUSDT', 'SFPUSDT', 'FISUSDT', 'OMUSDT', 'PONDUSDT', 'ALICEUSDT', 'SUPERUSDT', 'CFXUSDT', 'PUNDIXUSDT',
    'TLMUSDT', 'FORTHUSDT', 'BURGERUSDT', 'ICPUSDT', 'ARUSDT', 'LPTUSDT', 'XVGUSDT', 'ATAUSDT', 'GTCUSDT', 'ERNUSDT',
    'PHAUSDT', 'MLNUSDT', 'C98USDT', 'CLVUSDT', 'QNTUSDT', 'FLOWUSDT', 'MINAUSDT', 'FARMUSDT', 'REQUSDT', 'GHSTUSDT',
    'WAXPUSDT', 'GNOUSDT', 'XECUSDT', 'ELFUSDT', 'VIDTUSDT', 'GALAUSDT', 'SYSUSDT', 'DFUSDT', 'FIDAUSDT', 'AGLDUSDT',
    'RADUSDT', 'BETAUSDT', 'RAREUSDT', 'LAZIOUSDT', 'ADXUSDT', 'AUCTIONUSDT', 'DARUSDT', 'MOVRUSDT', 'ENSUSDT', 'JASMYUSDT',
    'AMPUSDT', 'PYRUSDT', 'BICOUSDT', 'FLUXUSDT', 'VOXELUSDT', 'ACHUSDT', 'IMXUSDT', 'GLMRUSDT', 'SCRTUSDT', 'API3USDT',
    'XNOUSDT', 'ALPINEUSDT', 'TUSDT', 'ASTRUSDT', 'GMTUSDT', 'KDAUSDT', 'STEEMUSDT', 'REIUSDT', 'OPUSDT', 'STGUSDT',
    'POLYXUSDT', 'APTUSDT', 'PHBUSDT', 'HOOKUSDT', 'MAGICUSDT', 'PROSUSDT', 'SSVUSDT', 'AMBUSDT', 'GASUSDT', 'GLMUSDT',
    'QKCUSDT', 'IDUSDT', 'EDUUSDT', 'SUIUSDT', 'AERGOUSDT', 'ASTUSDT', 'SNTUSDT', 'COMBOUSDT', 'MAVUSDT', 'PENDLEUSDT',
    'ARKMUSDT', 'WLDUSDT', 'CYBERUSDT', 'ARKUSDT', 'IQUSDT', 'NTRNUSDT', 'TIAUSDT', 'BEAMXUSDT', 'PIVXUSDT', 'VICUSDT',
    'BLURUSDT', 'VANRYUSDT', 'JTOUSDT', 'ACEUSDT', 'NFPUSDT', 'AIUSDT', 'XAIUSDT', 'MANTAUSDT', 'ALTUSDT', 'PYTHUSDT',
    'RONINUSDT', 'DYMUSDT', 'PIXELUSDT', 'PORTALUSDT', 'PDAUSDT', 'AXLUSDT', 'METISUSDT', 'ENAUSDT', 'WUSDT', 'TNSRUSDT',
    'SAGAUSDT', 'TAOUSDT', 'REZUSDT', 'NOTUSDT', 'IOUSDT', 'ZKUSDT', 'ZROUSDT', 'RENDERUSDT', 'POLUSDT', 'EIGENUSDT',
    'SCRUSDT', 'LUMIAUSDT', 'KAIAUSDT', 'ACTUSDT', 'ACXUSDT',
]

# Type Definitions
KlineData = List[List[Any]]


@dataclass
class SymbolAnalysisResult:
    symbol: str
    volume_change: float
    price_change: float
    last_candle_volume_coin: float  # Volume in the coin
    last_candle_open_time: str  # Open time of the last candle
    last_candle_close_time: str  # Close time of the last candle
    oldest_candle_volume_coin: float  # Volume in the coin (oldest candle)
    oldest_candle_close_price: float  # Close price of the oldest candle
    last_candle_close_price: float  # Close price of the last candle
    min_passed: int = 0
    is_price_spike: bool = False


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
    match = re.match(r'^(\d+)([mhd])$', timeframe)
    if not match:
        raise ValueError(f"Invalid timeframe format: {timeframe}")
    value, unit = match.groups()
    multipliers = {'m': 1, 'h': 60, 'd': 1440}  # m -> 1, h -> 60, d -> 1440 (24 * 60)
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

        # Calculate volume change
        volumes = [float(candle[5]) for candle in current_data]  # Volume is the 6th element (index 5)
        if len(volumes) < 4:
            console.print(f"[yellow]Skipping {symbol}: Not enough volume data[/yellow]")
            return None

        # Take last 2 volumes for comparison
        volumes_last = volumes[-2:]

        # Calculate median of all volumes except the last 2
        volumes_for_median = volumes[:-2]
        volume_median = median(volumes_for_median)

        # Skip if median volume is zero to avoid division by zero
        if volume_median == 0:
            console.print(f"[yellow]Skipping {symbol}: Median volume is zero[/yellow]")
            return None

        volume_last_avg = mean(volumes_last)  # Calculate the average of the last 2 volumes
        volume_change = ((volume_last_avg - volume_median) / volume_median) * 100

        # Calculate price change
        prices = [float(candle[4]) for candle in current_data]  # Close prices (index 4)
        price_change = ((prices[-1] - prices[0]) / prices[0]) * 100

        # Get last candle details
        last_candle = current_data[-1]
        last_candle_volume_coin = float(last_candle[5])  # Volume in the coin
        last_candle_close_price = float(last_candle[4])  # Closing price of the last candle
        last_candle_open_time = datetime.fromtimestamp(last_candle[0] / 1000).strftime('%Y-%m-%d %H:%M:%S')
        last_candle_close_time = datetime.fromtimestamp(last_candle[6] / 1000).strftime('%Y-%m-%d %H:%M:%S')

        # Get oldest candle details
        oldest_candle = current_data[0]
        oldest_candle_volume_coin = float(oldest_candle[5])  # Volume in the coin (oldest candle)
        oldest_candle_close_price = float(oldest_candle[4])  # Close price of the oldest candle

        # Check for volume spike
        is_valid_spike = volume_last_avg > volume_median and volume_change >= args.threshold

        if not is_valid_spike:
            console.print(f"[yellow]Skipping {symbol}: No valid volume spike (Change: {volume_change:.2f}%)[/yellow]")
            return None

        # Check for sustained growth and price spike
        min_passed = 0
        is_price_spike = False
        sustained_growth_index = find_sustained_growth(volumes, threshold=args.threshold / 100, consecutive=3)
        if sustained_growth_index != -1:
            # Count items from this index to the end
            count_items_after = len(volumes) - sustained_growth_index
            min_passed = count_items_after * convert_interval_to_minutes(args.interval)
            # Average diff between max and min of prices
            avg_minmax_before_list = [abs(float(candle[2]) - float(candle[3])) for candle in current_data[:sustained_growth_index]]
            avg_minmax_after_list = [abs(float(candle[2]) - float(candle[3])) for candle in current_data[sustained_growth_index:]]
            avg_minmax_before, avg_minmax_after = mean(avg_minmax_before_list), mean(avg_minmax_after_list)
            price_change_threshold_ratio = 0.25
            is_price_spike = avg_minmax_after > avg_minmax_before * price_change_threshold_ratio

        return SymbolAnalysisResult(
            symbol=symbol,
            volume_change=volume_change,
            price_change=price_change,
            last_candle_volume_coin=last_candle_volume_coin,  # Volume in the coin
            last_candle_open_time=last_candle_open_time,  # Open time of the last candle
            last_candle_close_time=last_candle_close_time,  # Close time of the last candle
            oldest_candle_volume_coin=oldest_candle_volume_coin,  # Volume in the coin (oldest candle)
            oldest_candle_close_price=oldest_candle_close_price,  # Close price of the oldest candle
            last_candle_close_price=last_candle_close_price,  # Close price of the last candle
            min_passed=min_passed,
            is_price_spike=is_price_spike
        )
    except Exception as e:
        console.print(f"[red]Error analyzing symbol {symbol}: {e}[/red]")
        return None


def find_sustained_growth(data, threshold=0.5, consecutive=2):
    count = 0  # Keeps track of consecutive growth periods
    for i in range(1, len(data)):
        # Calculate relative growth between consecutive items
        relative_change = (data[i] - data[i - 1]) / data[i - 1]

        # Check if the growth exceeds the threshold
        if relative_change > threshold:
            count += 1  # Increment if there's a growth above the threshold
            # If sustained growth occurs for the required number of consecutive periods
            if count >= consecutive:
                return i - consecutive + 1  # Return the start of the sustained growth
        else:
            count = 0  # Reset count if growth is interrupted
    return -1  # Return -1 if no sustained growth is found


def create_table(results: List[SymbolAnalysisResult], last_updated: str, args: argparse.Namespace) -> Table:
    top_count = args.count
    table = Table(title=f"Binance Top {top_count} Boosters and Losers\nUpdated: {last_updated}")
    table.add_column(f"Symbol", style="cyan", no_wrap=True)
    table.add_column(f"Volume Change", style="magenta", no_wrap=True)
    table.add_column(f"Price Change", style="magenta", no_wrap=True)
    table.add_column(f"Last Candle Volume (Coin)", style="magenta", no_wrap=True)
    table.add_column(f"Oldest Candle Volume (Coin)", style="magenta", no_wrap=True)
    table.add_column(f"Oldest Candle Close Price", style="magenta", no_wrap=True)
    table.add_column(f"Last Candle Close Price", style="magenta", no_wrap=True)
    table.add_column(f"Last Candle Open Time", style="magenta", no_wrap=True)
    table.add_column(f"Last Candle Close Time", style="magenta", no_wrap=True)
    table.add_column(f"Time since", style="magenta", no_wrap=True)

    for res in results:
        symbol = res.symbol
        volume_change = round(res.volume_change)
        price_change = res.price_change  # Keep the original value without rounding
        last_candle_volume_coin = res.last_candle_volume_coin
        oldest_candle_volume_coin = res.oldest_candle_volume_coin
        oldest_candle_close_price = res.oldest_candle_close_price
        last_candle_close_price = res.last_candle_close_price
        last_candle_open_time = res.last_candle_open_time
        last_candle_close_time = res.last_candle_close_time
        min_passed = res.min_passed
        time_passed = minutes_to_human_readable(min_passed)
        is_price_spike = res.is_price_spike

        symbol_display = f"[bright_cyan]{symbol}[/bright_cyan]" if is_price_spike else f"{symbol}"
        volume_display = f"[green]{volume_change}[/green]%" if volume_change > 0 else f"[red]{volume_change}[/red]%"
        price_display = f"[green]{price_change:.2f}[/green]%" if price_change > 0 else f"[red]{price_change:.2f}[/red]%"  # 2 decimal places
        last_candle_volume_coin_display = f"{last_candle_volume_coin:,.2f}"  # Format with commas for readability
        oldest_candle_volume_coin_display = f"{oldest_candle_volume_coin:,.2f}"  # Format with commas for readability
        oldest_candle_close_price_display = f"{oldest_candle_close_price:,.6f}"  # 6 decimal places
        last_candle_close_price_display = f"{last_candle_close_price:,.6f}"  # 6 decimal places
        time_passed_display = "-" if min_passed <= 0 else f"[green]{time_passed}[green]" if min_passed < 60 else f"[red]{time_passed}[/red]"
        table.add_row(
            symbol_display,
            volume_display,
            price_display,
            last_candle_volume_coin_display,
            oldest_candle_volume_coin_display,
            oldest_candle_close_price_display,
            last_candle_close_price_display,
            last_candle_open_time,
            last_candle_close_time,
            time_passed_display
        )
    return table


def minutes_to_human_readable(minutes):
    d, minutes = divmod(minutes, 1440)
    h, m = divmod(minutes, 60)
    return f"{d}d " * (d > 0) + f"{h}h " * (h > 0) + f"{m}m" * (m > 0) or "0m"


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

            if not args.watch:
                break

            await asyncio.sleep(args.wait)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Analyze volume changes of USDT coins on Binance Spot.')
    parser.add_argument('--interval', type=str, default="15m", help='Timeframe for volume analysis (e.g. 15m, 1h, 4h, 1d)')
    parser.add_argument('--range', type=str, default="6h", help='Time range for volume analysis (e.g. 4h, 1d, 3d)')
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
'''
'''
import asyncio
import platform
import sys
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
    'EOSUSDT', 'IOTAUSDT', 'ONTUSDT', 'ICXUSDT', 'NULSUSDT', 'VETUSDT', 'LINKUSDT', 'ONGUSDT', 'ZILUSDT', 'FETUSDT',
    'ZECUSDT', 'IOSTUSDT', 'CELRUSDT', 'THETAUSDT', 'ATOMUSDT', 'TFUELUSDT', 'ONEUSDT', 'ALGOUSDT', 'DUSKUSDT',
    'COSUSDT', 'MTLUSDT', 'WANUSDT', 'CVCUSDT', 'BANDUSDT', 'XTZUSDT', 'RVNUSDT', 'HBARUSDT', 'NKNUSDT', 'STXUSDT',
    'KAVAUSDT', 'ARPAUSDT', 'IOTXUSDT', 'RLCUSDT', 'CTXCUSDT', 'VITEUSDT', 'OGNUSDT', 'LSKUSDT', 'BNTUSDT', 'LTOUSDT',
    'COTIUSDT', 'STPTUSDT', 'DATAUSDT', 'CTSIUSDT', 'HIVEUSDT', 'CHRUSDT', 'ARDRUSDT', 'MDTUSDT', 'STMXUSDT', 'KNCUSDT',
    'SCUSDT', 'ZENUSDT', 'VTHOUSDT', 'DGBUSDT', 'SXPUSDT', 'DCRUSDT', 'STORJUSDT', 'BLZUSDT', 'KMDUSDT', 'NMRUSDT',
    'RSRUSDT', 'TRBUSDT', 'EGLDUSDT', 'DIAUSDT', 'FIOUSDT', 'UMAUSDT', 'OXTUSDT', 'UTKUSDT', 'NEARUSDT', 'FILUSDT',
    'CTKUSDT', 'AXSUSDT', 'STRAXUSDT', 'ROSEUSDT', 'AVAUSDT', 'SKLUSDT', 'GRTUSDT', 'CELOUSDT', 'RIFUSDT', 'CKBUSDT',
    'FIROUSDT', 'LITUSDT', 'SFPUSDT', 'FISUSDT', 'OMUSDT', 'PONDUSDT', 'ALICEUSDT', 'SUPERUSDT', 'CFXUSDT', 'PUNDIXUSDT',
    'TLMUSDT', 'FORTHUSDT', 'BURGERUSDT', 'ICPUSDT', 'ARUSDT', 'LPTUSDT', 'XVGUSDT', 'ATAUSDT', 'GTCUSDT', 'ERNUSDT',
    'PHAUSDT', 'MLNUSDT', 'C98USDT', 'CLVUSDT', 'QNTUSDT', 'FLOWUSDT', 'MINAUSDT', 'FARMUSDT', 'REQUSDT', 'GHSTUSDT',
    'WAXPUSDT', 'GNOUSDT', 'XECUSDT', 'ELFUSDT', 'VIDTUSDT', 'GALAUSDT', 'SYSUSDT', 'DFUSDT', 'FIDAUSDT', 'AGLDUSDT',
    'RADUSDT', 'BETAUSDT', 'RAREUSDT', 'LAZIOUSDT', 'ADXUSDT', 'AUCTIONUSDT', 'DARUSDT', 'MOVRUSDT', 'ENSUSDT', 'JASMYUSDT',
    'AMPUSDT', 'PYRUSDT', 'BICOUSDT', 'FLUXUSDT', 'VOXELUSDT', 'ACHUSDT', 'IMXUSDT', 'GLMRUSDT', 'SCRTUSDT', 'API3USDT',
    'XNOUSDT', 'ALPINEUSDT', 'TUSDT', 'ASTRUSDT', 'GMTUSDT', 'KDAUSDT', 'STEEMUSDT', 'REIUSDT', 'OPUSDT', 'STGUSDT',
    'POLYXUSDT', 'APTUSDT', 'PHBUSDT', 'HOOKUSDT', 'MAGICUSDT', 'PROSUSDT', 'SSVUSDT', 'AMBUSDT', 'GASUSDT', 'GLMUSDT',
    'QKCUSDT', 'IDUSDT', 'EDUUSDT', 'SUIUSDT', 'AERGOUSDT', 'ASTUSDT', 'SNTUSDT', 'COMBOUSDT', 'MAVUSDT', 'PENDLEUSDT',
    'ARKMUSDT', 'WLDUSDT', 'CYBERUSDT', 'ARKUSDT', 'IQUSDT', 'NTRNUSDT', 'TIAUSDT', 'BEAMXUSDT', 'PIVXUSDT', 'VICUSDT',
    'BLURUSDT', 'VANRYUSDT', 'JTOUSDT', 'ACEUSDT', 'NFPUSDT', 'AIUSDT', 'XAIUSDT', 'MANTAUSDT', 'ALTUSDT', 'PYTHUSDT',
    'RONINUSDT', 'DYMUSDT', 'PIXELUSDT', 'PORTALUSDT', 'PDAUSDT', 'AXLUSDT', 'METISUSDT', 'ENAUSDT', 'WUSDT', 'TNSRUSDT',
    'SAGAUSDT', 'TAOUSDT', 'REZUSDT', 'NOTUSDT', 'IOUSDT', 'ZKUSDT', 'ZROUSDT', 'RENDERUSDT', 'POLUSDT', 'EIGENUSDT',
    'SCRUSDT', 'LUMIAUSDT', 'KAIAUSDT', 'ACTUSDT', 'ACXUSDT',
]

# Type Definitions
KlineData = List[List[Any]]


@dataclass
class SymbolAnalysisResult:
    symbol: str
    volume_change: float
    price_change: float
    last_candle_volume_coin: float  # Volume in the coin
    last_candle_open_time: str  # Open time of the last candle
    last_candle_close_time: str  # Close time of the last candle
    oldest_candle_volume_coin: float  # Volume in the coin (oldest candle)
    oldest_candle_close_price: float  # Close price of the oldest candle
    last_candle_close_price: float  # Close price of the last candle
    min_passed: int = 0
    is_price_spike: bool = False


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
    match = re.match(r'^(\d+)([mhd])$', timeframe)
    if not match:
        raise ValueError(f"Invalid timeframe format: {timeframe}")
    value, unit = match.groups()
    multipliers = {'m': 1, 'h': 60, 'd': 1440}  # m -> 1, h -> 60, d -> 1440 (24 * 60)
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

        # Calculate volume change
        volumes = [float(candle[5]) for candle in current_data]  # Volume is the 6th element (index 5)
        if len(volumes) < 4:
            console.print(f"[yellow]Skipping {symbol}: Not enough volume data[/yellow]")
            return None

        # Take last 3 volumes for comparison
        volumes_last = volumes[-3:]
        volume_median = median(volumes)

        # Skip if median volume is zero to avoid division by zero
        if volume_median == 0:
            console.print(f"[yellow]Skipping {symbol}: Median volume is zero[/yellow]")
            return None

        volume_last_avg = mean(volumes_last)  # Calculate the average of the last 3 volumes
        volume_change = ((volume_last_avg - volume_median) / volume_median) * 100

        # Calculate price change
        prices = [float(candle[4]) for candle in current_data]  # Close prices (index 4)
        price_change = ((prices[-1] - prices[0]) / prices[0]) * 100

        # Get last candle details
        last_candle = current_data[-1]
        last_candle_volume_coin = float(last_candle[5])  # Volume in the coin
        last_candle_close_price = float(last_candle[4])  # Closing price of the last candle
        last_candle_open_time = datetime.fromtimestamp(last_candle[0] / 1000).strftime('%Y-%m-%d %H:%M:%S')
        last_candle_close_time = datetime.fromtimestamp(last_candle[6] / 1000).strftime('%Y-%m-%d %H:%M:%S')

        # Get oldest candle details
        oldest_candle = current_data[0]
        oldest_candle_volume_coin = float(oldest_candle[5])  # Volume in the coin (oldest candle)
        oldest_candle_close_price = float(oldest_candle[4])  # Close price of the oldest candle

        # Check for volume spike
        is_valid_spike = volume_last_avg > volume_median and volume_change >= args.threshold

        if not is_valid_spike:
            console.print(f"[yellow]Skipping {symbol}: No valid volume spike (Change: {volume_change:.2f}%)[/yellow]")
            return None

        # Check for sustained growth and price spike
        min_passed = 0
        is_price_spike = False
        sustained_growth_index = find_sustained_growth(volumes, threshold=args.threshold / 100, consecutive=3)
        if sustained_growth_index != -1:
            # Count items from this index to the end
            count_items_after = len(volumes) - sustained_growth_index
            min_passed = count_items_after * convert_interval_to_minutes(args.interval)
            # Average diff between max and min of prices
            avg_minmax_before_list = [abs(float(candle[2]) - float(candle[3])) for candle in current_data[:sustained_growth_index]]
            avg_minmax_after_list = [abs(float(candle[2]) - float(candle[3])) for candle in current_data[sustained_growth_index:]]
            avg_minmax_before, avg_minmax_after = mean(avg_minmax_before_list), mean(avg_minmax_after_list)
            price_change_threshold_ratio = 0.25
            is_price_spike = avg_minmax_after > avg_minmax_before * price_change_threshold_ratio

        return SymbolAnalysisResult(
            symbol=symbol,
            volume_change=volume_change,
            price_change=price_change,
            last_candle_volume_coin=last_candle_volume_coin,  # Volume in the coin
            last_candle_open_time=last_candle_open_time,  # Open time of the last candle
            last_candle_close_time=last_candle_close_time,  # Close time of the last candle
            oldest_candle_volume_coin=oldest_candle_volume_coin,  # Volume in the coin (oldest candle)
            oldest_candle_close_price=oldest_candle_close_price,  # Close price of the oldest candle
            last_candle_close_price=last_candle_close_price,  # Close price of the last candle
            min_passed=min_passed,
            is_price_spike=is_price_spike
        )
    except Exception as e:
        console.print(f"[red]Error analyzing symbol {symbol}: {e}[/red]")
        return None


def find_sustained_growth(data, threshold=0.5, consecutive=2):
    count = 0  # Keeps track of consecutive growth periods
    for i in range(1, len(data)):
        # Calculate relative growth between consecutive items
        relative_change = (data[i] - data[i - 1]) / data[i - 1]

        # Check if the growth exceeds the threshold
        if relative_change > threshold:
            count += 1  # Increment if there's a growth above the threshold
            # If sustained growth occurs for the required number of consecutive periods
            if count >= consecutive:
                return i - consecutive + 1  # Return the start of the sustained growth
        else:
            count = 0  # Reset count if growth is interrupted
    return -1  # Return -1 if no sustained growth is found


def create_table(results: List[SymbolAnalysisResult], last_updated: str, args: argparse.Namespace) -> Table:
    top_count = args.count
    table = Table(title=f"Binance Top {top_count} Boosters and Losers\nUpdated: {last_updated}")
    table.add_column(f"Symbol", style="cyan", no_wrap=True)
    table.add_column(f"Volume Change", style="magenta", no_wrap=True)
    table.add_column(f"Price Change", style="magenta", no_wrap=True)
    table.add_column(f"Last Candle Volume (Coin)", style="magenta", no_wrap=True)
    table.add_column(f"Oldest Candle Volume (Coin)", style="magenta", no_wrap=True)
    table.add_column(f"Oldest Candle Close Price", style="magenta", no_wrap=True)
    table.add_column(f"Last Candle Close Price", style="magenta", no_wrap=True)
    table.add_column(f"Last Candle Open Time", style="magenta", no_wrap=True)
    table.add_column(f"Last Candle Close Time", style="magenta", no_wrap=True)
    table.add_column(f"Time since", style="magenta", no_wrap=True)

    for res in results:
        symbol = res.symbol
        volume_change = round(res.volume_change)
        price_change = res.price_change  # Keep the original value without rounding
        last_candle_volume_coin = res.last_candle_volume_coin
        oldest_candle_volume_coin = res.oldest_candle_volume_coin
        oldest_candle_close_price = res.oldest_candle_close_price
        last_candle_close_price = res.last_candle_close_price
        last_candle_open_time = res.last_candle_open_time
        last_candle_close_time = res.last_candle_close_time
        min_passed = res.min_passed
        time_passed = minutes_to_human_readable(min_passed)
        is_price_spike = res.is_price_spike

        symbol_display = f"[bright_cyan]{symbol}[/bright_cyan]" if is_price_spike else f"{symbol}"
        volume_display = f"[green]{volume_change}[/green]%" if volume_change > 0 else f"[red]{volume_change}[/red]%"
        price_display = f"[green]{price_change:.2f}[/green]%" if price_change > 0 else f"[red]{price_change:.2f}[/red]%"  # 2 decimal places
        last_candle_volume_coin_display = f"{last_candle_volume_coin:,.2f}"  # Format with commas for readability
        oldest_candle_volume_coin_display = f"{oldest_candle_volume_coin:,.2f}"  # Format with commas for readability
        oldest_candle_close_price_display = f"{oldest_candle_close_price:,.6f}"  # 6 decimal places
        last_candle_close_price_display = f"{last_candle_close_price:,.6f}"  # 6 decimal places
        time_passed_display = "-" if min_passed <= 0 else f"[green]{time_passed}[green]" if min_passed < 60 else f"[red]{time_passed}[/red]"
        table.add_row(
            symbol_display,
            volume_display,
            price_display,
            last_candle_volume_coin_display,
            oldest_candle_volume_coin_display,
            oldest_candle_close_price_display,
            last_candle_close_price_display,
            last_candle_open_time,
            last_candle_close_time,
            time_passed_display
        )
    return table


def minutes_to_human_readable(minutes):
    d, minutes = divmod(minutes, 1440)
    h, m = divmod(minutes, 60)
    return f"{d}d " * (d > 0) + f"{h}h " * (h > 0) + f"{m}m" * (m > 0) or "0m"


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

            if not args.watch:
                break

            await asyncio.sleep(args.wait)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Analyze volume changes of USDT coins on Binance Spot.')
    parser.add_argument('--interval', type=str, default="15m", help='Timeframe for volume analysis (e.g. 15m, 1h, 4h, 1d)')
    parser.add_argument('--range', type=str, default="6h", help='Time range for volume analysis (e.g. 4h, 1d, 3d)')
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
'''
'''
import asyncio
import platform
import sys
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
    'EOSUSDT', 'IOTAUSDT', 'ONTUSDT', 'ICXUSDT', 'NULSUSDT', 'VETUSDT', 'LINKUSDT', 'ONGUSDT', 'ZILUSDT', 'FETUSDT',
    'ZECUSDT', 'IOSTUSDT', 'CELRUSDT', 'THETAUSDT', 'ATOMUSDT', 'TFUELUSDT', 'ONEUSDT', 'ALGOUSDT', 'DUSKUSDT',
    'COSUSDT', 'MTLUSDT', 'WANUSDT', 'CVCUSDT', 'BANDUSDT', 'XTZUSDT', 'RVNUSDT', 'HBARUSDT', 'NKNUSDT', 'STXUSDT',
    'KAVAUSDT', 'ARPAUSDT', 'IOTXUSDT', 'RLCUSDT', 'CTXCUSDT', 'VITEUSDT', 'OGNUSDT', 'LSKUSDT', 'BNTUSDT', 'LTOUSDT',
    'COTIUSDT', 'STPTUSDT', 'DATAUSDT', 'CTSIUSDT', 'HIVEUSDT', 'CHRUSDT', 'ARDRUSDT', 'MDTUSDT', 'STMXUSDT', 'KNCUSDT',
    'SCUSDT', 'ZENUSDT', 'VTHOUSDT', 'DGBUSDT', 'SXPUSDT', 'DCRUSDT', 'STORJUSDT', 'BLZUSDT', 'KMDUSDT', 'NMRUSDT',
    'RSRUSDT', 'TRBUSDT', 'EGLDUSDT', 'DIAUSDT', 'FIOUSDT', 'UMAUSDT', 'OXTUSDT', 'UTKUSDT', 'NEARUSDT', 'FILUSDT',
    'CTKUSDT', 'AXSUSDT', 'STRAXUSDT', 'ROSEUSDT', 'AVAUSDT', 'SKLUSDT', 'GRTUSDT', 'CELOUSDT', 'RIFUSDT', 'CKBUSDT',
    'FIROUSDT', 'LITUSDT', 'SFPUSDT', 'FISUSDT', 'OMUSDT', 'PONDUSDT', 'ALICEUSDT', 'SUPERUSDT', 'CFXUSDT', 'PUNDIXUSDT',
    'TLMUSDT', 'FORTHUSDT', 'BURGERUSDT', 'ICPUSDT', 'ARUSDT', 'LPTUSDT', 'XVGUSDT', 'ATAUSDT', 'GTCUSDT', 'ERNUSDT',
    'PHAUSDT', 'MLNUSDT', 'C98USDT', 'CLVUSDT', 'QNTUSDT', 'FLOWUSDT', 'MINAUSDT', 'REQUSDT', 'GHSTUSDT',
    'WAXPUSDT', 'GNOUSDT', 'XECUSDT', 'ELFUSDT', 'VIDTUSDT', 'GALAUSDT', 'SYSUSDT', 'DFUSDT', 'FIDAUSDT', 'AGLDUSDT',
    'RADUSDT', 'BETAUSDT', 'RAREUSDT', 'LAZIOUSDT', 'ADXUSDT', 'AUCTIONUSDT', 'DARUSDT', 'MOVRUSDT', 'ENSUSDT', 'JASMYUSDT',
    'AMPUSDT', 'PYRUSDT', 'BICOUSDT', 'FLUXUSDT', 'VOXELUSDT', 'ACHUSDT', 'IMXUSDT', 'GLMRUSDT', 'SCRTUSDT', 'API3USDT',
    'XNOUSDT', 'ALPINEUSDT', 'TUSDT', 'ASTRUSDT', 'GMTUSDT', 'KDAUSDT', 'STEEMUSDT', 'REIUSDT', 'OPUSDT', 'STGUSDT',
    'POLYXUSDT', 'APTUSDT', 'PHBUSDT', 'HOOKUSDT', 'MAGICUSDT', 'PROSUSDT', 'SSVUSDT', 'AMBUSDT', 'GASUSDT', 'GLMUSDT',
    'QKCUSDT', 'IDUSDT', 'EDUUSDT', 'SUIUSDT', 'AERGOUSDT', 'ASTUSDT', 'SNTUSDT', 'COMBOUSDT', 'MAVUSDT', 'PENDLEUSDT',
    'ARKMUSDT', 'WLDUSDT', 'CYBERUSDT', 'ARKUSDT', 'IQUSDT', 'NTRNUSDT', 'TIAUSDT', 'BEAMXUSDT', 'PIVXUSDT', 'VICUSDT',
    'BLURUSDT', 'VANRYUSDT', 'JTOUSDT', 'ACEUSDT', 'NFPUSDT', 'AIUSDT', 'XAIUSDT', 'MANTAUSDT', 'ALTUSDT', 'PYTHUSDT',
    'RONINUSDT', 'DYMUSDT', 'PIXELUSDT', 'PORTALUSDT', 'PDAUSDT', 'AXLUSDT', 'METISUSDT', 'ENAUSDT', 'WUSDT', 'TNSRUSDT',
    'SAGAUSDT', 'TAOUSDT', 'REZUSDT', 'NOTUSDT', 'IOUSDT', 'ZKUSDT', 'ZROUSDT', 'RENDERUSDT', 'POLUSDT', 'EIGENUSDT',
    'SCRUSDT', 'LUMIAUSDT', 'KAIAUSDT', 'ACTUSDT', 'ACXUSDT',
]

# Type Definitions
KlineData = List[List[Any]]


@dataclass
class SymbolAnalysisResult:
    symbol: str
    volume_change: float
    price_change: float
    last_candle_volume_coin: float  # Volume in the coin
    last_candle_open_time: str  # Open time of the last candle
    last_candle_close_time: str  # Close time of the last candle
    oldest_candle_volume_coin: float  # Volume in the coin (oldest candle)
    oldest_candle_close_price: float  # Close price of the oldest candle
    last_candle_close_price: float  # Close price of the last candle
    min_passed: int = 0
    is_price_spike: bool = False


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
    match = re.match(r'^(\d+)([mhd])$', timeframe)
    if not match:
        raise ValueError(f"Invalid timeframe format: {timeframe}")
    value, unit = match.groups()
    multipliers = {'m': 1, 'h': 60, 'd': 1440}  # m -> 1, h -> 60, d -> 1440 (24 * 60)
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

        # Calculate volume change
        volumes = [float(candle[5]) for candle in current_data]  # Volume is the 6th element (index 5)
        if len(volumes) < 4:
            console.print(f"[yellow]Skipping {symbol}: Not enough volume data[/yellow]")
            return None

        # Take last 3 volumes for comparison
        volumes_last = volumes[-3:]
        volume_median = median(volumes)

        # Skip if median volume is zero to avoid division by zero
        if volume_median == 0:
            console.print(f"[yellow]Skipping {symbol}: Median volume is zero[/yellow]")
            return None

        volume_last_avg = mean(volumes_last)  # Calculate the average of the last 3 volumes
        volume_change = ((volume_last_avg - volume_median) / volume_median) * 100

        # Calculate price change
        prices = [float(candle[4]) for candle in current_data]  # Close prices (index 4)
        price_change = ((prices[-1] - prices[0]) / prices[0]) * 100

        # Get last candle details
        last_candle = current_data[-1]
        last_candle_volume_coin = float(last_candle[5])  # Volume in the coin
        last_candle_close_price = float(last_candle[4])  # Closing price of the last candle
        last_candle_open_time = datetime.fromtimestamp(last_candle[0] / 1000).strftime('%Y-%m-%d %H:%M:%S')
        last_candle_close_time = datetime.fromtimestamp(last_candle[6] / 1000).strftime('%Y-%m-%d %H:%M:%S')

        # Get oldest candle details
        oldest_candle = current_data[0]
        oldest_candle_volume_coin = float(oldest_candle[5])  # Volume in the coin (oldest candle)
        oldest_candle_close_price = float(oldest_candle[4])  # Close price of the oldest candle

        # Check for volume spike
        is_valid_spike = volume_last_avg > volume_median and volume_change >= args.threshold

        if not is_valid_spike:
            console.print(f"[yellow]Skipping {symbol}: No valid volume spike (Change: {volume_change:.2f}%)[/yellow]")
            return None

        # Check for sustained growth and price spike
        min_passed = 0
        is_price_spike = False
        sustained_growth_index = find_sustained_growth(volumes, threshold=args.threshold / 100, consecutive=3)
        if sustained_growth_index != -1:
            # Count items from this index to the end
            count_items_after = len(volumes) - sustained_growth_index
            min_passed = count_items_after * convert_interval_to_minutes(args.interval)
            # Average diff between max and min of prices
            avg_minmax_before_list = [abs(float(candle[2]) - float(candle[3])) for candle in current_data[:sustained_growth_index]]
            avg_minmax_after_list = [abs(float(candle[2]) - float(candle[3])) for candle in current_data[sustained_growth_index:]]
            avg_minmax_before, avg_minmax_after = mean(avg_minmax_before_list), mean(avg_minmax_after_list)
            price_change_threshold_ratio = 0.25
            is_price_spike = avg_minmax_after > avg_minmax_before * price_change_threshold_ratio

        return SymbolAnalysisResult(
            symbol=symbol,
            volume_change=volume_change,
            price_change=price_change,
            last_candle_volume_coin=last_candle_volume_coin,  # Volume in the coin
            last_candle_open_time=last_candle_open_time,  # Open time of the last candle
            last_candle_close_time=last_candle_close_time,  # Close time of the last candle
            oldest_candle_volume_coin=oldest_candle_volume_coin,  # Volume in the coin (oldest candle)
            oldest_candle_close_price=oldest_candle_close_price,  # Close price of the oldest candle
            last_candle_close_price=last_candle_close_price,  # Close price of the last candle
            min_passed=min_passed,
            is_price_spike=is_price_spike
        )
    except Exception as e:
        console.print(f"[red]Error analyzing symbol {symbol}: {e}[/red]")
        return None


def find_sustained_growth(data, threshold=0.5, consecutive=2):
    count = 0  # Keeps track of consecutive growth periods
    for i in range(1, len(data)):
        # Calculate relative growth between consecutive items
        relative_change = (data[i] - data[i - 1]) / data[i - 1]

        # Check if the growth exceeds the threshold
        if relative_change > threshold:
            count += 1  # Increment if there's a growth above the threshold
            # If sustained growth occurs for the required number of consecutive periods
            if count >= consecutive:
                return i - consecutive + 1  # Return the start of the sustained growth
        else:
            count = 0  # Reset count if growth is interrupted
    return -1  # Return -1 if no sustained growth is found


def create_table(results: List[SymbolAnalysisResult], last_updated: str, args: argparse.Namespace) -> Table:
    top_count = args.count
    table = Table(title=f"Binance Top {top_count} Boosters and Losers\nUpdated: {last_updated}")
    table.add_column(f"Symbol", style="cyan", no_wrap=True)
    table.add_column(f"Volume Change", style="magenta", no_wrap=True)
    table.add_column(f"Price Change", style="magenta", no_wrap=True)
    table.add_column(f"Last Candle Volume (Coin)", style="magenta", no_wrap=True)
    table.add_column(f"Oldest Candle Volume (Coin)", style="magenta", no_wrap=True)
    table.add_column(f"Oldest Candle Close Price", style="magenta", no_wrap=True)
    table.add_column(f"Last Candle Close Price", style="magenta", no_wrap=True)
    table.add_column(f"Last Candle Open Time", style="magenta", no_wrap=True)
    table.add_column(f"Last Candle Close Time", style="magenta", no_wrap=True)
    table.add_column(f"Time since", style="magenta", no_wrap=True)

    for res in results:
        symbol = res.symbol
        volume_change = round(res.volume_change)
        price_change = res.price_change  # Keep the original value without rounding
        last_candle_volume_coin = res.last_candle_volume_coin
        oldest_candle_volume_coin = res.oldest_candle_volume_coin
        oldest_candle_close_price = res.oldest_candle_close_price
        last_candle_close_price = res.last_candle_close_price
        last_candle_open_time = res.last_candle_open_time
        last_candle_close_time = res.last_candle_close_time
        min_passed = res.min_passed
        time_passed = minutes_to_human_readable(min_passed)
        is_price_spike = res.is_price_spike

        symbol_display = f"[bright_cyan]{symbol}[/bright_cyan]" if is_price_spike else f"{symbol}"
        volume_display = f"[green]{volume_change}[/green]%" if volume_change > 0 else f"[red]{volume_change}[/red]%"
        price_display = f"[green]{price_change:.2f}[/green]%" if price_change > 0 else f"[red]{price_change:.2f}[/red]%"  # 2 decimal places
        last_candle_volume_coin_display = f"{last_candle_volume_coin:,.2f}"  # Format with commas for readability
        oldest_candle_volume_coin_display = f"{oldest_candle_volume_coin:,.2f}"  # Format with commas for readability
        oldest_candle_close_price_display = f"{oldest_candle_close_price:,.6f}"  # 6 decimal places
        last_candle_close_price_display = f"{last_candle_close_price:,.6f}"  # 6 decimal places
        time_passed_display = "-" if min_passed <= 0 else f"[green]{time_passed}[green]" if min_passed < 60 else f"[red]{time_passed}[/red]"
        table.add_row(
            symbol_display,
            volume_display,
            price_display,
            last_candle_volume_coin_display,
            oldest_candle_volume_coin_display,
            oldest_candle_close_price_display,
            last_candle_close_price_display,
            last_candle_open_time,
            last_candle_close_time,
            time_passed_display
        )
    return table


def minutes_to_human_readable(minutes):
    d, minutes = divmod(minutes, 1440)
    h, m = divmod(minutes, 60)
    return f"{d}d " * (d > 0) + f"{h}h " * (h > 0) + f"{m}m" * (m > 0) or "0m"


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

            # Filter results: Keep only coins with Volume Change or Price Change above 0.5%
            filtered_results = [
                res for res in results
                if abs(res.volume_change) > 0.5 or abs(res.price_change) > 0.5
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

            if not args.watch:
                break

            await asyncio.sleep(args.wait)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Analyze volume changes of USDT coins on Binance Spot.')
    parser.add_argument('--interval', type=str, default="15m", help='Timeframe for volume analysis (e.g. 15m, 1h, 4h, 1d)')
    parser.add_argument('--range', type=str, default="6h", help='Time range for volume analysis (e.g. 4h, 1d, 3d)')
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
'''
'''
import asyncio
import platform
import sys
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
    'EOSUSDT', 'IOTAUSDT', 'ONTUSDT', 'ICXUSDT', 'NULSUSDT', 'VETUSDT', 'LINKUSDT', 'ONGUSDT', 'ZILUSDT', 'FETUSDT',
    'ZECUSDT', 'IOSTUSDT', 'CELRUSDT', 'THETAUSDT', 'ATOMUSDT', 'TFUELUSDT', 'ONEUSDT', 'ALGOUSDT', 'DUSKUSDT',
    'COSUSDT', 'MTLUSDT', 'WANUSDT', 'CVCUSDT', 'BANDUSDT', 'XTZUSDT', 'RVNUSDT', 'HBARUSDT', 'NKNUSDT', 'STXUSDT',
    'KAVAUSDT', 'ARPAUSDT', 'IOTXUSDT', 'RLCUSDT', 'CTXCUSDT', 'VITEUSDT', 'OGNUSDT', 'LSKUSDT', 'BNTUSDT', 'LTOUSDT',
    'COTIUSDT', 'STPTUSDT', 'DATAUSDT', 'CTSIUSDT', 'HIVEUSDT', 'CHRUSDT', 'ARDRUSDT', 'MDTUSDT', 'STMXUSDT', 'KNCUSDT',
    'SCUSDT', 'ZENUSDT', 'VTHOUSDT', 'DGBUSDT', 'SXPUSDT', 'DCRUSDT', 'STORJUSDT', 'BLZUSDT', 'KMDUSDT', 'NMRUSDT',
    'RSRUSDT', 'TRBUSDT', 'EGLDUSDT', 'DIAUSDT', 'FIOUSDT', 'UMAUSDT', 'OXTUSDT', 'UTKUSDT', 'NEARUSDT', 'FILUSDT',
    'CTKUSDT', 'AXSUSDT', 'STRAXUSDT', 'ROSEUSDT', 'AVAUSDT', 'SKLUSDT', 'GRTUSDT', 'CELOUSDT', 'RIFUSDT', 'CKBUSDT',
    'FIROUSDT', 'LITUSDT', 'SFPUSDT', 'FISUSDT', 'OMUSDT', 'PONDUSDT', 'ALICEUSDT', 'SUPERUSDT', 'CFXUSDT', 'PUNDIXUSDT',
    'TLMUSDT', 'FORTHUSDT', 'BURGERUSDT', 'ICPUSDT', 'ARUSDT', 'LPTUSDT', 'XVGUSDT', 'ATAUSDT', 'GTCUSDT', 'ERNUSDT',
    'PHAUSDT', 'MLNUSDT', 'C98USDT', 'CLVUSDT', 'QNTUSDT', 'FLOWUSDT', 'MINAUSDT', 'FARMUSDT', 'REQUSDT', 'GHSTUSDT',
    'WAXPUSDT', 'GNOUSDT', 'XECUSDT', 'ELFUSDT', 'VIDTUSDT', 'GALAUSDT', 'SYSUSDT', 'DFUSDT', 'FIDAUSDT', 'AGLDUSDT',
    'RADUSDT', 'BETAUSDT', 'RAREUSDT', 'LAZIOUSDT', 'ADXUSDT', 'AUCTIONUSDT', 'DARUSDT', 'MOVRUSDT', 'ENSUSDT', 'JASMYUSDT',
    'AMPUSDT', 'PYRUSDT', 'BICOUSDT', 'FLUXUSDT', 'VOXELUSDT', 'ACHUSDT', 'IMXUSDT', 'GLMRUSDT', 'SCRTUSDT', 'API3USDT',
    'XNOUSDT', 'ALPINEUSDT', 'TUSDT', 'ASTRUSDT', 'GMTUSDT', 'KDAUSDT', 'STEEMUSDT', 'REIUSDT', 'OPUSDT', 'STGUSDT',
    'POLYXUSDT', 'APTUSDT', 'PHBUSDT', 'HOOKUSDT', 'MAGICUSDT', 'PROSUSDT', 'SSVUSDT', 'AMBUSDT', 'GASUSDT', 'GLMUSDT',
    'QKCUSDT', 'IDUSDT', 'EDUUSDT', 'SUIUSDT', 'AERGOUSDT', 'ASTUSDT', 'SNTUSDT', 'COMBOUSDT', 'MAVUSDT', 'PENDLEUSDT',
    'ARKMUSDT', 'WLDUSDT', 'CYBERUSDT', 'ARKUSDT', 'IQUSDT', 'NTRNUSDT', 'TIAUSDT', 'BEAMXUSDT', 'PIVXUSDT', 'VICUSDT',
    'BLURUSDT', 'VANRYUSDT', 'JTOUSDT', 'ACEUSDT', 'NFPUSDT', 'AIUSDT', 'XAIUSDT', 'MANTAUSDT', 'ALTUSDT', 'PYTHUSDT',
    'RONINUSDT', 'DYMUSDT', 'PIXELUSDT', 'PORTALUSDT', 'PDAUSDT', 'AXLUSDT', 'METISUSDT', 'ENAUSDT', 'WUSDT', 'TNSRUSDT',
    'SAGAUSDT', 'TAOUSDT', 'REZUSDT', 'NOTUSDT', 'IOUSDT', 'ZKUSDT', 'ZROUSDT', 'RENDERUSDT', 'POLUSDT', 'EIGENUSDT',
    'SCRUSDT', 'LUMIAUSDT', 'KAIAUSDT', 'ACTUSDT', 'ACXUSDT',
]

# Type Definitions
KlineData = List[List[Any]]


@dataclass
class SymbolAnalysisResult:
    symbol: str
    volume_change: float
    price_change: float
    last_candle_volume_coin: float  # Volume in the coin
    last_candle_open_time: str  # Open time of the last candle
    last_candle_close_time: str  # Close time of the last candle
    oldest_candle_volume_coin: float  # Volume in the coin (oldest candle)
    oldest_candle_close_price: float  # Close price of the oldest candle
    last_candle_close_price: float  # Close price of the last candle
    min_passed: int = 0
    is_price_spike: bool = False


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
    match = re.match(r'^(\d+)([mhd])$', timeframe)
    if not match:
        raise ValueError(f"Invalid timeframe format: {timeframe}")
    value, unit = match.groups()
    multipliers = {'m': 1, 'h': 60, 'd': 1440}  # m -> 1, h -> 60, d -> 1440 (24 * 60)
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

        # Calculate volume change
        volumes = [float(candle[5]) for candle in current_data]  # Volume is the 6th element (index 5)
        if len(volumes) < 4:
            console.print(f"[yellow]Skipping {symbol}: Not enough volume data[/yellow]")
            return None

        # Take last 3 volumes for comparison
        volumes_last = volumes[-3:]
        volume_median = median(volumes)

        # Skip if median volume is zero to avoid division by zero
        if volume_median == 0:
            console.print(f"[yellow]Skipping {symbol}: Median volume is zero[/yellow]")
            return None

        volume_last_avg = mean(volumes_last)  # Calculate the average of the last 3 volumes
        volume_change = ((volume_last_avg - volume_median) / volume_median) * 100

        # Calculate price change
        prices = [float(candle[4]) for candle in current_data]  # Close prices (index 4)
        price_change = ((prices[-1] - prices[0]) / prices[0]) * 100

        # Get last candle details
        last_candle = current_data[-1]
        last_candle_volume_coin = float(last_candle[5])  # Volume in the coin
        last_candle_close_price = float(last_candle[4])  # Closing price of the last candle
        last_candle_open_time = datetime.fromtimestamp(last_candle[0] / 1000).strftime('%Y-%m-%d %H:%M:%S')
        last_candle_close_time = datetime.fromtimestamp(last_candle[6] / 1000).strftime('%Y-%m-%d %H:%M:%S')

        # Get oldest candle details
        oldest_candle = current_data[0]
        oldest_candle_volume_coin = float(oldest_candle[5])  # Volume in the coin (oldest candle)
        oldest_candle_close_price = float(oldest_candle[4])  # Close price of the oldest candle

        # Check for volume spike
        is_valid_spike = volume_last_avg > volume_median and volume_change >= args.threshold

        if not is_valid_spike:
            console.print(f"[yellow]Skipping {symbol}: No valid volume spike (Change: {volume_change:.2f}%)[/yellow]")
            return None

        # Check for sustained growth and price spike
        min_passed = 0
        is_price_spike = False
        sustained_growth_index = find_sustained_growth(volumes, threshold=args.threshold / 100, consecutive=3)
        if sustained_growth_index != -1:
            # Count items from this index to the end
            count_items_after = len(volumes) - sustained_growth_index
            min_passed = count_items_after * convert_interval_to_minutes(args.interval)
            # Average diff between max and min of prices
            avg_minmax_before_list = [abs(float(candle[2]) - float(candle[3])) for candle in current_data[:sustained_growth_index]]
            avg_minmax_after_list = [abs(float(candle[2]) - float(candle[3])) for candle in current_data[sustained_growth_index:]]
            avg_minmax_before, avg_minmax_after = mean(avg_minmax_before_list), mean(avg_minmax_after_list)
            price_change_threshold_ratio = 0.25
            is_price_spike = avg_minmax_after > avg_minmax_before * price_change_threshold_ratio

        return SymbolAnalysisResult(
            symbol=symbol,
            volume_change=volume_change,
            price_change=price_change,
            last_candle_volume_coin=last_candle_volume_coin,  # Volume in the coin
            last_candle_open_time=last_candle_open_time,  # Open time of the last candle
            last_candle_close_time=last_candle_close_time,  # Close time of the last candle
            oldest_candle_volume_coin=oldest_candle_volume_coin,  # Volume in the coin (oldest candle)
            oldest_candle_close_price=oldest_candle_close_price,  # Close price of the oldest candle
            last_candle_close_price=last_candle_close_price,  # Close price of the last candle
            min_passed=min_passed,
            is_price_spike=is_price_spike
        )
    except Exception as e:
        console.print(f"[red]Error analyzing symbol {symbol}: {e}[/red]")
        return None


def find_sustained_growth(data, threshold=0.5, consecutive=2):
    count = 0  # Keeps track of consecutive growth periods
    for i in range(1, len(data)):
        # Calculate relative growth between consecutive items
        relative_change = (data[i] - data[i - 1]) / data[i - 1]

        # Check if the growth exceeds the threshold
        if relative_change > threshold:
            count += 1  # Increment if there's a growth above the threshold
            # If sustained growth occurs for the required number of consecutive periods
            if count >= consecutive:
                return i - consecutive + 1  # Return the start of the sustained growth
        else:
            count = 0  # Reset count if growth is interrupted
    return -1  # Return -1 if no sustained growth is found


def create_table(results: List[SymbolAnalysisResult], last_updated: str, args: argparse.Namespace) -> Table:
    top_count = args.count
    table = Table(title=f"Binance Top {top_count} Boosters and Losers\nUpdated: {last_updated}")
    table.add_column(f"Symbol", style="cyan", no_wrap=True)
    table.add_column(f"Volume Change", style="magenta", no_wrap=True)
    table.add_column(f"Price Change", style="magenta", no_wrap=True)
    table.add_column(f"Last Candle Volume (Coin)", style="magenta", no_wrap=True)
    table.add_column(f"Oldest Candle Volume (Coin)", style="magenta", no_wrap=True)
    table.add_column(f"Oldest Candle Close Price", style="magenta", no_wrap=True)
    table.add_column(f"Last Candle Close Price", style="magenta", no_wrap=True)
    table.add_column(f"Last Candle Open Time", style="magenta", no_wrap=True)
    table.add_column(f"Last Candle Close Time", style="magenta", no_wrap=True)
    table.add_column(f"Time since", style="magenta", no_wrap=True)

    for res in results:
        symbol = res.symbol
        volume_change = round(res.volume_change)
        price_change = res.price_change  # Keep the original value without rounding
        last_candle_volume_coin = res.last_candle_volume_coin
        oldest_candle_volume_coin = res.oldest_candle_volume_coin
        oldest_candle_close_price = res.oldest_candle_close_price
        last_candle_close_price = res.last_candle_close_price
        last_candle_open_time = res.last_candle_open_time
        last_candle_close_time = res.last_candle_close_time
        min_passed = res.min_passed
        time_passed = minutes_to_human_readable(min_passed)
        is_price_spike = res.is_price_spike

        symbol_display = f"[bright_cyan]{symbol}[/bright_cyan]" if is_price_spike else f"{symbol}"
        volume_display = f"[green]{volume_change}[/green]%" if volume_change > 0 else f"[red]{volume_change}[/red]%"
        price_display = f"[green]{price_change:.2f}[/green]%" if price_change > 0 else f"[red]{price_change:.2f}[/red]%"  # 2 decimal places
        last_candle_volume_coin_display = f"{last_candle_volume_coin:,.2f}"  # Format with commas for readability
        oldest_candle_volume_coin_display = f"{oldest_candle_volume_coin:,.2f}"  # Format with commas for readability
        oldest_candle_close_price_display = f"{oldest_candle_close_price:,.6f}"  # 6 decimal places
        last_candle_close_price_display = f"{last_candle_close_price:,.6f}"  # 6 decimal places
        time_passed_display = "-" if min_passed <= 0 else f"[green]{time_passed}[green]" if min_passed < 60 else f"[red]{time_passed}[/red]"
        table.add_row(
            symbol_display,
            volume_display,
            price_display,
            last_candle_volume_coin_display,
            oldest_candle_volume_coin_display,
            oldest_candle_close_price_display,
            last_candle_close_price_display,
            last_candle_open_time,
            last_candle_close_time,
            time_passed_display
        )
    return table


def minutes_to_human_readable(minutes):
    d, minutes = divmod(minutes, 1440)
    h, m = divmod(minutes, 60)
    return f"{d}d " * (d > 0) + f"{h}h " * (h > 0) + f"{m}m" * (m > 0) or "0m"


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

            # Filter results: Keep only coins with Volume Change or Price Change above 0.5%
            filtered_results = [
                res for res in results
                if abs(res.volume_change) > 0.5 or abs(res.price_change) > 0.5
            ]

            # Sort results by Volume Change (descending) and Price Change (descending)
            sorted_results = sorted(
                filtered_results,
                key=lambda x: (-x.volume_change, -x.price_change)
            )

            # Trim the list to top N
            final_results = sorted_results[:args.count]

            # Create table
            table = create_table(final_results, start_time, args)
            console.print(table)

            if not args.watch:
                break

            await asyncio.sleep(args.wait)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Analyze volume changes of USDT coins on Binance Spot.')
    parser.add_argument('--interval', type=str, default="15m", help='Timeframe for volume analysis (e.g. 15m, 1h, 4h, 1d)')
    parser.add_argument('--range', type=str, default="6h", help='Time range for volume analysis (e.g. 4h, 1d, 3d)')
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
'''
'''
import asyncio
import platform
import sys
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
    'EOSUSDT', 'IOTAUSDT', 'ONTUSDT', 'ICXUSDT', 'NULSUSDT', 'VETUSDT', 'LINKUSDT', 'ONGUSDT', 'ZILUSDT', 'FETUSDT',
    'ZECUSDT', 'IOSTUSDT', 'CELRUSDT', 'THETAUSDT', 'ATOMUSDT', 'TFUELUSDT', 'ONEUSDT', 'ALGOUSDT', 'DUSKUSDT',
    'COSUSDT', 'MTLUSDT', 'WANUSDT', 'CVCUSDT', 'BANDUSDT', 'XTZUSDT', 'RVNUSDT', 'HBARUSDT', 'NKNUSDT', 'STXUSDT',
    'KAVAUSDT', 'ARPAUSDT', 'IOTXUSDT', 'RLCUSDT', 'CTXCUSDT', 'VITEUSDT', 'OGNUSDT', 'LSKUSDT', 'BNTUSDT', 'LTOUSDT',
    'COTIUSDT', 'STPTUSDT', 'DATAUSDT', 'CTSIUSDT', 'HIVEUSDT', 'CHRUSDT', 'ARDRUSDT', 'MDTUSDT', 'STMXUSDT', 'KNCUSDT',
    'SCUSDT', 'ZENUSDT', 'VTHOUSDT', 'DGBUSDT', 'SXPUSDT', 'DCRUSDT', 'STORJUSDT', 'BLZUSDT', 'KMDUSDT', 'NMRUSDT',
    'RSRUSDT', 'TRBUSDT', 'EGLDUSDT', 'DIAUSDT', 'FIOUSDT', 'UMAUSDT', 'OXTUSDT', 'UTKUSDT', 'NEARUSDT', 'FILUSDT',
    'CTKUSDT', 'AXSUSDT', 'STRAXUSDT', 'ROSEUSDT', 'AVAUSDT', 'SKLUSDT', 'GRTUSDT', 'CELOUSDT', 'RIFUSDT', 'CKBUSDT',
    'FIROUSDT', 'LITUSDT', 'SFPUSDT', 'FISUSDT', 'OMUSDT', 'PONDUSDT', 'ALICEUSDT', 'SUPERUSDT', 'CFXUSDT', 'PUNDIXUSDT',
    'TLMUSDT', 'FORTHUSDT', 'BURGERUSDT', 'ICPUSDT', 'ARUSDT', 'LPTUSDT', 'XVGUSDT', 'ATAUSDT', 'GTCUSDT', 'ERNUSDT',
    'PHAUSDT', 'MLNUSDT', 'C98USDT', 'CLVUSDT', 'QNTUSDT', 'FLOWUSDT', 'MINAUSDT', 'FARMUSDT', 'REQUSDT', 'GHSTUSDT',
    'WAXPUSDT', 'GNOUSDT', 'XECUSDT', 'ELFUSDT', 'VIDTUSDT', 'GALAUSDT', 'SYSUSDT', 'DFUSDT', 'FIDAUSDT', 'AGLDUSDT',
    'RADUSDT', 'BETAUSDT', 'RAREUSDT', 'LAZIOUSDT', 'ADXUSDT', 'AUCTIONUSDT', 'DARUSDT', 'MOVRUSDT', 'ENSUSDT', 'JASMYUSDT',
    'AMPUSDT', 'PYRUSDT', 'BICOUSDT', 'FLUXUSDT', 'VOXELUSDT', 'ACHUSDT', 'IMXUSDT', 'GLMRUSDT', 'SCRTUSDT', 'API3USDT',
    'XNOUSDT', 'ALPINEUSDT', 'TUSDT', 'ASTRUSDT', 'GMTUSDT', 'KDAUSDT', 'STEEMUSDT', 'REIUSDT', 'OPUSDT', 'STGUSDT',
    'POLYXUSDT', 'APTUSDT', 'PHBUSDT', 'HOOKUSDT', 'MAGICUSDT', 'PROSUSDT', 'SSVUSDT', 'AMBUSDT', 'GASUSDT', 'GLMUSDT',
    'QKCUSDT', 'IDUSDT', 'EDUUSDT', 'SUIUSDT', 'AERGOUSDT', 'ASTUSDT', 'SNTUSDT', 'COMBOUSDT', 'MAVUSDT', 'PENDLEUSDT',
    'ARKMUSDT', 'WLDUSDT', 'CYBERUSDT', 'ARKUSDT', 'IQUSDT', 'NTRNUSDT', 'TIAUSDT', 'BEAMXUSDT', 'PIVXUSDT', 'VICUSDT',
    'BLURUSDT', 'VANRYUSDT', 'JTOUSDT', 'ACEUSDT', 'NFPUSDT', 'AIUSDT', 'XAIUSDT', 'MANTAUSDT', 'ALTUSDT', 'PYTHUSDT',
    'RONINUSDT', 'DYMUSDT', 'PIXELUSDT', 'PORTALUSDT', 'PDAUSDT', 'AXLUSDT', 'METISUSDT', 'ENAUSDT', 'WUSDT', 'TNSRUSDT',
    'SAGAUSDT', 'TAOUSDT', 'REZUSDT', 'NOTUSDT', 'IOUSDT', 'ZKUSDT', 'ZROUSDT', 'RENDERUSDT', 'POLUSDT', 'EIGENUSDT',
    'SCRUSDT', 'LUMIAUSDT', 'KAIAUSDT', 'ACTUSDT', 'ACXUSDT',
]

# Type Definitions
KlineData = List[List[Any]]


@dataclass
class SymbolAnalysisResult:
    symbol: str
    volume_change: float
    price_change: float
    last_candle_volume_coin: float  # Volume in the coin
    last_candle_open_time: str  # Open time of the last candle
    last_candle_close_time: str  # Close time of the last candle
    oldest_candle_volume_coin: float  # Volume in the coin (oldest candle)
    oldest_candle_close_price: float  # Close price of the oldest candle
    last_candle_close_price: float  # Close price of the last candle
    min_passed: int = 0
    is_price_spike: bool = False


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
    match = re.match(r'^(\d+)([mhd])$', timeframe)
    if not match:
        raise ValueError(f"Invalid timeframe format: {timeframe}")
    value, unit = match.groups()
    multipliers = {'m': 1, 'h': 60, 'd': 1440}  # m -> 1, h -> 60, d -> 1440 (24 * 60)
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

        # Calculate volume change
        volumes = [float(candle[5]) for candle in current_data]  # Volume is the 6th element (index 5)
        if len(volumes) < 4:
            console.print(f"[yellow]Skipping {symbol}: Not enough volume data[/yellow]")
            return None

        # Take last 3 volumes for comparison

        volumes_last = volumes[-3:]

        volume_median = median(volumes)

        # Skip if median volume is zero to avoid division by zero
        if volume_median == 0:
            console.print(f"[yellow]Skipping {symbol}: Median volume is zero[/yellow]")
            return None

        #volume_last_min = min(volumes_last)
        volume_last_avg = mean(volumes_last)  # Calculate the average of the last 3 volumes

        volume_change = ((volume_last_avg - volume_median) / volume_median) * 100

        # Calculate price change
        prices = [float(candle[4]) for candle in current_data]  # Close prices (index 4)
        price_change = ((prices[-1] - prices[0]) / prices[0]) * 100

        # Get last candle details
        last_candle = current_data[-1]
        last_candle_volume_coin = float(last_candle[5])  # Volume in the coin
        last_candle_close_price = float(last_candle[4])  # Closing price of the last candle
        last_candle_open_time = datetime.fromtimestamp(last_candle[0] / 1000).strftime('%Y-%m-%d %H:%M:%S')
        last_candle_close_time = datetime.fromtimestamp(last_candle[6] / 1000).strftime('%Y-%m-%d %H:%M:%S')

        # Get oldest candle details
        oldest_candle = current_data[0]
        oldest_candle_volume_coin = float(oldest_candle[5])  # Volume in the coin (oldest candle)
        oldest_candle_close_price = float(oldest_candle[4])  # Close price of the oldest candle

        # Check for volume spike
        is_valid_spike = volume_last_avg > volume_median and volume_change >= args.threshold

        if not is_valid_spike:
            console.print(f"[yellow]Skipping {symbol}: No valid volume spike (Change: {volume_change:.2f}%)[/yellow]")
            return None

        # Check for sustained growth and price spike
        min_passed = 0
        is_price_spike = False
        sustained_growth_index = find_sustained_growth(volumes, threshold=args.threshold / 100, consecutive=3)
        if sustained_growth_index != -1:
            # Count items from this index to the end
            count_items_after = len(volumes) - sustained_growth_index
            min_passed = count_items_after * convert_interval_to_minutes(args.interval)
            # Average diff between max and min of prices
            avg_minmax_before_list = [abs(float(candle[2]) - float(candle[3])) for candle in current_data[:sustained_growth_index]]
            avg_minmax_after_list = [abs(float(candle[2]) - float(candle[3])) for candle in current_data[sustained_growth_index:]]
            avg_minmax_before, avg_minmax_after = mean(avg_minmax_before_list), mean(avg_minmax_after_list)
            price_change_threshold_ratio = 0.25
            is_price_spike = avg_minmax_after > avg_minmax_before * price_change_threshold_ratio

        return SymbolAnalysisResult(
            symbol=symbol,
            volume_change=volume_change,
            price_change=price_change,
            last_candle_volume_coin=last_candle_volume_coin,  # Volume in the coin
            last_candle_open_time=last_candle_open_time,  # Open time of the last candle
            last_candle_close_time=last_candle_close_time,  # Close time of the last candle
            oldest_candle_volume_coin=oldest_candle_volume_coin,  # Volume in the coin (oldest candle)
            oldest_candle_close_price=oldest_candle_close_price,  # Close price of the oldest candle
            last_candle_close_price=last_candle_close_price,  # Close price of the last candle
            min_passed=min_passed,
            is_price_spike=is_price_spike
        )
    except Exception as e:
        console.print(f"[red]Error analyzing symbol {symbol}: {e}[/red]")
        return None


def find_sustained_growth(data, threshold=0.5, consecutive=2):
    count = 0  # Keeps track of consecutive growth periods
    for i in range(1, len(data)):
        # Calculate relative growth between consecutive items
        relative_change = (data[i] - data[i - 1]) / data[i - 1]

        # Check if the growth exceeds the threshold
        if relative_change > threshold:
            count += 1  # Increment if there's a growth above the threshold
            # If sustained growth occurs for the required number of consecutive periods
            if count >= consecutive:
                return i - consecutive + 1  # Return the start of the sustained growth
        else:
            count = 0  # Reset count if growth is interrupted
    return -1  # Return -1 if no sustained growth is found


def create_table(results: List[SymbolAnalysisResult], last_updated: str, args: argparse.Namespace) -> Table:
    top_count = args.count
    table = Table(title=f"Binance Top {top_count} Boosters and Losers\nUpdated: {last_updated}")
    table.add_column(f"Symbol", style="cyan", no_wrap=True)
    table.add_column(f"Volume Change", style="magenta", no_wrap=True)
    table.add_column(f"Price Change", style="magenta", no_wrap=True)
    table.add_column(f"Last Candle Volume (Coin)", style="magenta", no_wrap=True)
    table.add_column(f"Oldest Candle Volume (Coin)", style="magenta", no_wrap=True)
    table.add_column(f"Oldest Candle Close Price", style="magenta", no_wrap=True)
    table.add_column(f"Last Candle Close Price", style="magenta", no_wrap=True)
    table.add_column(f"Last Candle Open Time", style="magenta", no_wrap=True)
    table.add_column(f"Last Candle Close Time", style="magenta", no_wrap=True)
    table.add_column(f"Time since", style="magenta", no_wrap=True)

    for res in results:
        symbol = res.symbol
        volume_change = round(res.volume_change)
        price_change = res.price_change  # Keep the original value without rounding
        last_candle_volume_coin = res.last_candle_volume_coin
        oldest_candle_volume_coin = res.oldest_candle_volume_coin
        oldest_candle_close_price = res.oldest_candle_close_price
        last_candle_close_price = res.last_candle_close_price
        last_candle_open_time = res.last_candle_open_time
        last_candle_close_time = res.last_candle_close_time
        min_passed = res.min_passed
        time_passed = minutes_to_human_readable(min_passed)
        is_price_spike = res.is_price_spike

        symbol_display = f"[bright_cyan]{symbol}[/bright_cyan]" if is_price_spike else f"{symbol}"
        volume_display = f"[green]{volume_change}[/green]%" if volume_change > 0 else f"[red]{volume_change}[/red]%"
        price_display = f"[green]{price_change:.2f}[/green]%" if price_change > 0 else f"[red]{price_change:.2f}[/red]%"  # 2 decimal places
        last_candle_volume_coin_display = f"{last_candle_volume_coin:,.2f}"  # Format with commas for readability
        oldest_candle_volume_coin_display = f"{oldest_candle_volume_coin:,.2f}"  # Format with commas for readability
        oldest_candle_close_price_display = f"{oldest_candle_close_price:,.6f}"  # 6 decimal places
        last_candle_close_price_display = f"{last_candle_close_price:,.6f}"  # 6 decimal places
        time_passed_display = "-" if min_passed <= 0 else f"[green]{time_passed}[green]" if min_passed < 60 else f"[red]{time_passed}[/red]"
        table.add_row(
            symbol_display,
            volume_display,
            price_display,
            last_candle_volume_coin_display,
            oldest_candle_volume_coin_display,
            oldest_candle_close_price_display,
            last_candle_close_price_display,
            last_candle_open_time,
            last_candle_close_time,
            time_passed_display
        )
    return table


def minutes_to_human_readable(minutes):
    d, minutes = divmod(minutes, 1440)
    h, m = divmod(minutes, 60)
    return f"{d}d " * (d > 0) + f"{h}h " * (h > 0) + f"{m}m" * (m > 0) or "0m"


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

            # Sort results by volume change (descending), price change (descending), and time since (ascending)
            final_results = sorted(results, key=lambda x: (-x.volume_change, -x.price_change, x.min_passed))
            # Trim the list to top N
            final_results = final_results[:args.count]

            # Create table
            table = create_table(final_results, start_time, args)
            console.print(table)

            if not args.watch:
                break

            await asyncio.sleep(args.wait)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Analyze volume changes of USDT coins on Binance Spot.')
    parser.add_argument('--interval', type=str, default="15m", help='Timeframe for volume analysis (e.g. 15m, 1h, 4h, 1d)')
    parser.add_argument('--range', type=str, default="6h", help='Time range for volume analysis (e.g. 4h, 1d, 3d)')
    parser.add_argument('--watch', action='store_true', help='Continuous monitoring mode')
    parser.add_argument('--threshold', type=str, default="50%", help='Volume change threshold, by default filter everything without 50% spikes')
    parser.add_argument('--wait', type=int, default=30, help='Interval for continuous monitoring mode')
    parser.add_argument('--count', type=int, default=12, help='Number of top symbols to display')
    args = parser.parse_args()

    args.max_concurrency = MAX_CONCURRENCY
    args.interval = make_more_human_readable_interval_label(args.interval)
    args.threshold = parse_percentage(args.threshold)

    try:
        asyncio.run(main(args))
    except KeyboardInterrupt:
        console.print("[red]Program terminated by user.[/red]")
'''
'''
import asyncio
import platform
import sys
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
    'EOSUSDT', 'IOTAUSDT', 'ONTUSDT', 'ICXUSDT', 'NULSUSDT', 'VETUSDT', 'LINKUSDT', 'ONGUSDT', 'ZILUSDT', 'FETUSDT',
    'ZECUSDT', 'IOSTUSDT', 'CELRUSDT', 'THETAUSDT', 'ATOMUSDT', 'TFUELUSDT', 'ONEUSDT', 'ALGOUSDT', 'DUSKUSDT',
    'COSUSDT', 'MTLUSDT', 'WANUSDT', 'CVCUSDT', 'BANDUSDT', 'XTZUSDT', 'RVNUSDT', 'HBARUSDT', 'NKNUSDT', 'STXUSDT',
    'KAVAUSDT', 'ARPAUSDT', 'IOTXUSDT', 'RLCUSDT', 'CTXCUSDT', 'VITEUSDT', 'OGNUSDT', 'LSKUSDT', 'BNTUSDT', 'LTOUSDT',
    'COTIUSDT', 'STPTUSDT', 'DATAUSDT', 'CTSIUSDT', 'HIVEUSDT', 'CHRUSDT', 'ARDRUSDT', 'MDTUSDT', 'STMXUSDT', 'KNCUSDT',
    'SCUSDT', 'ZENUSDT', 'VTHOUSDT', 'DGBUSDT', 'SXPUSDT', 'DCRUSDT', 'STORJUSDT', 'BLZUSDT', 'KMDUSDT', 'NMRUSDT',
    'RSRUSDT', 'TRBUSDT', 'EGLDUSDT', 'DIAUSDT', 'FIOUSDT', 'UMAUSDT', 'OXTUSDT', 'UTKUSDT', 'NEARUSDT', 'FILUSDT',
    'CTKUSDT', 'AXSUSDT', 'STRAXUSDT', 'ROSEUSDT', 'AVAUSDT', 'SKLUSDT', 'GRTUSDT', 'CELOUSDT', 'RIFUSDT', 'CKBUSDT',
    'FIROUSDT', 'LITUSDT', 'SFPUSDT', 'FISUSDT', 'OMUSDT', 'PONDUSDT', 'ALICEUSDT', 'SUPERUSDT', 'CFXUSDT', 'PUNDIXUSDT',
    'TLMUSDT', 'FORTHUSDT', 'BURGERUSDT', 'ICPUSDT', 'ARUSDT', 'LPTUSDT', 'XVGUSDT', 'ATAUSDT', 'GTCUSDT', 'ERNUSDT',
    'PHAUSDT', 'MLNUSDT', 'C98USDT', 'CLVUSDT', 'QNTUSDT', 'FLOWUSDT', 'MINAUSDT', 'FARMUSDT', 'REQUSDT', 'GHSTUSDT',
    'WAXPUSDT', 'GNOUSDT', 'XECUSDT', 'ELFUSDT', 'VIDTUSDT', 'GALAUSDT', 'SYSUSDT', 'DFUSDT', 'FIDAUSDT', 'AGLDUSDT',
    'RADUSDT', 'BETAUSDT', 'RAREUSDT', 'LAZIOUSDT', 'ADXUSDT', 'AUCTIONUSDT', 'DARUSDT', 'MOVRUSDT', 'ENSUSDT', 'JASMYUSDT',
    'AMPUSDT', 'PYRUSDT', 'BICOUSDT', 'FLUXUSDT', 'VOXELUSDT', 'ACHUSDT', 'IMXUSDT', 'GLMRUSDT', 'SCRTUSDT', 'API3USDT',
    'XNOUSDT', 'ALPINEUSDT', 'TUSDT', 'ASTRUSDT', 'GMTUSDT', 'KDAUSDT', 'STEEMUSDT', 'REIUSDT', 'OPUSDT', 'STGUSDT',
    'POLYXUSDT', 'APTUSDT', 'PHBUSDT', 'HOOKUSDT', 'MAGICUSDT', 'PROSUSDT', 'SSVUSDT', 'AMBUSDT', 'GASUSDT', 'GLMUSDT',
    'QKCUSDT', 'IDUSDT', 'EDUUSDT', 'SUIUSDT', 'AERGOUSDT', 'ASTUSDT', 'SNTUSDT', 'COMBOUSDT', 'MAVUSDT', 'PENDLEUSDT',
    'ARKMUSDT', 'WLDUSDT', 'CYBERUSDT', 'ARKUSDT', 'IQUSDT', 'NTRNUSDT', 'TIAUSDT', 'BEAMXUSDT', 'PIVXUSDT', 'VICUSDT',
    'BLURUSDT', 'VANRYUSDT', 'JTOUSDT', 'ACEUSDT', 'NFPUSDT', 'AIUSDT', 'XAIUSDT', 'MANTAUSDT', 'ALTUSDT', 'PYTHUSDT',
    'RONINUSDT', 'DYMUSDT', 'PIXELUSDT', 'PORTALUSDT', 'PDAUSDT', 'AXLUSDT', 'METISUSDT', 'ENAUSDT', 'WUSDT', 'TNSRUSDT',
    'SAGAUSDT', 'TAOUSDT', 'REZUSDT', 'NOTUSDT', 'IOUSDT', 'ZKUSDT', 'ZROUSDT', 'RENDERUSDT', 'POLUSDT', 'EIGENUSDT',
    'SCRUSDT', 'LUMIAUSDT', 'KAIAUSDT', 'ACTUSDT', 'ACXUSDT',
]

# Type Definitions
KlineData = List[List[Any]]


@dataclass
class SymbolAnalysisResult:
    symbol: str
    volume_change: float
    price_change: float
    last_candle_volume_coin: float  # Volume in the coin
    last_candle_open_time: str  # Open time of the last candle
    last_candle_close_time: str  # Close time of the last candle
    oldest_candle_volume_coin: float  # Volume in the coin (oldest candle)
    oldest_candle_close_price: float  # Close price of the oldest candle
    last_candle_close_price: float  # Close price of the last candle
    min_passed: int = 0
    is_price_spike: bool = False


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
    match = re.match(r'^(\d+)([mhd])$', timeframe)
    if not match:
        raise ValueError(f"Invalid timeframe format: {timeframe}")
    value, unit = match.groups()
    multipliers = {'m': 1, 'h': 60, 'd': 1440}  # m -> 1, h -> 60, d -> 1440 (24 * 60)
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

        # Calculate volume change
        volumes = [float(candle[5]) for candle in current_data]  # Volume is the 6th element (index 5)
        if len(volumes) < 4:
            console.print(f"[yellow]Skipping {symbol}: Not enough volume data[/yellow]")
            return None

        # Take last 3 volumes for comparison
        volumes_last = volumes[-3:]
        volume_median = median(volumes)

        # Skip if median volume is zero to avoid division by zero
        if volume_median == 0:
            console.print(f"[yellow]Skipping {symbol}: Median volume is zero[/yellow]")
            return None

        volume_last_min = min(volumes_last)
        volume_change = ((volume_last_min - volume_median) / volume_median) * 100

        # Calculate price change
        prices = [float(candle[4]) for candle in current_data]  # Close prices (index 4)
        price_change = ((prices[-1] - prices[0]) / prices[0]) * 100

        # Get last candle details
        last_candle = current_data[-1]
        last_candle_volume_coin = float(last_candle[5])  # Volume in the coin
        last_candle_close_price = float(last_candle[4])  # Closing price of the last candle
        last_candle_open_time = datetime.fromtimestamp(last_candle[0] / 1000).strftime('%Y-%m-%d %H:%M:%S')
        last_candle_close_time = datetime.fromtimestamp(last_candle[6] / 1000).strftime('%Y-%m-%d %H:%M:%S')

        # Get oldest candle details
        oldest_candle = current_data[0]
        oldest_candle_volume_coin = float(oldest_candle[5])  # Volume in the coin (oldest candle)
        oldest_candle_close_price = float(oldest_candle[4])  # Close price of the oldest candle

        # Check for volume spike
        is_valid_spike = volume_last_min > volume_median and volume_change >= args.threshold

        if not is_valid_spike:
            console.print(f"[yellow]Skipping {symbol}: No valid volume spike (Change: {volume_change:.2f}%)[/yellow]")
            return None

        # Check for sustained growth and price spike
        min_passed = 0
        is_price_spike = False
        sustained_growth_index = find_sustained_growth(volumes, threshold=args.threshold / 100, consecutive=3)
        if sustained_growth_index != -1:
            # Count items from this index to the end
            count_items_after = len(volumes) - sustained_growth_index
            min_passed = count_items_after * convert_interval_to_minutes(args.interval)
            # Average diff between max and min of prices
            avg_minmax_before_list = [abs(float(candle[2]) - float(candle[3])) for candle in current_data[:sustained_growth_index]]
            avg_minmax_after_list = [abs(float(candle[2]) - float(candle[3])) for candle in current_data[sustained_growth_index:]]
            avg_minmax_before, avg_minmax_after = mean(avg_minmax_before_list), mean(avg_minmax_after_list)
            price_change_threshold_ratio = 0.25
            is_price_spike = avg_minmax_after > avg_minmax_before * price_change_threshold_ratio

        return SymbolAnalysisResult(
            symbol=symbol,
            volume_change=volume_change,
            price_change=price_change,
            last_candle_volume_coin=last_candle_volume_coin,  # Volume in the coin
            last_candle_open_time=last_candle_open_time,  # Open time of the last candle
            last_candle_close_time=last_candle_close_time,  # Close time of the last candle
            oldest_candle_volume_coin=oldest_candle_volume_coin,  # Volume in the coin (oldest candle)
            oldest_candle_close_price=oldest_candle_close_price,  # Close price of the oldest candle
            last_candle_close_price=last_candle_close_price,  # Close price of the last candle
            min_passed=min_passed,
            is_price_spike=is_price_spike
        )
    except Exception as e:
        console.print(f"[red]Error analyzing symbol {symbol}: {e}[/red]")
        return None


def find_sustained_growth(data, threshold=0.5, consecutive=2):
    count = 0  # Keeps track of consecutive growth periods
    for i in range(1, len(data)):
        # Calculate relative growth between consecutive items
        relative_change = (data[i] - data[i - 1]) / data[i - 1]

        # Check if the growth exceeds the threshold
        if relative_change > threshold:
            count += 1  # Increment if there's a growth above the threshold
            # If sustained growth occurs for the required number of consecutive periods
            if count >= consecutive:
                return i - consecutive + 1  # Return the start of the sustained growth
        else:
            count = 0  # Reset count if growth is interrupted
    return -1  # Return -1 if no sustained growth is found


def create_table(results: List[SymbolAnalysisResult], last_updated: str, args: argparse.Namespace) -> Table:
    top_count = args.count
    table = Table(title=f"Binance Top {top_count} Boosters and Losers\nUpdated: {last_updated}")
    table.add_column(f"Symbol", style="cyan", no_wrap=True)
    table.add_column(f"Volume Change", style="magenta", no_wrap=True)
    table.add_column(f"Price Change", style="magenta", no_wrap=True)
    table.add_column(f"Last Candle Volume (Coin)", style="magenta", no_wrap=True)
    table.add_column(f"Oldest Candle Volume (Coin)", style="magenta", no_wrap=True)
    table.add_column(f"Oldest Candle Close Price", style="magenta", no_wrap=True)
    table.add_column(f"Last Candle Close Price", style="magenta", no_wrap=True)
    table.add_column(f"Last Candle Open Time", style="magenta", no_wrap=True)
    table.add_column(f"Last Candle Close Time", style="magenta", no_wrap=True)
    table.add_column(f"Time since", style="magenta", no_wrap=True)

    for res in results:
        symbol = res.symbol
        volume_change = round(res.volume_change)
        price_change = round(res.price_change)
        last_candle_volume_coin = res.last_candle_volume_coin
        oldest_candle_volume_coin = res.oldest_candle_volume_coin
        oldest_candle_close_price = res.oldest_candle_close_price
        last_candle_close_price = res.last_candle_close_price
        last_candle_open_time = res.last_candle_open_time
        last_candle_close_time = res.last_candle_close_time
        min_passed = res.min_passed
        time_passed = minutes_to_human_readable(min_passed)
        is_price_spike = res.is_price_spike

        symbol_display = f"[bright_cyan]{symbol}[/bright_cyan]" if is_price_spike else f"{symbol}"
        volume_display = f"[green]{volume_change}[/green]%" if volume_change > 0 else f"[red]{volume_change}[/red]%"
        price_display = f"[green]{price_change}[/green]%" if price_change > 0 else f"[red]{price_change}[/red]%"
        last_candle_volume_coin_display = f"{last_candle_volume_coin:,.2f}"  # Format with commas for readability
        oldest_candle_volume_coin_display = f"{oldest_candle_volume_coin:,.2f}"  # Format with commas for readability
        oldest_candle_close_price_display = f"{oldest_candle_close_price:,.6f}"  # 6 decimal places
        last_candle_close_price_display = f"{last_candle_close_price:,.6f}"  # 6 decimal places
        time_passed_display = "-" if min_passed <= 0 else f"[green]{time_passed}[green]" if min_passed < 60 else f"[red]{time_passed}[/red]"
        table.add_row(
            symbol_display,
            volume_display,
            price_display,
            last_candle_volume_coin_display,
            oldest_candle_volume_coin_display,
            oldest_candle_close_price_display,
            last_candle_close_price_display,
            last_candle_open_time,
            last_candle_close_time,
            time_passed_display
        )
    return table


def minutes_to_human_readable(minutes):
    d, minutes = divmod(minutes, 1440)
    h, m = divmod(minutes, 60)
    return f"{d}d " * (d > 0) + f"{h}h " * (h > 0) + f"{m}m" * (m > 0) or "0m"


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

            # Sort results by volume change (descending), price change (descending), and time since (ascending)
            final_results = sorted(results, key=lambda x: (-x.volume_change, -x.price_change, x.min_passed))
            # Trim the list to top N
            final_results = final_results[:args.count]

            # Create table
            table = create_table(final_results, start_time, args)
            console.print(table)

            if not args.watch:
                break

            await asyncio.sleep(args.wait)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Analyze volume changes of USDT coins on Binance Spot.')
    parser.add_argument('--interval', type=str, default="15m", help='Timeframe for volume analysis (e.g. 15m, 1h, 4h, 1d)')
    parser.add_argument('--range', type=str, default="6h", help='Time range for volume analysis (e.g. 4h, 1d, 3d)')
    parser.add_argument('--watch', action='store_true', help='Continuous monitoring mode')
    parser.add_argument('--threshold', type=str, default="50%", help='Volume change threshold, by default filter everything without 50% spikes')
    parser.add_argument('--wait', type=int, default=30, help='Interval for continuous monitoring mode')
    parser.add_argument('--count', type=int, default=12, help='Number of top symbols to display')
    args = parser.parse_args()

    args.max_concurrency = MAX_CONCURRENCY
    args.interval = make_more_human_readable_interval_label(args.interval)
    args.threshold = parse_percentage(args.threshold)

    try:
        asyncio.run(main(args))
    except KeyboardInterrupt:
        console.print("[red]Program terminated by user.[/red]")
'''
'''
import asyncio
import platform
import sys
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
'EOSUSDT',  'IOTAUSDT',  'ONTUSDT', 'ICXUSDT',
'NULSUSDT', 'VETUSDT',  'LINKUSDT', 'ONGUSDT', 'ZILUSDT', 'FETUSDT',  'ZECUSDT', 'IOSTUSDT', 'CELRUSDT', 
'THETAUSDT',  'ATOMUSDT', 'TFUELUSDT', 'ONEUSDT',  'ALGOUSDT','DUSKUSDT',   'COSUSDT', 'MTLUSDT',   'WANUSDT',
'CVCUSDT',  'BANDUSDT', 'XTZUSDT',  'RVNUSDT', 'HBARUSDT', 'NKNUSDT', 'STXUSDT', 'KAVAUSDT', 'ARPAUSDT', 'IOTXUSDT', 
'RLCUSDT', 'CTXCUSDT','VITEUSDT',   'OGNUSDT',  'LSKUSDT', 'BNTUSDT', 'LTOUSDT',  'COTIUSDT','STPTUSDT', 'DATAUSDT',
'CTSIUSDT', 'HIVEUSDT', 'CHRUSDT', 'ARDRUSDT', 'MDTUSDT', 'STMXUSDT', 'KNCUSDT', 'SCUSDT', 'ZENUSDT', 'VTHOUSDT',
'DGBUSDT', 'SXPUSDT', 'DCRUSDT', 'STORJUSDT', 'BLZUSDT', 'KMDUSDT',  'NMRUSDT',  'RSRUSDT',  'TRBUSDT',
'EGLDUSDT', 'DIAUSDT', 'FIOUSDT', 'UMAUSDT',    'OXTUSDT', 'UTKUSDT', 'NEARUSDT', 'FILUSDT',  'CTKUSDT',  'AXSUSDT',
'STRAXUSDT', 'ROSEUSDT', 'AVAUSDT', 'SKLUSDT', 'GRTUSDT',    'CELOUSDT', 'RIFUSDT',  'CKBUSDT','FIROUSDT', 'LITUSDT',
'SFPUSDT',   'FISUSDT', 'OMUSDT', 'PONDUSDT', 'ALICEUSDT',   'SUPERUSDT', 'CFXUSDT',  'PUNDIXUSDT', 'TLMUSDT',  'FORTHUSDT', 
'BURGERUSDT','ICPUSDT', 'ARUSDT',  'LPTUSDT', 'XVGUSDT', 'ATAUSDT', 'GTCUSDT', 'ERNUSDT', 'PHAUSDT', 'MLNUSDT', 
'C98USDT', 'CLVUSDT', 'QNTUSDT', 'FLOWUSDT', 'MINAUSDT',  'FARMUSDT',    'REQUSDT', 'GHSTUSDT','WAXPUSDT', 'GNOUSDT', 
'XECUSDT', 'ELFUSDT',  'VIDTUSDT',  'GALAUSDT',   'SYSUSDT','DFUSDT', 'FIDAUSDT', 'AGLDUSDT', 'RADUSDT', 'BETAUSDT',
'RAREUSDT', 'LAZIOUSDT',  'ADXUSDT', 'AUCTIONUSDT', 'DARUSDT', 'MOVRUSDT',  'ENSUSDT',    'JASMYUSDT', 'AMPUSDT', 'PYRUSDT',
'BICOUSDT','FLUXUSDT',  'VOXELUSDT',    'ACHUSDT', 'IMXUSDT', 'GLMRUSDT', 'SCRTUSDT', 'API3USDT',   'XNOUSDT',  'ALPINEUSDT',
'TUSDT', 'ASTRUSDT', 'GMTUSDT', 'KDAUSDT','STEEMUSDT',  'REIUSDT',  'OPUSDT',  'STGUSDT',   'POLYXUSDT','APTUSDT', 
'PHBUSDT', 'HOOKUSDT', 'MAGICUSDT',   'PROSUSDT',  'SSVUSDT',  'AMBUSDT',  'GASUSDT', 'GLMUSDT',  'QKCUSDT',  'IDUSDT',
'EDUUSDT', 'SUIUSDT', 'AERGOUSDT',   'ASTUSDT', 'SNTUSDT', 'COMBOUSDT', 'MAVUSDT', 'PENDLEUSDT', 'ARKMUSDT','WLDUSDT',
'CYBERUSDT', 'ARKUSDT',  'IQUSDT', 'NTRNUSDT', 'TIAUSDT','BEAMXUSDT', 'PIVXUSDT', 'VICUSDT', 'BLURUSDT', 'VANRYUSDT',
'JTOUSDT',  'ACEUSDT', 'NFPUSDT', 'AIUSDT','XAIUSDT', 'MANTAUSDT', 'ALTUSDT',  'PYTHUSDT', 'RONINUSDT', 'DYMUSDT',
'PIXELUSDT',  'PORTALUSDT', 'PDAUSDT', 'AXLUSDT','METISUSDT',    'ENAUSDT', 'WUSDT', 'TNSRUSDT', 'SAGAUSDT', 'TAOUSDT',
'REZUSDT','NOTUSDT', 'IOUSDT', 'ZKUSDT',  'ZROUSDT',  'RENDERUSDT',   'POLUSDT',      'EIGENUSDT', 'SCRUSDT',
'LUMIAUSDT', 'KAIAUSDT',  'ACTUSDT',  'ACXUSDT',]

# Type Definitions
KlineData = List[List[Any]]


@dataclass
class SymbolAnalysisResult:
    symbol: str
    volume_change: float
    price_change: float
    last_candle_volume_coin: float  # Volume in the coin
    last_candle_open_time: str  # Open time of the last candle
    last_candle_close_time: str  # Close time of the last candle
    oldest_candle_volume_coin: float  # Volume in the coin (oldest candle)
    oldest_candle_close_price: float  # Close price of the oldest candle
    last_candle_close_price: float  # Close price of the last candle
    min_passed: int = 0
    is_price_spike: bool = False


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
    match = re.match(r'^(\d+)([mhd])$', timeframe)
    if not match:
        raise ValueError(f"Invalid timeframe format: {timeframe}")
    value, unit = match.groups()
    multipliers = {'m': 1, 'h': 60, 'd': 1440}  # m -> 1, h -> 60, d -> 1440 (24 * 60)
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

        # Calculate volume change
        volumes = [float(candle[5]) for candle in current_data]
        if len(volumes) < 4:
            console.print(f"[yellow]Skipping {symbol}: Not enough volume data[/yellow]")
            return None

        # Take last 3 volumes for comparison
        volumes_last = volumes[-3:]
        volume_median = median(volumes)

        # Skip if median volume is zero to avoid division by zero
        if volume_median == 0:
            console.print(f"[yellow]Skipping {symbol}: Median volume is zero[/yellow]")
            return None

        volume_last_min = min(volumes_last)
        volume_change = ((volume_last_min - volume_median) / volume_median) * 100

        # Calculate price change
        prices = [float(candle[4]) for candle in current_data]  # Close prices
        price_change = ((prices[-1] - prices[0]) / prices[0]) * 100

        # Get last candle details
        last_candle = current_data[-1]
        last_candle_volume_coin = float(last_candle[5])  # Volume in the coin
        last_candle_close_price = float(last_candle[4])  # Closing price of the last candle
        last_candle_open_time = datetime.fromtimestamp(last_candle[0] / 1000).strftime('%Y-%m-%d %H:%M:%S')
        last_candle_close_time = datetime.fromtimestamp(last_candle[6] / 1000).strftime('%Y-%m-%d %H:%M:%S')

        # Get oldest candle details
        oldest_candle = current_data[0]
        oldest_candle_volume_coin = float(oldest_candle[5])  # Volume in the coin (oldest candle)
        oldest_candle_close_price = float(oldest_candle[4])  # Close price of the oldest candle

        # Check for volume spike
        is_valid_spike = volume_last_min > volume_median and volume_change >= args.threshold

        if not is_valid_spike:
            console.print(f"[yellow]Skipping {symbol}: No valid volume spike (Change: {volume_change:.2f}%)[/yellow]")
            return None

        # Check for sustained growth and price spike
        min_passed = 0
        is_price_spike = False
        sustained_growth_index = find_sustained_growth(volumes, threshold=args.threshold / 100, consecutive=3)
        if sustained_growth_index != -1:
            # Count items from this index to the end
            count_items_after = len(volumes) - sustained_growth_index
            min_passed = count_items_after * convert_interval_to_minutes(args.interval)
            # Average diff between max and min of prices
            avg_minmax_before_list = [abs(float(candle[2]) - float(candle[3])) for candle in current_data[:sustained_growth_index]]
            avg_minmax_after_list = [abs(float(candle[2]) - float(candle[3])) for candle in current_data[sustained_growth_index:]]
            avg_minmax_before, avg_minmax_after = mean(avg_minmax_before_list), mean(avg_minmax_after_list)
            price_change_threshold_ratio = 0.25
            is_price_spike = avg_minmax_after > avg_minmax_before * price_change_threshold_ratio

        return SymbolAnalysisResult(
            symbol=symbol,
            volume_change=volume_change,
            price_change=price_change,
            last_candle_volume_coin=last_candle_volume_coin,  # Volume in the coin
            last_candle_open_time=last_candle_open_time,  # Open time of the last candle
            last_candle_close_time=last_candle_close_time,  # Close time of the last candle
            oldest_candle_volume_coin=oldest_candle_volume_coin,  # Volume in the coin (oldest candle)
            oldest_candle_close_price=oldest_candle_close_price,  # Close price of the oldest candle
            last_candle_close_price=last_candle_close_price,  # Close price of the last candle
            min_passed=min_passed,
            is_price_spike=is_price_spike
        )
    except Exception as e:
        console.print(f"[red]Error analyzing symbol {symbol}: {e}[/red]")
        return None


def find_sustained_growth(data, threshold=0.5, consecutive=2):
    count = 0  # Keeps track of consecutive growth periods
    for i in range(1, len(data)):
        # Calculate relative growth between consecutive items
        relative_change = (data[i] - data[i - 1]) / data[i - 1]

        # Check if the growth exceeds the threshold
        if relative_change > threshold:
            count += 1  # Increment if there's a growth above the threshold
            # If sustained growth occurs for the required number of consecutive periods
            if count >= consecutive:
                return i - consecutive + 1  # Return the start of the sustained growth
        else:
            count = 0  # Reset count if growth is interrupted
    return -1  # Return -1 if no sustained growth is found


def create_table(results: List[SymbolAnalysisResult], last_updated: str, args: argparse.Namespace) -> Table:
    top_count = args.count
    table = Table(title=f"Binance Top {top_count} Boosters and Losers\nUpdated: {last_updated}")
    table.add_column(f"Symbol", style="cyan", no_wrap=True)
    table.add_column(f"Volume Change", style="magenta", no_wrap=True)
    table.add_column(f"Price Change", style="magenta", no_wrap=True)
    table.add_column(f"Last Candle Volume (Coin)", style="magenta", no_wrap=True)
    table.add_column(f"Oldest Candle Volume (Coin)", style="magenta", no_wrap=True)
    table.add_column(f"Oldest Candle Close Price", style="magenta", no_wrap=True)
    table.add_column(f"Last Candle Close Price", style="magenta", no_wrap=True)
    table.add_column(f"Last Candle Open Time", style="magenta", no_wrap=True)
    table.add_column(f"Last Candle Close Time", style="magenta", no_wrap=True)
    table.add_column(f"Time since", style="magenta", no_wrap=True)

    for res in results:
        symbol = res.symbol
        volume_change = round(res.volume_change)
        price_change = round(res.price_change)
        last_candle_volume_coin = res.last_candle_volume_coin
        oldest_candle_volume_coin = res.oldest_candle_volume_coin
        oldest_candle_close_price = res.oldest_candle_close_price
        last_candle_close_price = res.last_candle_close_price
        last_candle_open_time = res.last_candle_open_time
        last_candle_close_time = res.last_candle_close_time
        min_passed = res.min_passed
        time_passed = minutes_to_human_readable(min_passed)
        is_price_spike = res.is_price_spike

        symbol_display = f"[bright_cyan]{symbol}[/bright_cyan]" if is_price_spike else f"{symbol}"
        volume_display = f"[green]{volume_change}[/green]%" if volume_change > 0 else f"[red]{volume_change}[/red]%"
        price_display = f"[green]{price_change}[/green]%" if price_change > 0 else f"[red]{price_change}[/red]%"
        last_candle_volume_coin_display = f"{last_candle_volume_coin:,.2f}"  # Format with commas for readability
        oldest_candle_volume_coin_display = f"{oldest_candle_volume_coin:,.2f}"  # Format with commas for readability
        oldest_candle_close_price_display = f"{oldest_candle_close_price:,.2f}"  # Format with commas for readability
        last_candle_close_price_display = f"{last_candle_close_price:,.2f}"  # Format with commas for readability
        time_passed_display = "-" if min_passed <= 0 else f"[green]{time_passed}[green]" if min_passed < 60 else f"[red]{time_passed}[/red]"
        table.add_row(
            symbol_display,
            volume_display,
            price_display,
            last_candle_volume_coin_display,
            oldest_candle_volume_coin_display,
            oldest_candle_close_price_display,
            last_candle_close_price_display,
            last_candle_open_time,
            last_candle_close_time,
            time_passed_display
        )
    return table


def minutes_to_human_readable(minutes):
    d, minutes = divmod(minutes, 1440)
    h, m = divmod(minutes, 60)
    return f"{d}d " * (d > 0) + f"{h}h " * (h > 0) + f"{m}m" * (m > 0) or "0m"


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

            # Sort results by volume change (descending), price change (descending), and time since (ascending)
            final_results = sorted(results, key=lambda x: (-x.volume_change, -x.price_change, x.min_passed))
            # Trim the list to top N
            final_results = final_results[:args.count]

            # Create table
            table = create_table(final_results, start_time, args)
            console.print(table)

            if not args.watch:
                break

            await asyncio.sleep(args.wait)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Analyze volume changes of USDT coins on Binance Spot.')
    parser.add_argument('--interval', type=str, default="15m", help='Timeframe for volume analysis (e.g. 15m, 1h, 4h, 1d)')
    parser.add_argument('--range', type=str, default="6h", help='Time range for volume analysis (e.g. 4h, 1d, 3d)')
    parser.add_argument('--watch', action='store_true', help='Continuous monitoring mode')
    parser.add_argument('--threshold', type=str, default="50%", help='Volume change threshold, by default filter everything without 50% spikes')
    parser.add_argument('--wait', type=int, default=30, help='Interval for continuous monitoring mode')
    parser.add_argument('--count', type=int, default=12, help='Number of top symbols to display')
    args = parser.parse_args()

    args.max_concurrency = MAX_CONCURRENCY
    args.interval = make_more_human_readable_interval_label(args.interval)
    args.threshold = parse_percentage(args.threshold)

    try:
        asyncio.run(main(args))
    except KeyboardInterrupt:
        console.print("[red]Program terminated by user.[/red]")

'''