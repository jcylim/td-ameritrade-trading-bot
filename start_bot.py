import time as true_time
import pprint
import pathlib
import operator
import pandas as pd

from datetime import datetime, timedelta
from configparser import ConfigParser

from bot_objects.bot import PyRobot
from bot_objects.indicators import Indicators

# grab the config file values
config = ConfigParser()
config.read('configs/config.ini')

CLIENT_ID = config.get('main', 'CLIENT_ID')
REDIRECT_URI = config.get('main', 'REDIRECT_URI')
CREDENTIALS_PATH = config.get('main', 'JSON_PATH')
ACCOUNT_NUMBER = config.get('main', 'ACCOUNT_NUMBER')
CHROME_DRIVER = config.get('main', 'CHROME_DRIVER')

print(f'client_id: {CLIENT_ID}')
print(f'redirect_uri: {REDIRECT_URI}')
print(f'credentials_path: {CREDENTIALS_PATH}')
print(f'account_number: {ACCOUNT_NUMBER}')
print(f'chrome_driver: {CHROME_DRIVER}')

# initialize the bot
trading_bot = PyRobot(
    client_id=CLIENT_ID,
    redirect_uri=REDIRECT_URI,
    credentials_path=CREDENTIALS_PATH,
    trading_acct=ACCOUNT_NUMBER
)

# create new portfolio
trading_bot_portfolio = trading_bot.create_portfolio()

# add multiple positions to our portfolio
multiple_positions = [
    {
        'asset_type': 'equity',
        'quantity': 2,
        'purchase_price': 4.00,
        'symbol': 'TSLA',
        'purchase_date': '2020-01-31'
    },
    {
        'asset_type': 'equity',
        'quantity': 2,
        'purchase_price': 4.00,
        'symbol': 'SQ',
        'purchase_date': '2020-01-31'
    }
]

# add positions to portfolio
new_positions = trading_bot.portfolio.add_positions(positions=multiple_positions)
pprint.pprint(new_positions)

# add a single position to the portfolio
trading_bot.portfolio.add_position(
    symbol='MSFT',
    quantity=10,
    purchase_price=10.00,
    asset_type='equity',
    purchase_date='2021-04-01'
)
pprint.pprint(trading_bot.portfolio.positions)

# check to see if the regular market is open
if trading_bot.regular_market_open:
    print('Regular Market Open')
else:
    print('Regular Market Not Open')

# check to see if the pre market is open
if trading_bot.pre_market_open:
    print('Pre Market Open')
else:
    print('Pre Market Not Open')

# check to see if the post market is open
if trading_bot.post_market_open:
    print('Post Market Open')
else:
    print('Post Market Not Open')

# grab the current quotes in our portfolio
current_quotes = trading_bot.grab_current_quotes()
# pprint.pprint(current_quotes)

# define our date range
end_date = datetime.today()
start_date = end_date - timedelta(days=30)

# grab historical prices
historical_prices = trading_bot.grab_historical_prices(
    start=start_date,
    end=end_date,
    bar_size=1,
    bar_type='minute'
)

# convert data into stockframe
stock_frame = trading_bot.create_stock_frame(data=historical_prices['aggregated'])

# print head of StockFrame
pprint.pprint(stock_frame.frame.head(n=20))

# Create a new Trade Object.
new_trade = trading_bot.create_trade(
    trade_id='long_fb',
    enter_or_exit='enter',
    long_or_short='short',
    order_type='lmt',
    price=318.00
)

# Make it Good Till Cancel.
new_trade.good_till_cancel(cancel_time=datetime.now() + timedelta(minutes=90))

# Change the session
new_trade.modify_session(session='am')

# Add an Order Leg.
new_trade.instrument(
    symbol='FB',
    quantity=1,
    asset_type='EQUITY'
)

# Add a Stop Loss Order with the Main Order.
new_trade.add_stop_loss(
    stop_size=.10,
    percentage=False
)

# Print out the order.
pprint.pprint(new_trade.order)

# create a new indicator client
indicator_client = Indicators(stock_frame=stock_frame)

# add the RSI indicator 
indicator_client.rsi(period=14)

# add a 200-day simple moving average
indicator_client.sma(period=200)

# add a 50-day exponential moving average
indicator_client.ema(period=50)

# add a signal to check for
indicator_client.set_indicator_signal(
    indicator='rsi',
    buy=40.0,
    sell=20.0,
    condition_buy=operator.ge,
    condition_sell=operator.le
)

# define a trade dictionary
trades_dict = {
    'FB': {
        'trade_func': trading_bot.trades['long_fb'],
        'trade_id': trading_bot.trades['long_fb'].trade_id
    }
}

while True:
    if trading_bot.regular_market_open or trading_bot.pre_market_open or trading_bot.post_market_open:
        # grab the latest bar
        latest_bars = trading_bot.get_latest_bar()

        # add those bars to the StockFrame
        stock_frame.add_rows(data=latest_bars)

        # refresh the indicators
        indicator_client.refresh()

        print("="*50)
        print("Current StockFrame")
        print("-"*50)
        print(stock_frame.symbol_groups.tail())
        print("-"*50)
        print("")

        # Check for signals.
        # signals = indicator_client.check_signals()

        # # execute trades
        # trading_bot.execute_signals(signals=signals, trades_to_execute=trades_dict)

        # grab the last bar, keep in mind this is after adding the new rows
        last_bar_timestamp = trading_bot.stock_frame.frame.tail(1).index.get_level_values(1)

        # wait till the next bar
        trading_bot.wait_till_next_bar(last_bar_timestamp=last_bar_timestamp)
    
    else:
        print("Market not opened atm")
        true_time.sleep(10)