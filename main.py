#!/usr/bin/python3

import requests
import json
import hmac
import hashlib
from datetime import datetime, timezone
from secrets import * # Secrets file containing api key, etc.

class RoboTrader:
    
    def __init__(self, api_key, symbol):
        self.headers = {'X-MBX-APIKEY': api_key}
        self.exchange = "https://api.binance.com/"
        self.params = {'symbol': symbol}

    def stringify_params(self, params):
        param_string = ""
        for i,x in enumerate(params.keys()):
            each_param = x + "=" + params[x]
            if i > 0:
                each_param = "&" + each_param
            param_string += each_param
        return param_string

    def generate_signature(self, params, key):
        encoded_params = str.encode(self.stringify_params(params))
        encoded_key = str.encode(secret_key)
        sig = hmac.new(encoded_key, encoded_params, hashlib.sha256)
        return sig.hexdigest()    

    def get_ms_timestamp(self):
        timestamp = datetime.now(timezone.utc).timestamp() * 1000
        return str(int(timestamp))

    def get_historical_data(self):
        url = self.exchange + "api/v3/historicalTrades"
        req = requests.get(url, params=self.params, headers=self.headers)
        return req.json()
    
    def get_current_avg(self):
        url = self.exchange + "api/v3/avgPrice"
        req = requests.get(url, params=self.params, headers=self.headers)
        return req.json()

    def get_all_orders(self):
        url = self.exchange + "api/v3/allOrders"
        params = self.params
        params['timestamp'] = self.get_ms_timestamp()
        params['recvWindow'] = '5000'
        params['signature'] = self.generate_signature(self.params, secret_key)
        req = requests.get(url, params=params, headers=self.headers)
        return req.json()

if __name__ == "__main__":
    robot = RoboTrader(api_key, 'BTCUSDT')
    #print(robot.get_historical_data())
    #print(robot.get_current_avg())
    print(robot.get_all_orders())

