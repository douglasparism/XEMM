import pandas as pd
import numpy as np
import warnings
from data import fees_schedule, order_book
from timeit import default_timer as timer
import time
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

def test_XEMM():

    ob_data = pd.read_json('files/orderbooks_ray.json', orient='values', typ='series')
    exchanges = ["kraken", "bitfinex"]
    symbol = 'BTC/EUR'
    expected_volume = 0
    fees = [fees_schedule(exchange=i, symbol=symbol, expected_volume=expected_volume) for i in exchanges]
    clean_order_kraken = f_del_none_dict(ob_data['kraken'])

    clean_order_bitfinex = f_del_none_dict(ob_data['bitfinex'])

    df_datetime = pd.DataFrame(columns=['dict_key', 'timestamp', 'exchange'])
    df_datetime['dict_key'] = clean_order_kraken.keys()
    df_datetime['timestamp'] = clean_order_kraken.keys()
    df_datetime['exchange'] = 'kraken'

    df_datetime_aux = pd.DataFrame(columns=['dict_key', 'timestamp', 'exchange'])
    df_datetime_aux['dict_key'] = clean_order_bitfinex.keys()
    df_datetime_aux['timestamp'] = clean_order_bitfinex.keys()
    df_datetime_aux['exchange'] = 'bitfinex'

    df_datetime = df_datetime.append(df_datetime_aux)
    df_datetime['timestamp'] = pd.to_datetime(df_datetime['timestamp'])
    df_datetime = df_datetime.sort_values(by=['timestamp'])
    df_datetime = df_datetime.reset_index(drop=True)



    pd.set_option("display.max_rows", None, "display.max_columns", None)
    current_kraken = ''
    current_bitfinex = ''
    test = [1, 1, 1, 1]  # for testing
    lat = 0.01
    k = 0
    b = 0
    order_pairs = pd.DataFrame(columns=['size', 'price', 'type', 'source', 'id'])
    for i in range(len(test)):
        if df_datetime['exchange'][i] == 'kraken' and k == 0:
            k = 1
            current_kraken = df_datetime['dict_key'][i]

        if df_datetime['exchange'][i] == 'bitfinex':
            b = 1
            current_bitfinex = df_datetime['dict_key'][i]
            current_bitfinex_time = df_datetime['timestamp'][i]

        if k == 1 and b == 1:
            print('Al momento')
            print(current_bitfinex, 'bitfinex')
            print(current_kraken, 'kraken')

            k = 0
            b = 0

            bit_time = df_datetime[df_datetime['exchange'] == 'bitfinex']
            future = bit_time[bit_time['timestamp'] > current_bitfinex_time].reset_index(drop=True)
            future_bitfinex_time = future.loc[0]['timestamp']
            tdelta = (future_bitfinex_time - current_bitfinex_time).total_seconds()

            print('TIEMPO MAS CERCANO FUTURO BITFINEX', future_bitfinex_time)

            # Sacar los OB
            ex_O = dict_to_df('kraken', current_kraken, ob_data)
            ex_D = dict_to_df('bitfinex', current_bitfinex, ob_data)

            ex_D_final = flatten_D(ex_D)
            ex_O_final = flatten_O(ex_O, spread=25)

            # print('Destination inicial',ex_D_final)
            # print('Origin inicial',ex_O_final)

            display('Highest Bid Prices')
            display('Destination: ' + exchanges[1] + ' ' + str(max(ex_D.bid)))
            display('Origin: ' + exchanges[0] + ' ' + str(max(ex_O.bid)))

            display('Lowest Ask Prices')
            display('Destination: ' + exchanges[1] + ' ' + str(min(ex_D.ask)))
            display('Origin: ' + exchanges[0] + ' ' + str(min(ex_O.ask)))

            bid_example = ex_O_final[ex_O_final['Type'] == 'bid']
            bid_example = bid_example[bid_example['price'] == bid_example['price'].max()]
            init_bid = bid_example.index.values[0]

            ask_example = ex_O_final[ex_O_final['Type'] == 'ask']
            ask_example = ask_example[ask_example['price'] == ask_example['price'].min()]
            init_ask = ask_example.index.values[0]

            display(bid_example)
            display(ask_example)

            taker_fee = fees[0]['taker'] * 0.0001  # bps to decimal
            maker_fee = fees[1]['maker'] * 0.0001  # bps to decimal
            token = 100  # BTC
            fiat = 1000000  # EUR
            inventory = {'asset': 100, 'fiat': 1000000}
            tokens = {'asset': 0, 'fiat': 0}
            profit = 0.01  # 1 centavo de profit por trade
            decimals = 10
            print(tdelta)
            time_i = timer()

            order_historical = pd.DataFrame(columns=['size', 'price', 'type', 'source', 'status', 'time_delta'])

            for t in range(len(ex_O_final)):

                to_ex = order_historical[(order_historical['time_delta'] <= timer() - time_i) & (
                            order_historical['time_delta'] > 0)].reset_index()

                display(to_ex)

                for j in range(len(to_ex)):
                    if len(to_ex) >= 1:

                        if to_ex.loc[j]['type'] == 'bid':
                            id_orden = order_pairs[order_pairs['price'] == to_ex.loc[j]['price']]['id'].values[0]

                            # print(order_pairs[order_pairs['id'] == id_orden])
                            origin_price = order_pairs[order_pairs['id'] == id_orden]
                            origin_price = origin_price[origin_price['source'] == 'orig']
                            origin_price = origin_price[origin_price['type'] == 'bid']['price'].values[0]
                            # print('El precio de origen es:', origin_price)
                            # EJECUTAR BIDS
                            inventory, tokens, ex_D_final_2, ex_O_final_2 = execute_bids(origin_price,
                                                                                            to_ex.loc[j]['price'],
                                                                                            taker_fee, maker_fee,
                                                                                            to_ex.loc[j]['size'], inventory,
                                                                                            tokens, ex_D_final_2,
                                                                                            ex_O_final_2, lat)
                            ex_D_final = ex_D_final_2
                            ex_O_final = ex_O_final_2
                            order_historical.loc[len(order_historical)] = [to_ex.loc[j]['size'], to_ex.loc[j]['price'],
                                                                           'bid', 'destination', 'executed', 0]
                            order_historical.loc[len(order_historical)] = [to_ex.loc[j]['size'], origin_price, 'bid',
                                                                           'origin', 'executed', 0]

                            destination_bid = order_pairs[order_pairs['id'] == id_orden]
                            destination_bid = destination_bid[destination_bid['source'] == 'des']
                            destination_bid = destination_bid[destination_bid['type'] == 'bid']['price'].values[0]

                            index_ex = order_historical[(order_historical['price'] == destination_bid) & (
                                        order_historical['status'] == 'posted')].index[0]
                            order_historical.iloc[index_ex, 5] = 0

                        else:

                            id_orden = order_pairs[order_pairs['price'] == to_ex.loc[j]['price']]['id'].values[0]
                            # print(order_pairs[order_pairs['id'] == id_orden])
                            origin_price = order_pairs[order_pairs['id'] == id_orden]
                            origin_price = origin_price[origin_price['source'] == 'orig']
                            origin_price = origin_price[origin_price['type'] == 'ask']['price'].values[0]
                            # print('El precio de origen es:', origin_price)
                            # EJECUTAR ASK
                            inventory, tokens, ex_D_final_2, ex_O_final_2 = execute_asks(origin_price,
                                                                                            to_ex.loc[j]['price'],
                                                                                            taker_fee,
                                                                                            maker_fee, to_ex.loc[j]['size'],
                                                                                            inventory, tokens, ex_D_final_2,
                                                                                            ex_O_final_2, lat)

                            ex_D_final = ex_D_final_2
                            ex_O_final = ex_O_final_2

                            order_historical.loc[len(order_historical)] = [to_ex.loc[j]['size'], to_ex.loc[j]['price'],
                                                                           'ask', 'destination', 'executed', 0]
                            order_historical.loc[len(order_historical)] = [to_ex.loc[j]['size'], origin_price, 'ask',
                                                                           'origin', 'executed', 0]

                            destination_ask = order_pairs[order_pairs['id'] == id_orden]
                            destination_ask = destination_ask[destination_ask['source'] == 'des']
                            destination_ask = destination_ask[destination_ask['type'] == 'ask']['price'].values[0]

                            index_ex = order_historical[(order_historical['price'] == destination_ask) & (
                                        order_historical['status'] == 'posted')].index[0]
                            order_historical.iloc[index_ex, 5] = 0

                if (time_i + tdelta) < timer():
                    # print(time_i + tdelta)
                    # print(timer())
                    break

                if init_bid >= 0:

                    bid_example = ex_O_final[ex_O_final['Type'] == 'bid']
                    bid_example = bid_example[bid_example['price'] == bid_example['price'][init_bid]]

                    ask_example = ex_O_final[ex_O_final['Type'] == 'ask']
                    ask_example = ask_example[ask_example['price'] == ask_example['price'][init_ask]]

                    init_bid = init_bid - 1
                    init_ask = init_ask + 1

                    print('bid id', init_bid)

                    ex_D_final, inventory, tokens = post_maker_bid(bid_example['price'], bid_example['size'], taker_fee,
                                                                      maker_fee,
                                                                      inventory, tokens, ex_D_final, decimals, profit, lat)

                    ex_D_final, inventory, tokens = post_maker_ask(ask_example['price'], ask_example['size'], taker_fee,
                                                                      maker_fee,
                                                                      inventory, tokens, ex_D_final, decimals, profit, lat)

                    print(inventory, tokens)

                    ex_D_final_2 = ex_D_final.copy()
                    ex_O_final_2 = ex_O_final.copy()

                    destination_bid = calc_D_bid(float(bid_example['price']), taker_fee, maker_fee, decimals,
                                                    profit)  # calculamos los precios posteados
                    destination_ask = calc_D_ask(float(ask_example['price']), taker_fee, maker_fee, decimals,
                                                    profit)  # calculamos los precios posteados

                    idf = len(order_pairs)

                    order_pairs.loc[len(order_pairs)] = [bid_example['size'].values[0], bid_example['price'].values[0],
                                                         'bid', 'orig', idf]
                    order_pairs.loc[len(order_pairs)] = [bid_example['size'].values[0], destination_bid, 'bid', 'des', idf]

                    order_pairs.loc[len(order_pairs)] = [ask_example['size'].values[0], ask_example['price'].values[0],
                                                         'ask', 'orig', idf]
                    order_pairs.loc[len(order_pairs)] = [ask_example['size'].values[0], destination_ask, 'ask', 'des', idf]

                    if not ex_D_final[(ex_D_final['price'] == destination_bid) & (ex_D_final['Type'] == 'bid')].empty:
                        random_time_ex = np.random.uniform(min(timer() - time_i, tdelta), tdelta)

                        order_historical.loc[len(order_historical)] = [bid_example['size'].values[0], destination_bid,
                                                                       'bid', 'destination', 'posted', random_time_ex]

                    if not ex_D_final[(ex_D_final['price'] == destination_ask) & (ex_D_final['Type'] == 'ask')].empty:
                        random_time_ex = np.random.uniform(min(timer() - time_i, tdelta), tdelta)
                        order_historical.loc[len(order_historical)] = [ask_example['size'].values[0], destination_ask,
                                                                       'ask', 'destination', 'posted', random_time_ex]

                    print('Destination BID', destination_bid)
                    print('Destination ASK', destination_ask)

                    # Se ejecutan??? CASO BID

                    best_ask = ex_D_final_2[ex_D_final_2['Type'] == 'ask']
                    best_ask = best_ask[best_ask['price'] == best_ask['price'].min()]
                    # print('Best ASK colocation',best_ask['price'].values[0])

                    if destination_bid > best_ask['price'].values[0]:
                        print('Se ejecuta BID')
                        # ejecutamos los bids
                        inventory, tokens, ex_D_final_2, ex_O_final_2 = execute_bids(float(bid_example['price']),
                                                                                        destination_bid, taker_fee,
                                                                                        maker_fee,
                                                                                        float(bid_example['size']),
                                                                                        inventory, tokens, ex_D_final_2,
                                                                                        ex_O_final_2, lat)
                        ex_D_final = ex_D_final_2
                        ex_O_final = ex_O_final_2
                        order_historical.loc[len(order_historical)] = [bid_example['size'].values[0], destination_bid,
                                                                       'bid', 'destination', 'executed', 0]
                        order_historical.loc[len(order_historical)] = [bid_example['size'].values[0],
                                                                       float(bid_example['price']), 'bid', 'origin',
                                                                       'executed', 0]

                        index_ex = order_historical[(order_historical['price'] == destination_bid) & (
                                    order_historical['status'] == 'posted')].index[0]
                        order_historical.iloc[index_ex, 5] = 0

                    # Se ejecutan??? CASO BID
                    best_bid = ex_D_final_2[ex_D_final_2['Type'] == 'bid']
                    best_bid = best_bid[best_bid['price'] == best_bid['price'].max()]
                    # print('Best BID colocation',best_bid['price'].values[0])

                    if destination_ask < best_bid['price'].values[0]:
                        print('Se ejecuta ASK')
                        # ejecutamos los asks
                        inventory, tokens, ex_D_final_2, ex_O_final_2 = execute_asks(float(ask_example['price']),
                                                                                        destination_ask, taker_fee,
                                                                                        maker_fee,
                                                                                        float(ask_example['size']),
                                                                                        inventory, tokens, ex_D_final_2,
                                                                                        ex_O_final_2, lat)

                        ex_D_final = ex_D_final_2
                        ex_O_final = ex_O_final_2

                        order_historical.loc[len(order_historical)] = [ask_example['size'].values[0], destination_ask,
                                                                       'ask', 'destination', 'executed', 0]
                        order_historical.loc[len(order_historical)] = [ask_example['size'].values[0],
                                                                       float(ask_example['price']), 'ask', 'origin',
                                                                       'executed', 0]

                        index_ex = order_historical[(order_historical['price'] == destination_ask) & (
                                    order_historical['status'] == 'posted')].index[0]
                        order_historical.iloc[index_ex, 5] = 0

                    # print(inventory['fiat']+tokens['fiat'])

                    # print('Destination final',ex_D_final)
                    # print('Origin final',ex_O_final)
            display(order_historical)
            print(inventory, tokens)
            print('TIMEDELTA', tdelta)

        else:
            pass

