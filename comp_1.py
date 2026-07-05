# %% DEBUG - RESMİ TATİLDE HARD X==0 SABİTLEME VAR MI?

# Bu hücre solve'dan hemen önce çalışmalı.
# Amaç: modelin içine resmi tatil günü için x[(a, ds, v)] == 0 hard kısıtı eklenmiş mi görmek.

resmi_tatil_debug_days = set()

if "resmi_tatil_plan_gunleri" in globals():
    resmi_tatil_debug_days = set(resmi_tatil_plan_gunleri)
else:
    if "RESMI_TATIL_GUNLERI" in globals():
        resmi_tatil_key_set = set(RESMI_TATIL_GUNLERI)

        for ds in PLAN_GUNLER:
            if pd.to_datetime(ds).strftime("%Y-%m-%d") in resmi_tatil_key_set:
                resmi_tatil_debug_days.add(ds)

print("Resmi tatil debug günleri:", resmi_tatil_debug_days)


# x variable index -> key map
x_index_to_key = {}

for key, var in x.items():
    x_index_to_key[var.Index()] = key


# work variable index -> key map
work_index_to_key = {}

for key, var in work.items():
    work_index_to_key[var.Index()] = key


hard_zero_x_rows = []
hard_zero_work_rows = []

proto = model.Proto()

for c_idx, ct in enumerate(proto.constraints):

    if not ct.HasField("linear"):
        continue

    lin = ct.linear

    # Sadece tek değişkenli x == 0 / work == 0 kısıtlarını yakalıyoruz.
    # model.Add(x == 0) genelde:
    # vars = [x_index], coeffs = [1], domain = [0, 0]
    if len(lin.vars) == 1 and len(lin.coeffs) == 1:
        var_idx = lin.vars[0]
        coeff = lin.coeffs[0]
        domain = list(lin.domain)

        if coeff == 1 and domain == [0, 0]:

            if var_idx in x_index_to_key:
                a, ds, v = x_index_to_key[var_idx]

                if ds in resmi_tatil_debug_days:
                    bas, bit = saat[(ds, v)] if (ds, v) in saat else (None, None)

                    hard_zero_x_rows.append({
                        "constraint_index": c_idx,
                        "agent_user_code": a,
                        "date": ds,
                        "shift": v,
                        "shift_start": bas,
                        "shift_end": bit,
                    })

            if var_idx in work_index_to_key:
                a, ds = work_index_to_key[var_idx]

                if ds in resmi_tatil_debug_days:
                    hard_zero_work_rows.append({
                        "constraint_index": c_idx,
                        "agent_user_code": a,
                        "date": ds,
                    })


hard_zero_x_df = pd.DataFrame(hard_zero_x_rows)
hard_zero_work_df = pd.DataFrame(hard_zero_work_rows)

print("Resmi tatil günü hard x==0 sayısı:", len(hard_zero_x_df))
print("Resmi tatil günü hard work==0 sayısı:", len(hard_zero_work_df))

if len(hard_zero_x_df) > 0:
    agent_info_cols = [
        "agent_user_code",
        "agent_name",
        "takim",
        "teamleader_name",
        "hamile_flg",
        "sut_izni_flg",
        "mesaiye_kalamaz_flg",
        "sabah_calisir_flg"
    ]

    agent_info = df_tam[agent_info_cols].copy()
    agent_info["agent_user_code"] = agent_info["agent_user_code"].astype(str).str.strip()

    hard_zero_x_df = hard_zero_x_df.merge(
        agent_info,
        on="agent_user_code",
        how="left"
    )

    print("Resmi tatilde hard x==0 detay:")
    display(
        hard_zero_x_df
        .sort_values(["shift_start", "shift_end", "takim", "agent_user_code"])
        .head(200)
    )

if len(hard_zero_work_df) > 0:
    print("Resmi tatilde hard work==0 detay:")
    display(
        hard_zero_work_df
        .sort_values(["date", "agent_user_code"])
        .head(200)
    )


# %% DEBUG - RESMİ TATİL SOFT MU HARD MI?

print("Arife günleri:", arife_plan_gunleri if "arife_plan_gunleri" in globals() else None)
print("Resmi tatil günleri:", resmi_tatil_plan_gunleri if "resmi_tatil_plan_gunleri" in globals() else None)

print("resmi_tatil_kisitli_ihlal var mı:", "resmi_tatil_kisitli_ihlal" in globals())
print("resmi_tatil_kisitli_ihlal değişken sayısı:", len(resmi_tatil_kisitli_ihlal) if "resmi_tatil_kisitli_ihlal" in globals() else 0)

print("resmi_tatil_mesai değişken sayısı:", len(resmi_tatil_mesai) if "resmi_tatil_mesai" in globals() else 0)

print("weekly_target_debug_df var mı:", "weekly_target_debug_df" in globals())

if "weekly_target_debug_df" in globals():
    display(
        weekly_target_debug_df
        .head(20)
    )
