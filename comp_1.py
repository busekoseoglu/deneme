def agent_hard_off_talepli_mi(a, ds):
    a = str(a).strip()
    ds_date = pd.to_datetime(ds).date()

    return ds_date in hard_off_talep_map.get(a, set())


def agent_soft_off_talepli_mi(a, ds):
    a = str(a).strip()
    ds_date = pd.to_datetime(ds).date()

    return soft_off_talep_map.get((a, ds_date), 0) == 1
