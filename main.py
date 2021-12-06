
# -- --------------------------------------------------------------------------------------------------- -- #
# -- MarketMaker-BackTest                                                                                -- #
# -- --------------------------------------------------------------------------------------------------- -- #
# -- file: main.py                                                                                       -- #
# -- Description: Main execution logic for the project                                                   -- #
# -- --------------------------------------------------------------------------------------------------- -- #
# -- Author: IFFranciscoME - if.francisco.me@gmail.com                                                   -- #
# -- license: MIT License                                                                                -- #
# -- Repository: https://github.com/IFFranciscoME/MarketMaker-BackTest                                   -- #
# --------------------------------------------------------------------------------------------------------- #

# -- Load Packages for this script
import pandas as pd
import functions as fn
from data import fees_schedule, order_book
from timeit import default_timer as timer
import time

# -- Load other scripts
from data import fees_schedule, order_book

# Small test
exchanges = ["bitfinex", "kraken"]
symbol = 'BTC/USD'
expected_volume = 0

# Get fee schedule
# fees = fees_schedule(exchange='kraken', symbol=symbol, expected_volume=expected_volume)

# Massive download of OrderBook data
#data = order_book(symbol=symbol, exchanges=exchanges, output='JSON', stop=None,
#                  verbose=True, execution='ray', exec_time=120,jsonpath="files/orderbooks_ray.json")

# Test
# data['kraken'][list(data['kraken'].keys())[2]]

# Read previously downloaded file
ob_data = pd.read_json('files/orderbooks_ray.json', orient='values', typ='series')
#Describe OB data

E1_ts_data = [i for i in ob_data[exchanges[0]].keys() if ob_data[exchanges[0]][i] != None]
E2_ts_data = [i for i in ob_data[exchanges[1]].keys() if ob_data[exchanges[1]][i] != None]

q1_results = fn.f_timestamps_info(ts_list_o=E1_ts_data, ts_list_d=E2_ts_data)

display('Timestamps in Origin data:')
display('First Timestamp: ' + q1_results["first_o"])
display('Last Timestamp: ' + q1_results["last_o"])
display('Total number of orderbooks: ' + str(q1_results["qty_o"]))

display('Timestamps in Destination data:')
display('First Timestamp: ' + q1_results["first_d"])
display('Last Timestamp: ' + q1_results["last_d"])
display('Total number of orderbooks: ' + str(q1_results["qty_d"]))

display('Exact match of Timestamps: ' + str(q1_results["exact_match"]["qty"]))
if q1_results["exact_match"]["qty"] == 0:
    display("no exact matches")
else:
    display('First 2 values are: ')
    display(q1_results["exact_match"]["values"][0].strftime("%Y-%m-%dT%H:%M:%S.%fZ"))
    display(q1_results["exact_match"]["values"][1].strftime("%Y-%m-%dT%H:%M:%S.%fZ"))
    display('Last 2 values are: ')
    display(q1_results["exact_match"]["values"][-1].strftime("%Y-%m-%dT%H:%M:%S.%fZ"))
    display(q1_results["exact_match"]["values"][-2].strftime("%Y-%m-%dT%H:%M:%S.%fZ"))


# -- Simulation of trades (Pending)

"""
- Type A: Make a BID in Kraken, then Take BID in Bitfinex

Check Signal_BID
    Difference between BIDs on Origin and Destination is greater than Maker_Margin_BID
    Make on Destination and Take on Origin

kr_maker_bid * (1 + kr_maker_fee) = bf_taker_bid * (1 - bf_taker_fee)
e.g. -> 5942.5638 * (1 + 0.0016) = 5964.00 * (1 - 0.0020) = 0

- Type B: Take an ASK on Bitfinex, then Make an ASK in Kraken

Check Signal_ASK
    Difference between ASKs on Origin and Destination is greater than Maker_Margin_ASK
    Take on Origin and Maker on Destination

bf_taker_ask * (1 + bf_taker_fee) = kr_maker_ask * (1 - kr_maker_fee)
e.g. -> 6000 * (1 + 0.0020) - 6021.6346 * (1 - 0.0016) = 0
"""
