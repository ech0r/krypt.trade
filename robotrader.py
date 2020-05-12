#!/usr/bin/python3

######################### IMPORTS ###################################################################
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
from colors import * # Prompt colors
# Attempt to import API keys from secrets file, if not available can't run.
try:
    from secrets import secret_key, api_key # Secrets file containing api key, etc.
except ImportError:
    print(f"{colors.FAIL}[ERROR]: Unable to import secrets file. Please check configuration. {colors.ENDC}")


######################## ROBOTRADER #################################################################

class RoboTrader:
    
    def __init__(self, api_key, symbol, trading_interval=None):
        self.headers = {'X-MBX-APIKEY': api_key}
        self.exchange = "https://api.binance.com/"
        self.params = {'symbol': symbol}
        self.candlesticks = None
        self.trading_interval=trading_interval
        self.historical_file_name = "historical_data.csv"

    ########################## HELPER FUNCTIONS #####################################################

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
            print(f"{colors.OKBLUE}[INFO]: Creating historical_data.csv.{colors.ENDC}")
            dataframe.to_csv(self.historical_file_name, sep=",", index=False)
            print(f"{colors.OKGREEN}[SUCCESS]: historical_data.csv saved.{colors.ENDC}")
        
    def generate_signature(self, params, key):
        encoded_params = str.encode(self.stringify_params(params))
        encoded_key = str.encode(secret_key)
        sig = hmac.new(encoded_key, encoded_params, hashlib.sha256)
        return sig.hexdigest()    

    def get_ms_timestamp(self):
        # Get UNIX/POSIX/epoch time
        timestamp = datetime.now(timezone.utc).timestamp() * 1000
        return str(int(timestamp))
    
    def date_to_ms(self, date):
        # Get UNIX/POSIX/epoch time
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

    ######################### API CALLS #############################################################
    
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
        x = self.candlestick_parser(req.json())
        print(x)
        return x

    def get_historical_data(self, symbol, interval, limit=None, start=None, end=None):
        # Define the size of the chunks of data we pull from the API
        limit = limit if limit else 1000
        # Define the interval of time represented by a chunk
        interval_ms = self.interval_to_ms(interval) * limit 
        # Define the start of where we want to start gathering data, if given
        start_epoch = self.date_to_ms(start) if start else None
        # Define end of first chunk, if given
        end_iter_epoch = start_epoch + interval_ms if start_epoch else None
        # Define where we want to finally stop gathering data, if given
        end_epoch = self.date_to_ms(end) if end else None
        # If only end is defined
        if not start_epoch and end_epoch:
            start_epoch = end_epoch - interval_ms
        # If only start is defined
        if start_epoch and not end_epoch:
            # Calculate closest candlestick based on interval
            end_epoch = interval_ms/limit
            end_iter_epoch = end_epoch
        # Dataframe that holds data as we iterate through the time series
        historical_data = None
        i = 0 # Counter
        while True:
            # Pause every 3rd loop to be easy on the API
            if i % 3 == 0:
                time.sleep(1)
            if start_epoch: # If we are iterating through a time series starting at some point in the past
                start_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_epoch))
                end_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_iter_epoch))
                print(f"{colors.OKBLUE}[INFO]: Gathering historical data from API, getting data for {start_time} -> {end_time} {colors.ENDC}")
                temp_data = self.get_candlestick(interval, symbol, limit, start_epoch, end_iter_epoch)
                if i == 0:
                    historical_data = temp_data
                else:
                    historical_data.append(temp_data)
            
                if end_iter_epoch == end_epoch:
                    break
                # Increment our steps through the time series
                end_iter_epoch += interval_ms
                start_epoch = temp_data['close_time'].values[-1] + 1
                i += 1
            else: # We want most recent dataset.
                timestamp = self.get_ms_timestamp()
                start_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp - interval_ms))
                end_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))
                print(f"{colors.OKBLUE}[INFO]: Gathering most recent data from API, getting data for {start_time} -> {end_time} {colors.ENDC}")
                temp_data = self.get_candlestick(interval, symbol, limit)
                historical_data = temp_data
                break
        return historical_data

        limit = limit if limit else 1000
        interval_ms = self.interval_to_ms(interval) * limit
        start_ms = self.date_to_ms(start) if start else None
        if start_ms:
            itr_end_ms = start_ms + interval_ms
        end_ms = self.date_to_ms(end) if end else None
        historical_data = None # Holds Dataframe of past candlesticks
        i = 0
        while True:
            # Pauses every 3rd loop, to be easy on the API.
            if i % 3 == 0:
                time.sleep(1)
            print(f"{colors.OKBLUE}[INFO]: Gathering historical data from API, getting data for {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_ms))}. {colors.ENDC}")
            temp_data = self.get_candlestick(interval, symbol, limit, start_ms, end_ms)
            if not temp_data.empty:
                if i == 0:
                    historical_data = temp_data
                else:
                    historical_data = historical_data.append(temp_data)
                # Check if we have reached the end date
                beginning_of_candlestick = temp_data['open_time'].values[0]
                end_of_candlestick = temp_data['open_time'].values[-1]
                # Our exit criteria - have we reached the latest?
                timestamp = int(self.get_ms_timestamp()) if not end_ms else end_ms
                end_timestamp = timestamp - interval_ms
                if timestamp <= end_of_candlestick:
                    break
                start_ms = temp_data['close_time'].values[-1] + 1
            # If symbol doesn't exist, slide to next interval.
            else:
                start_ms += interval_ms
            i += 1
        # If API returns duplicate rows, we remove them
        historical_data.drop_duplicates(inplace=True)
        if end_ms:
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

    def place_order(self, side, order_type, time_in_force=None, stopPrice=None):
        url = self.exchange + "api/v3/order/test"
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

    ################################# STRATEGY DEFINITIONS ##########################################

    def fomo_strategy(self, data, volume_threshold=None, price_threshold=None, ):
        ### PARAMETER NOTES #########################################################################
        # volume_threshold given as a percent change off the previous num_historical unit average   #
        # price_threshold given as a percent change off the previous num_historical unit average    #
        # num_historical number of candlesticks to use for moving average                           # 
        #############################################################################################
        if not volume_threshold:
            volume_threshold = 10
        if not price_threshold:
            price_threshold = 10
        # Get last row of dataframe, most up-to-date candlestick
        current_data = data[-1]
        # Get all but last row of dataframe, data upon which to build our strategy  
        historical_data = data[:-1]
        historical_vol_mean = historical_data["volume"].mean()
        historical_price_mean = data["close"].mean() # We've chosen to use the closing price, but this could change to be open, low, or a range between high/low
        percent_price_change = (historical_price_mean - current_data["close"])/historical_price_mean*100
        percent_volume_change = (historical_vol_mean - current_data["volume"])/historical_vol_mean*100
        if abs(percent_price_change) > price_threshold and abs(percent_volume_change) > volume_threshold:
            # Now we know the volume AND price are over our threshold - we want to FOMO in and ride the wave, up or down
            # Now that we know the amplitude of the move, we need to determine its direction
            if percent_price_change > 0:
                # Movement is in the positive direction - we need to buy.
                # TODO: Buy at current price.
                current_price = self.get_ticker()['price']
                self.place_order('BUY', )
            else:
                # Movement is in the negative direction - we need to sell.
                # TODO: Sell at current price.
                current_price = self.get_ticker()['price']
                self.place_order('SELL', )


    '''
    def std_dev_reversal_strategy(self, data) :

    def arbitrage_strategy(self, data):

    def mean_reversal_stratgey(self, data):

    def trend_follower_strategy(self, data):

    def fft_strategy(self, data):

    def sma_ema_strategy(self, data):

    def buy_and_hold_strategy(self, data):

    

    ### BACKTESTING ###
    def backtest(self, strategy, params, historical_data):
        
        for x in historical_data:

        results = strategy(params)
        #Plot results
    '''

if __name__ == "__main__":
    robot = RoboTrader(api_key, 'BTCUSDT')
    historical_data = robot.get_historical_data('BTCUSDT', '1m', limit=1000, start="March 13, 2020", end="May 10, 2020 7pm")
    #print(robot.get_ticker()['price'])
    robot.save_historical_data(historical_data)