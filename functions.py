from datetime import timedelta, datetime

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