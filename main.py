#!/usr/bin/python3

import requests
import json
from secrets import * # Secrets file containing api key, etc.

class RoboTrader:
    
    def __init__(self, api_key, symbol):
        self.headers = {'X-MBX-APIKEY': api_key}
        self.exchange = "https://api.binance.com/"
        self.params = {'symbol': symbol}
    
    def get_historical_data(self):
        url = self.exchange + "api/v3/historicalTrades"
        req = requests.get(url, params=self.params, headers=self.headers)
        return req.json()
    
    def get_current_avg(self):
        url = self.exchange + "api/v3/avgPrice"
        req = requests.get(url, params=self.params, headers=self.headers)
        return req.json()
    

if __name__ == "__main__":
    xrp_robot = RoboTrader(api_key, 'XRPUSDT')
    #print(robot.get_historical_data())
    print(xrp_robot.get_current_avg())

