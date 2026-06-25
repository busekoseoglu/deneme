# %% [HÜCRE 14] - HAMİLE VE SÜT İZNİ HAFTA SONU ÇALIŞAMAZ

special_weekend_constraints = 0

for _, row in df_tam.iterrows():
    a = str(row["agent_user_code"]).strip()

    weekend_off = (
        int(row.get("hamile_flg", 0) or 0) == 1
        or int(row.get("sut_izni_flg", 0) or 0) == 1
    )

    if not weekend_off:
        continue

    for ds in PLAN_GUNLER:
        d = pd.to_datetime(ds).date()

        # Cumartesi = 5, Pazar = 6
        if d.weekday() not in [5, 6]:
            continue

        for v in gun_vardiyalari.get(ds, []):
            if (a, ds, v) in x:
                model.Add(x[(a, ds, v)] == 0)
                special_weekend_constraints += 1

print(f"hamile/süt izni hafta sonu çalışamaz kısıtı: {special_weekend_constraints} adet")
