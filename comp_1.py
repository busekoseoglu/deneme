# %% KONTROL - ARİFE 13 SONRASI İHLAL DETAYI

arife_ihlal_detay_rows = []

for (a, ds, v), ihlal_var in arife_13_sonrasi_ihlal.items():
    a = str(a).strip()

    ihlal_value = solver.Value(ihlal_var)

    if ihlal_value != 1:
        continue

    bas, bit = saat[(ds, v)] if (ds, v) in saat else (None, None)

    ds_key = arife_ds_key(ds)
    hedef_bas, hedef_bit = ARIFE_GUNLERI[ds_key]["kisitli_agent_normal_vardiya"]

    # Bu agent için 09-13 vardiya opsiyonu var mı?
    hedef_09_13_var_mi = False
    hedef_09_13_atandi_mi = False

    for vv in gun_vardiyalari.get(ds, []):

        if (a, ds, vv) not in x:
            continue

        if (ds, vv) not in saat:
            continue

        b2, e2 = saat[(ds, vv)]

        if b2 == hedef_bas and e2 == hedef_bit:
            hedef_09_13_var_mi = True

            if solver.Value(x[(a, ds, vv)]) == 1:
                hedef_09_13_atandi_mi = True

    wk = day_week[ds]

    week_work_days = sum(
        solver.Value(work[(a, d)])
        for d in week_days[wk]
        if (a, d) in work
    )

    week_izin_days = sum(
        1
        for d in week_days[wk]
        if d in izin_map.get(a, set())
    )

    overtime_val = (
        solver.Value(overtime_week[(a, wk)])
        if (a, wk) in overtime_week
        else None
    )

    arife_ihlal_detay_rows.append({
        "agent_user_code": a,
        "date": ds,
        "week": wk,
        "assigned_shift": v,
        "shift_start": bas,
        "shift_end": bit,

        "hedef_09_13_var_mi": hedef_09_13_var_mi,
        "hedef_09_13_atandi_mi": hedef_09_13_atandi_mi,

        "week_work_days": week_work_days,
        "week_izin_days": week_izin_days,
        "overtime_week": overtime_val,

        "arife_mesai_vardiyasi_mi": arife_mesai_vardiyasi_mi.get((ds, v), False),
        "arife_kisitli_icin_yasak_vardiya_mi": arife_kisitli_yasak_vardiya_mi.get((ds, v), False),
    })

arife_ihlal_detay_df = pd.DataFrame(arife_ihlal_detay_rows)

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

arife_ihlal_detay_df = arife_ihlal_detay_df.merge(
    agent_info,
    on="agent_user_code",
    how="left"
)

print("Arife 13 sonrası ihlal sayısı:", len(arife_ihlal_detay_df))

display(
    arife_ihlal_detay_df
    .sort_values(["shift_start", "takim", "agent_user_code"])
)


# %% KONTROL - ARİFE 13 SONRASI İHLAL VARDİYA ÖZETİ

display(
    arife_ihlal_detay_df
    .groupby(
        [
            "date",
            "assigned_shift",
            "shift_start",
            "shift_end",
            "hamile_flg",
            "sut_izni_flg",
            "mesaiye_kalamaz_flg"
        ],
        as_index=False
    )
    .agg(
        agent_sayisi=("agent_user_code", "nunique")
    )
    .sort_values(["shift_start", "shift_end"])
)
