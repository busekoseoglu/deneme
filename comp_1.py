# %% KONTROL - AKŞAM / GECE LOKASYON DAĞILIMI

lokasyon_kontrol_rows = []

for key, count_var in lokasyon_aksam_gece_count.items():

    ds, v, loc = key

    actual_count = solver.Value(count_var)
    target = lokasyon_aksam_gece_target[key]
    abs_diff = solver.Value(lokasyon_aksam_gece_abs_diff[key])

    required = int(talep[(ds, v)])

    assigned_total = sum(
        solver.Value(x[(a, ds, v)])
        for a in AGENTS
        if (a, ds, v) in x
    )

    config_oran = float(lokasyon_oranlari[loc])

    # Gerçek oran:
    # O vardiyada toplam atanan kişi içindeki lokasyon payı
    actual_ratio = (
        actual_count / assigned_total
        if assigned_total > 0
        else 0
    )

    target_ratio_diff = actual_ratio - config_oran

    shift_start, shift_end = _get_shift_time_for_aksam_gece(ds, v)

    lokasyon_kontrol_rows.append({
        "date": pd.to_datetime(ds).strftime("%Y-%m-%d"),
        "week": day_week.get(ds),
        "shift": v,
        "shift_start": shift_start,
        "shift_end": shift_end,

        "lokasyon": loc,
        "required": required,
        "assigned_total": assigned_total,

        "config_oran": config_oran,
        "target_count": target,
        "actual_count": actual_count,

        "count_diff": actual_count - target,
        "abs_diff": abs_diff,

        "actual_ratio": actual_ratio,
        "ratio_diff": target_ratio_diff,
        "ratio_diff_pct": target_ratio_diff * 100,
    })


lokasyon_kontrol_df = pd.DataFrame(lokasyon_kontrol_rows)

print("Lokasyon kontrol satır sayısı:", len(lokasyon_kontrol_df))

display(
    lokasyon_kontrol_df
    .sort_values(
        ["date", "shift_start", "lokasyon"]
    )
    .head(200)
)


# %% KONTROL - EN YÜKSEK LOKASYON SAPMALARI

display(
    lokasyon_kontrol_df
    .sort_values(
        ["abs_diff", "date", "shift_start"],
        ascending=[False, True, True]
    )
    .head(100)
)


