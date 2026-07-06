# %% [HÜCRE] - İZİN KONTROL HELPER - SAĞLAM VERSİYON

def agent_izinli_mi(a, ds):
    a = str(a).strip()

    izinler = izin_map.get(a, set())

    # Bool, None, NaN gibi şeyler izin listesi değildir.
    if izinler is None:
        return False

    if isinstance(izinler, bool):
        return False

    if isinstance(izinler, float) and pd.isna(izinler):
        return False

    # Set/list/tuple değilse tek elemanlı sete çevir.
    if isinstance(izinler, set):
        izin_set = izinler
    elif isinstance(izinler, list):
        izin_set = set(izinler)
    elif isinstance(izinler, tuple):
        izin_set = set(izinler)
    else:
        izin_set = {izinler}

    ds_str = pd.to_datetime(ds).strftime("%Y-%m-%d")
    ds_date = pd.to_datetime(ds).date()

    return (
        ds in izin_set
        or ds_str in izin_set
        or ds_date in izin_set
    )
    
    
    
# %% TEST - İZİN HELPER ÇALIŞIYOR MU?

test_count = 0

for a in AGENTS[:20]:
    for ds in PLAN_GUNLER[:5]:
        sonuc = agent_izinli_mi(a, ds)
        test_count += 1

print("Test edilen agent-gün:", test_count)
print("Helper çalıştı.")