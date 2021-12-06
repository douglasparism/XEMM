import pandas as pd
import time
import warnings
warnings.filterwarnings("ignore")

def f_timestamps_info(ts_list_o, ts_list_d):
    ts_list_o_dt = [datetime.strptime(i, "%Y-%m-%dT%H:%M:%S.%fZ") for i in ts_list_o]
    ts_list_d_dt = [datetime.strptime(i, "%Y-%m-%dT%H:%M:%S.%fZ") for i in ts_list_d]
    f_compare_ts = {}
    f_compare_ts['first_o'] = min(ts_list_o_dt).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    f_compare_ts['last_o'] = max(ts_list_o_dt).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    f_compare_ts['qty_o'] = len(ts_list_o_dt)
    f_compare_ts['first_d'] = min(ts_list_d_dt).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    f_compare_ts['last_d'] = max(ts_list_d_dt).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    f_compare_ts['qty_d'] = len(ts_list_d_dt)
    unique_dates = list(dict.fromkeys(ts_list_o_dt + ts_list_d_dt))
    exact_matches = [i for i in unique_dates if (i in (ts_list_o_dt) and i in (ts_list_d_dt))]
    f_compare_ts['exact_match'] = {"qty": len(exact_matches), "values": exact_matches}
    return f_compare_ts


def dict_to_df(exchange, timestamp, orderbook):
    orderbooks_data = orderbook
    ask_size = orderbooks_data[exchange][timestamp]['ask_size'].values()
    ask = orderbooks_data[exchange][timestamp]['ask'].values()
    bid_size = orderbooks_data[exchange][timestamp]['bid_size'].values()
    bid = orderbooks_data[exchange][timestamp]['bid'].values()

    df_orderbook = pd.DataFrame(columns=['ask_size', 'ask', 'bid', 'bid_size', 'status'])
    df_orderbook['ask_size'] = ask_size
    df_orderbook['ask'] = ask
    df_orderbook['bid'] = bid
    df_orderbook['bid_size'] = bid_size
    df_orderbook['status'] = exchange
    return df_orderbook

def f_del_none_dict(dictionary_to_clean):
    dict_c = dictionary_to_clean
    clean_ob_data = {k: v for k, v in dict_c.items() if v is not None}
    display(
    'Number of historical orderbooks:',
    ('Before dropping Nones: '+ str(len(dict_c))),
    ('After dropping Nones: ' + str(len(clean_ob_data))))
    return clean_ob_data


def post_maker_bid(origin_bid, volume, taker_fee, maker_fee, inventory, tokens, ex_D_final, decimals, profit, lat):
    destination_bid = calc_D_bid(origin_bid, taker_fee, maker_fee, decimals,
                                 profit)  # obtenemos el precio de equilibrio

    if (inventory['asset'] - volume).values[0] >= 0:

        inventory.update(
            {'asset': (inventory['asset'] - volume).values[0]})  # reservamos el volumen a entregar en caso de ejecucion
        tokens.update(
            {'asset': (tokens['asset'] + volume).values[0]})  # reservamos el volumen a entregar en caso de ejecucion
        ex_D_final.loc[-1] = [volume.values[0], destination_bid.values[0], "bid"]  # posteamos la orden
        print('Order posted')
        print(ex_D_final.loc[-1])
        ex_D_final = ex_D_final.sort_values('price')  # ordenamos el libro
        ex_D_final.reset_index(inplace=True, drop=True)  # reseteamos el índice
        time.sleep(lat)
    else:
        print('Not enough Assets in inventory')
    return ex_D_final, inventory, tokens


def post_maker_ask(origin_ask, volume, taker_fee, maker_fee, inventory, tokens, ex_D_final, decimals, profit, lat):
    destination_ask = calc_D_ask(origin_ask, taker_fee, maker_fee, decimals,
                                 profit)  # obtenemos el precio de equilibrio

    if (inventory['fiat'] - destination_ask * volume).values[0] >= 0:

        inventory.update({'fiat': (inventory['fiat'] - destination_ask * volume).values[
            0]})  # reservamos el volumen a entregar en caso de ejecucion
        tokens.update({'fiat': (tokens['fiat'] + destination_ask * volume).values[
            0]})  # reservamos el volumen a entregar en caso de ejecucion
        ex_D_final.loc[-1] = [volume.values[0], destination_ask.values[0], "ask"]  # posteamos la orden
        print('Order posted')
        print(ex_D_final.loc[-1])
        ex_D_final = ex_D_final.sort_values('price')  # ordenamos el libro
        ex_D_final.reset_index(inplace=True, drop=True)  # reseteamos el índice
        time.sleep(lat)

    else:
        print('Not enough Fiat in inventory')

    return ex_D_final, inventory, tokens

def calc_D_bid(origin_bid, taker_fee, maker_fee, decimals, profit):
    b = origin_bid*(1-taker_fee)/(1+maker_fee) - profit
    return round(b,decimals)

def calc_D_ask(origin_ask, taker_fee, maker_fee, decimals, profit):
    a = origin_ask*(1+taker_fee)/(1-maker_fee) + profit
    return round(a,decimals)


def execute_bids(origin_bid, destination_bid, taker_fee, maker_fee, volume, inventory, tokens, ex_D_final, ex_O_final,
                 lat):
    # ejecutamos el origin bid
    idx = ex_O_final[(ex_O_final['Type'] == 'bid') & (ex_O_final['price'] == origin_bid)].index[
        0]  # obtenemos la orden orig
    ex_O_final.loc[idx, 'size'] = ex_O_final.loc[idx, 'size'] - volume  # actualizamos el size

    tokens.update(
        {'fiat': tokens['fiat'] + volume * origin_bid * (1 - taker_fee)})  # Recibimos el bid menos la comision
    tokens.update({'asset': tokens['asset'] - volume})  # entregamos el activo

    # nos ejecutan el destination bid
    idx = ex_D_final[(ex_O_final['Type'] == 'bid') & (ex_D_final['price'] == destination_bid)].index[
        0]  # obtenemos la orden dest
    ex_D_final.loc[idx, 'size'] = ex_D_final.loc[idx, 'size'] - volume  # actualizamos el size

    inventory.update({'asset': inventory['asset'] + volume})  # obtenemos el activo
    tokens.update(
        {'fiat': tokens['fiat'] - volume * destination_bid * (1 + maker_fee)})  # pagamos el bid más la comisión
    time.sleep(lat)
    return inventory, tokens, ex_D_final, ex_O_final


def execute_asks(origin_ask, destination_ask, taker_fee, maker_fee, volume, inventory, tokens, ex_D_final, ex_O_final,
                 lat):
    # ejecutamos el origin ask
    idx = ex_O_final[(ex_O_final['Type'] == 'ask') & (ex_O_final['price'] == origin_ask)].index[
        0]  # obtenemos la orden orig
    ex_O_final.loc[idx, 'size'] = ex_O_final.loc[idx, 'size'] - volume  # actualizamos el size

    tokens.update({'asset': tokens['asset'] + volume})  # obtenemos el activo
    tokens.update({'fiat': tokens['fiat'] - volume * origin_ask * (1 + taker_fee)})  # pagamos el ask más la comisión

    # nos ejecutan el destination bid
    idx = ex_D_final[(ex_D_final['Type'] == 'ask') & (ex_D_final['price'] == destination_ask)].index[
        0]  # obtenemos la orden dest
    ex_D_final.loc[idx, 'size'] = ex_D_final.loc[idx, 'size'] - volume  # actualizamos el size

    inventory.update(
        {'fiat': inventory['fiat'] + volume * destination_ask * (1 - maker_fee)})  # Recibimos el ask menos la comision
    tokens.update({'asset': tokens['asset'] - volume})  # entregamos el activo
    time.sleep(lat)
    return inventory, tokens, ex_D_final, ex_O_final


def flatten_D(ex_D):
    ex_D_ask = ex_D.loc[:, 'ask_size':'ask'].copy()
    ex_D_ask.columns = ['size', 'price']
    ex_D_ask['Type'] = 'ask'
    ex_D_bid = ex_D[['bid_size', 'bid']].copy()
    ex_D_bid.columns = ['size', 'price']
    ex_D_bid['Type'] = 'bid'
    ex_D_final = pd.concat([ex_D_ask, ex_D_bid]).sort_values('price')
    ex_D_final.reset_index(inplace=True, drop=True)
    return ex_D_final


def flatten_O(ex_O, spread):
    Mid_price_origin = round((min(ex_O.ask) + max(ex_O.bid)) / 2, 6)
    PLimit_Repl_max = Mid_price_origin * (1 + spread / 10000)
    PLimit_Repl_min = Mid_price_origin * (1 - spread / 10000)

    ex_O_ask = ex_O[ex_O.ask <= PLimit_Repl_max].loc[:, 'ask_size':'ask'].copy()  # limitamos por los bps a replicar
    ex_O_ask.columns = ['size', 'price']
    ex_O_ask = ex_O_ask[~ex_O_ask.price.isin([ex_O_ask.price])]  # no copiaremos los precios donde ya hay volumen
    ex_O_ask['Type'] = 'ask'
    ex_O_bid = ex_O[ex_O.bid >= PLimit_Repl_min][['bid_size', 'bid']].copy()  # limitamos por los bps a replicar
    ex_O_bid.columns = ['size', 'price']
    ex_O_bid = ex_O_bid[~ex_O_bid.price.isin([ex_O_bid.price])]  # no copiaremos los precios donde ya hay volumen
    ex_O_bid['Type'] = 'bid'
    ex_O_final = pd.concat([ex_O_ask, ex_O_bid]).sort_values('price')
    ex_O_final.reset_index(inplace=True, drop=True)
    return ex_O_final

