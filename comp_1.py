# %% [HAZIRLIK] - İZİN / HARD OFF / SOFT OFF MAP'LERİ

off_map = {}
off_talep_map = {}

for _, row in df_izin_off_model.iterrows():

    code = str(row["agent_user_code"]).strip()
    tarih = pd.to_datetime(row["tarih"]).date()
    izin_tipi = str(row["izin_tipi"]).strip().lower()

    # Yıllık izin: her zaman hard
    if izin_tipi == "izin":
        off_map.setdefault(code, set()).add(tarih)

    # off_t2: config açıkken hard
    elif izin_tipi == "off_t2":

        if ENABLE_OFF_T2_HARD:
            off_map.setdefault(code, set()).add(tarih)
        else:
            off_talep_map[(code, tarih)] = 1

    # off_t: config'e göre hard veya soft
    elif izin_tipi == "off_t":

        if ENABLE_OFF_T_HARD:
            off_map.setdefault(code, set()).add(tarih)
        else:
            off_talep_map[(code, tarih)] = 1
