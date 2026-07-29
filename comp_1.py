daily_one_shift_constraints = 0

for a in AGENTS:
    a = str(a).strip()

    for ds in PLAN_GUNLER:

        vars_day = [
            x[(a, ds, v)]
            for v in gun_vardiyalari.get(ds, [])
            if (a, ds, v) in x
        ]

        if vars_day:
            model.Add(sum(vars_day) == work[(a, ds)])
        else:
            model.Add(work[(a, ds)] == 0)

        daily_one_shift_constraints += 1

print(
    f"Günde max 1 vardiya/work kısıtı: "
    f"{daily_one_shift_constraints} agent-gün"
)


# Hard OFF günlerinde yanlışlıkla x oluşturulmuş mu?

hard_off_x_hatalari = []

for a in AGENTS:
    a = str(a).strip()

    for ds in PLAN_GUNLER:
        ds_date = pd.to_datetime(ds).date()

        if ds_date not in hard_off_map.get(a, set()):
            continue

        bulunan_x = [
            v
            for v in gun_vardiyalari.get(ds, [])
            if (a, ds, v) in x
        ]

        if bulunan_x:
            hard_off_x_hatalari.append({
                "agent_user_code": a,
                "tarih": ds_date,
                "x_olusan_vardiyalar": bulunan_x
            })

hard_off_x_hata_df = pd.DataFrame(hard_off_x_hatalari)

print("Hard OFF gününde x oluşturulan kayıt:", len(hard_off_x_hata_df))
display(hard_off_x_hata_df.head(20))




# %% [HAZIRLIK] - İZİN / OFF_T2 / OFF_T MAP'LERİ

izin_map = {}
off_t2_map = {}
off_t_map = {}

for _, row in df_izin_off_model.iterrows():

    code = str(row["agent_user_code"]).strip()
    tarih = pd.to_datetime(row["tarih"]).date()
    izin_tipi = str(row["izin_tipi"]).strip().lower()

    if izin_tipi == "izin":
        izin_map.setdefault(code, set()).add(tarih)

    elif izin_tipi == "off_t2":
        off_t2_map.setdefault(code, set()).add(tarih)

    elif izin_tipi == "off_t":
        off_t_map.setdefault(code, set()).add(tarih)



# %% [HAZIRLIK] - HARD OFF MAP

hard_off_map = {}

for a in AGENTS:

    a = str(a).strip()

    hard_days = set()

    hard_days |= izin_map.get(a, set())
    hard_days |= off_t2_map.get(a, set())

    if ENABLE_OFF_T_HARD:
        hard_days |= off_t_map.get(a, set())

    hard_off_map[a] = hard_days
