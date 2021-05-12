import operator
import numpy as np
import pandas as pd

from typing import List, Dict, Union, Optional, Tuple, Any

from bot_objects.stock_frame import StockFrame


class Indicators:

    def __init__(self, stock_frame: StockFrame) -> None:
        self._stock_frame: StockFrame = stock_frame
        self._price_groups = stock_frame.symbol_groups
        self._current_indicators = {}
        self._indicator_signals = {}
        self._frame = self._stock_frame.frame

    def set_indicator_signal(self, indicator: str, buy: float, sell: float, condition_buy: Any, condition_sell: Any) -> None:
        # if there's no signal for that indicator, set a template
        if indicator not in self._indicator_signals:
            self._indicator_signals[indicator] = {}

        # modify the signal
        self._indicator_signals[indicator]['buy'] = buy
        self._indicator_signals[indicator]['sell'] = sell
        self._indicator_signals[indicator]['buy_operator'] = condition_buy
        self._indicator_signals[indicator]['sell_operator'] = condition_sell

    def get_indicator_signals(self, indicator: Optional[str]) -> dict:
        if indicator and indicator in self._indicator_signals:
            return self._indicator_signals[indicator]
        else:
            return self._indicator_signals
    
    @property
    def stock_frame(self) -> pd.DataFrame:
        return self._frame

    @stock_frame.setter
    def stock_frame(self, stock_frame: pd.DataFrame) -> None:
        self._frame = stock_frame
    
    def change_in_price(self) -> pd.DataFrame:
        locals_data = locals()
        del locals_data['self']

        column_name = 'change_in_price'
        self._current_indicators[column_name] = {}
        self._current_indicators[column_name]['args'] = locals_data
        self._current_indicators[column_name]['func'] = self.change_in_price

        self._frame[column_name] = self._price_groups['close'].transform(
            lambda x: x.diff()
        )

    def rsi(self, period: int, method: str = 'wilders') -> pd.DataFrame:
        locals_data = locals()
        del locals_data['self']

        column_name = 'rsi'
        self._current_indicators[column_name] = {}
        self._current_indicators[column_name]['args'] = locals_data
        self._current_indicators[column_name]['func'] = self.rsi

        if 'change_in_price' not in self._frame.columns:
            self.change_in_price()
        
        # define the up days
        self._frame['up_day'] = self._price_groups['change_in_price'].transform(
            lambda x: np.where(x >= 0, x, 0)
        )

        # define the down days
        self._frame['down_day'] = self._price_groups['change_in_price'].transform(
            lambda x: np.where(x < 0, x.abs(), 0)
        )

        # define the exponential weighted moving average (EWMA) up days
        self._frame['ewma_up'] = self._price_groups['up_day'].transform(
            lambda x: x.ewm(span=period).mean()
        )

        # define the exponential weighted moving average (EWMA) down days
        self._frame['ewma_down'] = self._price_groups['down_day'].transform(
            lambda x: x.ewm(span=period).mean()
        )

        relative_strength = self._frame['ewma_up'] / self._frame['ewma_down']

        relative_strength_index = 100.0 - (100.0 / (1.0 + relative_strength))

        # add RSI indicator to the dataframe
        self._frame['rsi'] = np.where(relative_strength_index == 0, 100, relative_strength_index)

        # clean up before sending back
        self._frame.drop(
            labels=['ewma_up', 'ewma_down', 'down_day', 'up_day', 'change_in_price'],
            axis=1,
            inplace=True
        )

        return self._frame

    # simple moving average indicator
    def sma(self, period: int) -> pd.DataFrame:
        locals_data = locals()
        del locals_data['self']

        column_name = 'sma'
        self._current_indicators[column_name] = {}
        self._current_indicators[column_name]['args'] = locals_data
        self._current_indicators[column_name]['func'] = self.sma

        # add the SMA
        self._frame[column_name] = self._price_groups['close'].transform(
            lambda x: x.rolling(window=period).mean()
        )

        return self._frame

    # exponential moving average
    def ema(self, period: int, alpha: float = 0.0) -> pd.DataFrame:
        locals_data = locals()
        del locals_data['self']

        column_name = 'ema'
        self._current_indicators[column_name] = {}
        self._current_indicators[column_name]['args'] = locals_data
        self._current_indicators[column_name]['func'] = self.ema

        # add the SMA
        self._frame[column_name] = self._price_groups['close'].transform(
            lambda x: x.ewm(span=period).mean()
        )

        return self._frame

    def refresh(self) -> None:
        # first update the groups
        self._price_groups = self._stock_frame.symbol_groups

        # loop through all the stored indicators
        for indicator in self._current_indicators:
            indicator_arguments = self._current_indicators[indicator]['args']
            indicator_function = self._current_indicators[indicator]['func']

            # update the columns
            indicator_function(**indicator_arguments)

    def check_signals(self) -> Union[pd.DataFrame, None]:
        signals_df = self._stock_frame._check_signals(indicators=self._indicator_signals)

        return signals_df