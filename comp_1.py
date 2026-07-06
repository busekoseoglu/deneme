# %% [HÜCRE] - İZİN KONTROL HELPER

def agent_izinli_mi(a, ds):
    a = str(a).strip()

    izinler = izin_map.get(a, set())

    # None / bool gelirse boş izin seti kabul et
    if izinler is None or isinstance(izinler, bool):
        izinler = set()

    # NaN gelirse boş izin seti kabul et
    elif isinstance(izinler, float) and pd.isna(izinler):
        izinler = set()

    # Tek tarih/string gelirse set'e çevir
    elif not isinstance(izinler, (set, list, tuple)):
        izinler = {izinler}

    ds_str = pd.to_datetime(ds).strftime("%Y-%m-%d")
    ds_date = pd.to_datetime(ds).date()

    return (ds in izinler) or (ds_str in izinler) or (ds_date in izinler)