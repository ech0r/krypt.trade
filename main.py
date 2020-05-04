#!/usr/bin/python3

import requests
import dateparser
import pytz
import json
import hmac
import hashlib
import pandas as pd
import numpy
import matplotlib.pyplot as plt
import csv
import os.path
import time
from datetime import datetime, timezone
from secrets import * # Secrets file containing api key, etc.

class RoboTrader:
    
    def __init__(self, api_key, symbol):
        self.headers = {'X-MBX-APIKEY': api_key}
        self.exchange = "https://api.binance.com/"
        self.params = {'symbol': symbol}
        self.candlesticks = None
        self.historical_file_name = "historical_data.csv"

    ### HELPER FUNCTIONS ###

    def stringify_params(self, params):
        param_string = ""
        for i,x in enumerate(params.keys()):
            each_param = x + "=" + params[x]
            if i > 0:
                each_param = "&" + each_param
            param_string += each_param
        return param_string

    def save_historical_data(self, dataframe, mode=None):
        if mode == 'a':
            dataframe.to_csv(self.historical_file_name, mode='a', index=False, header=False)
        else:
            print("creating new historical_data.csv")
            dataframe.to_csv(self.historical_file_name, sep=",", index=False)
        
    def generate_signature(self, params, key):
        encoded_params = str.encode(self.stringify_params(params))
        encoded_key = str.encode(secret_key)
        sig = hmac.new(encoded_key, encoded_params, hashlib.sha256)
        return sig.hexdigest()    

    def get_ms_timestamp(self):
        # get UNIX epoch time
        timestamp = datetime.now(timezone.utc).timestamp() * 1000
        return str(int(timestamp))
    
    def date_to_ms(self, date):
        # get UNIX epoch time
        epoch = datetime.utcfromtimestamp(0).replace(tzinfo=pytz.utc)
        time = dateparser.parse(date)
        if time.tzinfo is None or time.tzinfo.utcoffset(time) is None:
            time = time.replace(tzinfo=pytz.utc)
        return int((time - epoch).total_seconds() * 1000.0)

    def interval_to_ms(self, interval):
        unit = interval[-1]
        milliseconds = None
        seconds_per_unit = {
            "m": 60,
            "h": 60*60,
            "d": 60*60*24,
            "w": 7*60*60*24
        }
        if unit in seconds_per_unit:
            try:
                milliseconds = int(interval[:-1]) * seconds_per_unit[unit] * 1000
            except ValueError:
                pass
        return milliseconds

    def candlestick_parser(self, data):
        columns = ["open_time", "open", "high", "low", "close", "volume", "close_time", "quote_asset_volume", "num_of_trades", "taker_buy_base_vol", "taker_buy_quote_vol", "x"]
        df = pd.DataFrame(data, columns=columns)
        return df

    #def trend_analyzer(self):


    ### API CALLS ###    
    
    def get_current_avg(self, symbol=None):
        params = self.params
        if symbol:
            params['symbol'] = symbol
        url = self.exchange + "api/v3/avgPrice"
        req = requests.get(url, params=self.params, headers=self.headers)
        return req.json()

    def get_ticker(self, symbol=None):
        params = self.params
        if symbol:
            params['symbol'] = symbol
        url = self.exchange + "/api/v3/ticker/price"
        req = requests.get(url, params=params, headers=self.headers)
        return req.json()

    def get_candlestick(self, interval, symbol=None, limit=None, start_time=None, end_time=None):
        url = self.exchange + "/api/v3/klines"
        params = self.params
        params['interval'] = interval
        params['symbol'] = symbol if symbol else self.params['symbol']
        params['limit'] = limit if limit else None
        params['startTime'] = start_time if start_time else None
        params['endTime'] = end_time if end_time else None
        params = {k:v for k,v in params.items() if v is not None}
        req = requests.get(url, params=params, headers=self.headers)
        return self.candlestick_parser(req.json())

    def get_historical_data(self, symbol, interval, limit=None, start=None, end=None):
        limit = limit if limit else 1000
        interval_ms = self.interval_to_ms(interval) * limit
        start_ms = self.date_to_ms(start) if start else None
        end_ms = self.date_to_ms(end) if end else None
        # Not always apparent when a symbol was added to Binance
        symbol_existed = False
        historical_data = None # holds Dataframe of past candlesticks
        i = 0
        start = start_ms
        while True:
            print("Running loop %d" % (i+1))
            temp_data = self.get_candlestick(interval, symbol, limit, start)
            if not temp_data.empty:
                print(temp_data)
                if i == 0:
                    historical_data = temp_data
                else:
                    historical_data = historical_data.append(temp_data)
                # check if we have reached the end date
                beginning_of_candlestick = temp_data['open_time'].values[0]
                end_of_candlestick = temp_data['open_time'].values[-1]
                if end_ms <= end_of_candlestick:
                    break
                start = temp_data['close_time'].values[-1] + 1
            else:
                start += interval_ms
            i += 1
        # not totally necessary - but if API returns duplicate rows, we can remove it with this.
        historical_data.drop_duplicates(inplace=True)
        historical_data = historical_data[historical_data.open_time <= end_ms]
        return historical_data

    def get_all_orders(self):
        url = self.exchange + "api/v3/allOrders"
        params = self.params
        params['timestamp'] = self.get_ms_timestamp()
        params['recvWindow'] = '5000'
        params['signature'] = self.generate_signature(self.params, secret_key)
        req = requests.get(url, params=params, headers=self.headers)
        return req.json()

    def get_open_orders(self):
        url = self.exchange + "api/v3/openOrders"
        params = self.params
        params['timestamp'] = self.get_ms_timestamp()
        params['recvWindow'] = '5000'
        params['signature'] = self.generate_signature(self.params, secret_key)

    def place_order(self, side, order_type, time_in_force=None):
        url = self.exchange + "api/v3/order"
        params=self.params
        if time_in_force:
            params['timeInForce'] = time_in_force
        params['timestamp'] = self.get_ms_timestamp()
        params['recvWindow'] = '5000'
        params['signature'] = self.generate_signature(self.params, secret_key)
        params['side'] = side
        params['type'] = order_type
        params['quantity']
        req = requests.post(url, params=params, headers=self.headers)

if __name__ == "__main__":
    robot = RoboTrader(api_key, 'BTCUSDT')
    historical_data = robot.get_historical_data('BTCUSDT', '15m', 1000, "January 20, 2020", "March 25, 2020, 4pm")
    robot.save_historical_data(historical_data)