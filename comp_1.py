for loc in oran_lokasyonlari:

    oran = float(lokasyon_oranlari[loc])
    key = (ds, loc)

    loc_agent_count = lokasyon_agent_sayisi[loc]

    # Lokasyondaki toplam çalışan sayısının config'teki oranı
    target = int(round(
        loc_agent_count * oran
    ))

    lokasyon_aksam_gece_target[key] = target

    loc_assignment_vars = [
        x[(a, d, v)]
        for a in AGENTS
        if agent_location_map.get(str(a).strip()) == loc
        for d, v in day_shift_keys
        if (a, d, v) in x
    ]

    max_possible = len(loc_assignment_vars)

    lokasyon_aksam_gece_max_possible[key] = max_possible

    lokasyon_aksam_gece_count[key] = model.NewIntVar(
        0,
        max_possible,
        f"lokasyon_aksam_gece_count_{ds}_{loc}"
    )

    if loc_assignment_vars:
        model.Add(
            lokasyon_aksam_gece_count[key]
            ==
            sum(loc_assignment_vars)
        )
    else:
        model.Add(
            lokasyon_aksam_gece_count[key] == 0
        )

    diff_lb = -target
    diff_ub = max_possible - target

    lokasyon_aksam_gece_diff[key] = model.NewIntVar(
        diff_lb,
        diff_ub,
        f"lokasyon_aksam_gece_diff_{ds}_{loc}"
    )

    model.Add(
        lokasyon_aksam_gece_diff[key]
        ==
        lokasyon_aksam_gece_count[key] - target
    )

    max_abs_diff = max(
        abs(diff_lb),
        abs(diff_ub)
    )

    lokasyon_aksam_gece_abs_diff[key] = model.NewIntVar(
        0,
        max_abs_diff,
        f"lokasyon_aksam_gece_abs_diff_{ds}_{loc}"
    )

    model.AddAbsEquality(
        lokasyon_aksam_gece_abs_diff[key],
        lokasyon_aksam_gece_diff[key]
    )

    lokasyon_aksam_gece_sapma_terms.append(
        LOKASYON_AKSAM_GECE_ORAN_SAPMA_W
        * lokasyon_aksam_gece_abs_diff[key]
    )

    lokasyon_aksam_gece_debug_rows.append({
        "date": pd.to_datetime(ds).strftime("%Y-%m-%d"),
        "week": day_week.get(ds),
        "lokasyon": loc,
        "lokasyon_agent_sayisi": loc_agent_count,
        "config_oran": oran,
        "daily_aksam_gece_required": daily_required,
        "target_count": target,
        "max_possible_var_count": max_possible,
        "aksam_gece_shift_count": len(day_shift_keys),
        "sapma_weight": LOKASYON_AKSAM_GECE_ORAN_SAPMA_W,
    })
