import pandas as pd
import time as time_true
import holidays

from td.client import TDClient
from td.utils import TDUtilities

from datetime import datetime, time, timezone, timedelta

from typing import List, Dict, Union, Optional

from bot_objects.portfolio import Portfolio
from bot_objects.stock_frame import StockFrame
from bot_objects.trades import Trades


class PyRobot:

    def __init__(self, client_id: str, redirect_uri: str, credentials_path: str = None, trading_acct: str = None, paper_trading: bool = True) -> None:
        self._us_holidays = holidays.US()

        self.trading_acct: str = trading_acct
        self.client_id: str = client_id
        self.redirect_uri: str = redirect_uri
        self.credentials_path: str = credentials_path

        self.session: TDClient = self._create_session()
        self.trades: dict = {}
        self.historical_prices: dict = {}
        self.paper_trading = paper_trading

    def _create_session(self) -> TDClient:
        td_client: TDClient = TDClient(
            client_id=self.client_id,
            redirect_uri=self.redirect_uri,
            credentials_path=self.credentials_path
        )

        # login to the session
        td_client.login()

        return td_client

    @property
    def pre_market_open(self) -> bool:
        pre_market_start_time = datetime.utcnow().replace(hour=12, minute=00, second=00).timestamp()
        market_start_time = datetime.utcnow().replace(hour=13, minute=30, second=00).timestamp()
        right_now = datetime.utcnow().timestamp()

        is_holiday = True if datetime.utcnow().date() in self._us_holidays else False

        if datetime.utcnow().date().weekday() <= 4 and pre_market_start_time <= right_now <= market_start_time and not is_holiday:
            return True
        else:
            return False

    @property
    def post_market_open(self) -> bool:
        post_market_start_time = datetime.utcnow().replace(hour=22, minute=30, second=00).timestamp()
        market_end_time = datetime.utcnow().replace(hour=20, minute=00, second=00).timestamp()
        right_now = datetime.utcnow().timestamp()

        is_holiday = True if datetime.utcnow().date() in self._us_holidays else False

        if datetime.utcnow().date().weekday() <= 4 and market_end_time <= right_now <= post_market_start_time and not is_holiday:
            return True
        else:
            return False
    
    @property
    def regular_market_open(self) -> bool:
        market_start_time = datetime.utcnow().replace(hour=13, minute=30, second=00).timestamp()
        market_end_time = datetime.utcnow().replace(hour=20, minute=00, second=00).timestamp()
        right_now = datetime.utcnow().timestamp()

        is_holiday = True if datetime.utcnow().date() in self._us_holidays else False

        if datetime.utcnow().date().weekday() <= 4 and market_start_time <= right_now <= market_end_time and not is_holiday:
            return True
        else:
            return False

    def create_portfolio(self):
        # initialize a new portfolio object
        self.portfolio = Portfolio(account_number=self.trading_acct)

        # assign the client
        self.portfolio.td_client = self.session

        return self.portfolio

    def create_trade(self, trade_id: str, enter_or_exit: str, long_or_short: str, order_type: str = 'mkt', price: float = 0.0, stop_limit_price: float = 0.0) -> Trades:
        # initialize a new trade object
        trade = Trades()

        # create a new trade
        trade.new_trade(
            trade_id=trade_id,
            order_type=order_type,
            enter_or_exit=enter_or_exit,
            long_or_short=long_or_short,
            price=price,
            stop_limit_price=stop_limit_price
        )

        self.trades[trade_id] = trade
        
        return trade
    
    def create_stock_frame(self, data: List[Dict]) -> StockFrame:
        self.stock_frame = StockFrame(data=data)

        return self.stock_frame

    def grab_current_quotes(self) -> dict:
        # first grab all the symbols
        symbols = self.portfolio.positions.keys()

        # grab the quotes
        quotes = self.session.get_quotes(instruments=list(symbols))

        return quotes

    def grab_historical_prices(self, start: datetime, end: datetime, bar_size: int = 1, bar_type: str = 'min', symbols: Optional[List[str]] = None) -> List[Dict]:
        self._bar_size = bar_size
        self._bar_type = bar_type

        # start = str(TDUtilities.milliseconds_since_epoch(dt_object=start))
        # end = str(TDUtilities.milliseconds_since_epoch(dt_object=end))
        start = str(int(start.timestamp() * 1000))
        end = str(int(end.timestamp() * 1000))

        new_prices = []

        if not symbols:
            symbols = self.portfolio.positions

        for symbol in symbols:
            historical_price_response = self.session.get_price_history(
                symbol=symbol,
                period_type='day',
                start_date=start,
                end_date=end,
                frequency_type=bar_type,
                frequency=bar_size,
                extended_hours=True
            )

            self.historical_prices[symbol] = {}
            self.historical_prices[symbol]['candles'] = historical_price_response['candles']

            for candle in historical_price_response['candles']:
                new_price_mini_dict = {}
                new_price_mini_dict['symbol'] = symbol
                new_price_mini_dict['open'] = candle['open']
                new_price_mini_dict['close'] = candle['close']
                new_price_mini_dict['high'] = candle['high']
                new_price_mini_dict['low'] = candle['low']
                new_price_mini_dict['volume'] = candle['volume']
                new_price_mini_dict['datetime'] = candle['datetime']
                new_prices.append(new_price_mini_dict)

        self.historical_prices['aggregated'] = new_prices

        return self.historical_prices
               
    def get_latest_bar(self) -> List[Dict]:
        bar_size = self._bar_size
        bar_type = self._bar_type

        # define our date range
        end_date = datetime.today()
        start_date = end_date - timedelta(minutes=15)

        start = str(int(start_date.timestamp() * 1000))
        end = str(int(end_date.timestamp() * 1000))

        latest_prices = []

        for symbol in self.portfolio.positions:
            try:
                # Grab the request.
                historical_prices_response = self.session.get_price_history(
                    symbol=symbol,
                    period_type='day',
                    start_date=start,
                    end_date=end,
                    frequency_type=bar_type,
                    frequency=bar_size,
                    extended_hours=True
                )
            except:
                time_true.sleep(2)

                # Grab the request.
                historical_prices_response = self.session.get_price_history(
                    symbol=symbol,
                    period_type='day',
                    start_date=start,
                    end_date=end,
                    frequency_type=bar_type,
                    frequency=bar_size,
                    extended_hours=True
                )

            for candle in historical_prices_response['candles'][-1:]:
                new_price_mini_dict = {}
                new_price_mini_dict['symbol'] = symbol
                new_price_mini_dict['open'] = candle['open']
                new_price_mini_dict['close'] = candle['close']
                new_price_mini_dict['high'] = candle['high']
                new_price_mini_dict['low'] = candle['low']
                new_price_mini_dict['volume'] = candle['volume']
                new_price_mini_dict['datetime'] = candle['datetime']
                latest_prices.append(new_price_mini_dict)

        return latest_prices

    def wait_till_next_bar(self, last_bar_timestamp: pd.DatetimeIndex) -> None:
        last_bar_time = last_bar_timestamp.to_pydatetime()[0].replace(tzinfo=timezone.utc)
        next_bar_time = last_bar_time + timedelta(seconds=60)
        curr_bar_time = datetime.now(tz=timezone.utc)

        last_bar_timestamp = int(last_bar_time.timestamp())
        next_bar_timestamp = int(next_bar_time.timestamp())
        curr_bar_timestamp = int(curr_bar_time.timestamp())

        _time_to_wait_bar = next_bar_timestamp - last_bar_timestamp
        time_to_wait_now = next_bar_timestamp - curr_bar_timestamp

        if time_to_wait_now < 0:
            time_to_wait_now = 0

        print(f"{last_bar_time.strftime('%Y-%m-%d %H:%M:%S')}")

        print("=" * 80)
        print("Pausing for the next bar")
        print("-" * 80)
        print(f"Curr Time: {curr_bar_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Next Time: {next_bar_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Sleep Time: {time_to_wait_now}")
        print("-" * 80)
        print('')

        time_true.sleep(time_to_wait_now)

    def execute_signals(self, signals: List[pd.Series], trades_to_execute: dict) -> List[dict]:        
        # Define the Buy and sells.
        buys: pd.Series = signals['buys']
        sells: pd.Series = signals['sells']

        order_responses = []

        # If we have buys or sells continue.
        if not buys.empty:

            # Grab the buy Symbols.
            symbols_list = buys.index.get_level_values(0).to_list()

            # Loop through each symbol.
            for symbol in symbols_list:

                # Check to see if there is a Trade object.
                if symbol in trades_to_execute:

                    if self.portfolio.in_portfolio(symbol=symbol):
                        self.portfolio.set_ownership_status(
                            symbol=symbol,
                            ownership=True
                        )

                    # Set the Execution Flag.
                    trades_to_execute[symbol]['has_executed'] = True
                    trade_obj: Trade = trades_to_execute[symbol]['buy']['trade_func']

                    if not self.paper_trading:
                        # Execute the order.
                        order_response = self.execute_orders(
                            trade_obj=trade_obj
                        )

                        order_response = {
                            'order_id': order_response['order_id'],
                            'request_body': order_response['request_body'],
                            'timestamp': datetime.now().isoformat()
                        }
                    else:
                        order_response = {
                            'order_id': trade_obj._generate_order_id(),
                            'request_body': trade_obj.order,
                            'timestamp': datetime.now().isoformat()
                        }

                    order_responses.append(order_response)

        elif not sells.empty:
            # Grab the sell Symbols.
            symbols_list = sells.index.get_level_values(0).to_list()

            # Loop through each symbol.
            for symbol in symbols_list:

                # Check to see if there is a Trade object.
                if symbol in trades_to_execute:

                    # Set the Execution Flag.
                    trades_to_execute[symbol]['has_executed'] = True

                    if self.portfolio.in_portfolio(symbol=symbol):
                        self.portfolio.set_ownership_status(
                            symbol=symbol,
                            ownership=False
                        )

                    trade_obj: Trade = trades_to_execute[symbol]['sell']['trade_func']

                    if not self.paper_trading:
                        # Execute the order.
                        order_response = self.execute_orders(
                            trade_obj=trade_obj
                        )

                        order_response = {
                            'order_id': order_response['order_id'],
                            'request_body': order_response['request_body'],
                            'timestamp': datetime.now().isoformat()
                        }
                    else:

                        order_response = {
                            'order_id': trade_obj._generate_order_id(),
                            'request_body': trade_obj.order,
                            'timestamp': datetime.now().isoformat()
                        }

                    order_responses.append(order_response)

        # Save the response.
        self.save_orders(order_response_dict=order_responses)

        return order_responses

    def execute_orders(self, trade_obj: Trades) -> dict:
        # Execute the order.
        order_dict = self.session.place_order(
            account=self.trading_account,
            order=trade_obj.order
        )

        # Store the order.
        trade_obj._order_response = order_dict

        # Process the order response.
        trade_obj._process_order_response()

        return order_dict

    def save_orders(self, order_response_dict: dict) -> bool:
        """Saves the order to a JSON file for further review.
        Arguments:
        ----
        order_response {dict} -- A single order response.
        Returns:
        ----
        {bool} -- `True` if the orders were successfully saved.
        """

        def default(obj):
            if isinstance(obj, bytes):
                return str(obj)

        # Define the folder.
        folder: pathlib.PurePath = pathlib.Path(
            __file__
        ).parents[1].joinpath("data")

        # See if it exist, if not create it.
        if not folder.exists():
            folder.mkdir()

        # Define the file path.
        file_path = folder.joinpath('orders.json')

        # First check if the file alread exists.
        if file_path.exists():
            with open('data/orders.json', 'r') as order_json:
                orders_list = json.load(order_json)
        else:
            orders_list = []

        # Combine both lists.
        orders_list = orders_list + order_response_dict

        # Write the new data back.
        with open(file='data/orders.json', mode='w+') as order_json:
            json.dump(obj=orders_list, fp=order_json, indent=4, default=default)

        return True
