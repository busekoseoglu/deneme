# %% KONTROL 6 - HAFTALIK ÇALIŞMA HEDEFİ

weekly_debug_rows = []

# Resmi tatil günlerini al
resmi_tatil_gunleri_for_check = set()

if "resmi_tatil_plan_gunleri" in globals():
    resmi_tatil_gunleri_for_check = set(resmi_tatil_plan_gunleri)
else:
    if "ENABLE_RESMI_TATIL_KURALI" in globals() and ENABLE_RESMI_TATIL_KURALI:
        if "RESMI_TATIL_GUNLERI" in globals():
            resmi_tatil_key_set = set(RESMI_TATIL_GUNLERI)

            for ds in PLAN_GUNLER:
                ds_key = pd.to_datetime(ds).strftime("%Y-%m-%d")
                if ds_key in resmi_tatil_key_set:
                    resmi_tatil_gunleri_for_check.add(ds)


for a in AGENTS:
    a = str(a).strip()
    izinli = izin_map.get(a, set())

    for wk, days_in_week in week_days.items():

        # Bu haftadaki resmi tatil günleri
        resmi_tatil_days_this_week = set(
            ds
            for ds in days_in_week
            if ds in resmi_tatil_gunleri_for_check
        )

        # Bu haftadaki izin günleri
        izin_days_this_week = set(
            ds
            for ds in days_in_week
            if pd.to_datetime(ds).date() in izinli or ds in izinli
        )

        # Resmi tatil normal hedefe dahil değil.
        # Aynı gün hem izin hem resmi tatilse iki kere düşmeyelim.
        izin_normal_days_this_week = izin_days_this_week - resmi_tatil_days_this_week

        # Normal hedef = 5 - resmi tatil - normal izin
        raw_normal_target = NORMAL_WORK_DAYS - len(resmi_tatil_days_this_week) - len(izin_normal_days_this_week)
        raw_normal_target = max(0, raw_normal_target)

        # Feasible günler: izin olmayan ve resmi tatil olmayan, en az bir x opsiyonu olan günler
        feasible_days = []

        for ds in days_in_week:

            if ds in resmi_tatil_days_this_week:
                continue

            if pd.to_datetime(ds).date() in izinli or ds in izinli:
                continue

            has_option = any(
                (a, ds, v) in x
                for v in gun_vardiyalari.get(ds, [])
            )

            if has_option:
                feasible_days.append(ds)

        normal_target = min(raw_normal_target, len(feasible_days))

        # Normal günlerde çalışılan gün sayısı
        normal_worked_days = sum(
            solver.Value(work[(a, ds)])
            for ds in days_in_week
            if (a, ds) in work
            and ds not in resmi_tatil_days_this_week
        )

        # Resmi tatilde çalışılan gün sayısı
        resmi_tatil_worked_days = sum(
            solver.Value(work[(a, ds)])
            for ds in days_in_week
            if (a, ds) in work
            and ds in resmi_tatil_days_this_week
        )

        overtime_val = (
            solver.Value(overtime_week[(a, wk)])
            if (a, wk) in overtime_week
            else 0
        )

        weekly_under_val = (
            solver.Value(weekly_under[(a, wk)])
            if "weekly_under" in globals() and (a, wk) in weekly_under
            else None
        )

        weekly_over_val = (
            solver.Value(weekly_over[(a, wk)])
            if "weekly_over" in globals() and (a, wk) in weekly_over
            else None
        )

        weekly_debug_rows.append({
            "agent_user_code": a,
            "hafta": wk,
            "haftadaki_gun": len(days_in_week),
            "izin_count_this_week": len(izin_days_this_week),
            "resmi_tatil_count_this_week": len(resmi_tatil_days_this_week),
            "raw_normal_target": raw_normal_target,
            "feasible_day_count": len(feasible_days),
            "normal_target": normal_target,
            "normal_worked_days": normal_worked_days,
            "resmi_tatil_worked_days": resmi_tatil_worked_days,
            "total_worked_days": normal_worked_days + resmi_tatil_worked_days,
            "overtime_week": overtime_val,
            "weekly_under": weekly_under_val,
            "weekly_over": weekly_over_val,
            "worked_minus_target": normal_worked_days - normal_target,
            "normal_haftalik_calisma_ok": normal_worked_days == normal_target + overtime_val,
        })


weekly_target_check_df = pd.DataFrame(weekly_debug_rows)

print("Normal çalışma hedef farkı dağılımı:")
display(
    weekly_target_check_df["worked_minus_target"]
    .value_counts()
    .sort_index()
)

print("Weekly under toplam:")
if "weekly_under" in globals():
    print(sum(solver.Value(v) for v in weekly_under.values()))
else:
    print("weekly_under yok")

print("Weekly over toplam:")
if "weekly_over" in globals():
    print(sum(solver.Value(v) for v in weekly_over.values()))
else:
    print("weekly_over yok")

display(
    weekly_target_check_df
    .sort_values(["worked_minus_target", "hafta", "agent_user_code"])
    .head(100)
)