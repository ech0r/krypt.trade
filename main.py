#!/usr/bin/python3

import requests
from secrets import * # Secrets file containing api key, etc.



if __name__ == "__main__":
    headers = {'X-MBX-APIKEY': api_key}
    xrp = {'symbol': 'XRPUSDT'}
    r = requests.get("https://api.binance.com/api/v3/historicalTrades", params=xrp, headers=headers)
    print(r.text)