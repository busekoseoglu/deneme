# %% [HÜCRE] - İZİN KONTROL HELPER

def agent_izinli_mi(a, ds):
    a = str(a).strip()
    izinler = izin_map.get(a, set())

    ds_str = pd.to_datetime(ds).strftime("%Y-%m-%d")
    ds_date = pd.to_datetime(ds).date()

    return (ds in izinler) or (ds_str in izinler) or (ds_date in izinler)
    
    
    