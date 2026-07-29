hard_off_map = {}

for a in AGENTS:
    a = str(a).strip()

    hard_days = set()

    hard_days |= izin_map.get(a, set())
    hard_days |= off_t2_map.get(a, set())

    if ENABLE_OFF_T_HARD:
        hard_days |= off_t_map.get(a, set())

    hard_off_map[a] = hard_days

#-----------------------------
# x karar değişkeni
# Hard izin/OFF günlerinde x oluşturulmaz.
# -----------------------------

x = {}

for a in AGENTS:
    a = str(a).strip()

    for ds in PLAN_GUNLER:
        ds_date = pd.to_datetime(ds).date()

        # Gerçek izin + off_t2 + hard ise off_t
        hard_off_gunleri = hard_off_map.get(a, set())

        if ds_date in hard_off_gunleri:
            continue

        for v in gun_vardiyalari.get(ds, []):
            x[(a, ds, v)] = model.NewBoolVar(
                f"x_{a}_{ds}_{v}"
            )
