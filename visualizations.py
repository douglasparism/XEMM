
# -- --------------------------------------------------------------------------------------------------- -- #
# -- MarketMaker-BackTest                                                                                -- #
# -- --------------------------------------------------------------------------------------------------- -- #
# -- file: visualizations.py                                                                             -- #
# -- Description: Functions for plots, tables and text visualizations for the project                    -- #
# -- --------------------------------------------------------------------------------------------------- -- #
# -- Author: IFFranciscoME - if.francisco.me@gmail.com                                                   -- #
# -- license: MIT License                                                                                -- #
# -- Repository: https://github.com/IFFranciscoME/MarketMaker-BackTest                                   -- #
# --------------------------------------------------------------------------------------------------------- #

# -- Load base packages
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import warnings
warnings.filterwarnings("ignore")

def plot_orderbook_2excahnges(ob_data_plot_origin, ob_data_plot_destionation):
    ob_data = ob_data_plot_origin
    ob_data_bid = ob_data[['bid_size', 'bid']]
    ob_data_bid = ob_data_bid.sort_values(ascending=True, by='bid')
    ob_data_ask = ob_data[['ask_size', 'ask']]
    ob_data_ask = ob_data_ask
    fig = go.Figure()
    fig.add_trace(
        go.Bar(x=ob_data_bid['bid'],
               y=ob_data_bid['bid_size'], name='Bid-Origin', width=.7, opacity=0.5, marker_color='red',
               text=ob_data['status']))

    fig.add_trace(
        go.Bar(x=ob_data_ask['ask'],
               y=ob_data_ask['ask_size'], name='Ask-Origin', width=.7, opacity=0.5, marker_color='blue',
               text=ob_data['status']))

    ob_data = ob_data_plot_destionation
    ob_data_bid = ob_data[['bid_size', 'bid']]
    ob_data_bid = ob_data_bid.sort_values(ascending=True, by='bid')
    ob_data_ask = ob_data[['ask_size', 'ask']]
    ob_data_ask = ob_data_ask

    fig.add_trace(
        go.Bar(x=ob_data_bid['bid'],
               y=ob_data_bid['bid_size'], name='Bid-Destination', width=.7, opacity=0.5, marker_color='yellow',
               text=ob_data['status']))

    fig.add_trace(
        go.Bar(x=ob_data_ask['ask'],
               y=ob_data_ask['ask_size'], name='Ask-Destination', width=.7, opacity=0.5, marker_color='green',
               text=ob_data['status']))

    # fig.update_xaxes(type='category')

    fig.update_traces(marker_line_color='rgb(8,48,107)',
                      marker_line_width=.6)

    fig.update_layout(
        width=950,
        height=650)
    # Update yaxis properties
    fig.update_yaxes(title_text="Size")
    fig.update_xaxes(title_text="Price")
    fig.show()