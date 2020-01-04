#!/usr/bin/python3

import requests
import json
from secrets import * # Secrets file containing api key, etc.

class RoboTrader:
    
    def __init__(self, api_key):
        self.headers = {'X-MBX-APIKEY': api_key}
        self.exchange = "https://api.binance.com/"
    
    def get_historical_data(self, symbol):
        url = self.exchange + "api/v3/historicalTrades"
        params = {'symbol': symbol}
        req = requests.get(url, params=params, headers=self.headers)
        return req.json()
    


if __name__ == "__main__":
    robot = RoboTrader(api_key)
    print(robot.get_historical_data('XRPUSDT'))
