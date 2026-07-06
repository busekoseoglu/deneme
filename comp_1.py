# %% [HÜCRE] - HAFTALIK ÇALIŞMA + MESAİ - SOFT DEBUG / RESMİ TATİL HEDEF DÜZELTMELİ
# Amaç:
# Haftalık hedef infeasible yapmasın.
# Resmi tatil normal haftalık hedeften düşsün.
#
# Mantık:
# - Normal haftalık hedef = 5 - izin günleri - resmi tatil günleri
# - Aynı gün hem izin hem resmi tatilse 1 kez düşülür.
# - Resmi tatilde çalışan kişi ekstra çalışma/mesai gibi davranır.
# - Hedef tutmazsa weekly_under / weekly_over ile sapmayı gösterir.

if "day_week" not in globals() or "week_days" not in globals() or "WEEKS" not in globals():

    day_week = {}
    week_days = {}

    for ds in PLAN_GUNLER:
        dt = pd.to_datetime(ds)
        wk = f"{dt.isocalendar().year}-W{dt.isocalendar().week:02d}"

        day_week[ds] = wk

        if wk not in week_days:
            week_days[wk] = []

        week_days[wk].append(ds)

    WEEKS = sorted(week_days.keys())


mesaiye_kalamaz_agents = set(
    df_tam[
        pd.to_numeric(df_tam["mesaiye_kalamaz_flg"], errors="coerce")
        .fillna(0)
        .astype(int) == 1
    ]["agent_user_code"].astype(str).str.strip()
)


# -------------------------------------------------
# Resmi tatil günlerini PLAN_GUNLER formatında al
# -------------------------------------------------

resmi_tatil_gunleri_for_weekly = set()

if "resmi_tatil_plan_gunleri" in globals():
    resmi_tatil_gunleri_for_weekly = set(resmi_tatil_plan_gunleri)
else:
    if "ENABLE_RESMI_TATIL_KURALI" in globals() and ENABLE_RESMI_TATIL_KURALI:
        if "RESMI_TATIL_GUNLERI" in globals():
            resmi_tatil_key_set = set(RESMI_TATIL_GUNLERI)

            for ds in PLAN_GUNLER:
                ds_key = pd.to_datetime(ds).strftime("%Y-%m-%d")

                if ds_key in resmi_tatil_key_set:
                    resmi_tatil_gunleri_for_weekly.add(ds)

print("Haftalık hedeften düşülecek resmi tatil günleri:", resmi_tatil_gunleri_for_weekly)


weekly_work_constraints = 0
weekly_overtime_block_constraints = 0
monthly_overtime_constraints = 0

weekly_under = {}
weekly_over = {}
weekly_target_debug_rows = []


for a in AGENTS:
    a = str(a).strip()

    for wk in WEEKS:

        week_days_list = week_days[wk]

        work_vars = [
            work[(a, ds)]
            for ds in week_days_list
            if (a, ds) in work
        ]

        if not work_vars:
            continue

        # -------------------------------------------------
        # 1) İzin günleri
        # -------------------------------------------------

        izin_days_this_week = set(
            ds
            for ds in week_days_list
            if ds in izin_map.get(a, set())
        )

        # -------------------------------------------------
        # 2) Resmi tatil günleri
        # -------------------------------------------------

        resmi_tatil_days_this_week = set(
            ds
            for ds in week_days_list
            if ds in resmi_tatil_gunleri_for_weekly
        )

        # Aynı gün hem izin hem resmi tatilse 1 kez düş.
        hedef_dusulecek_gunler = izin_days_this_week | resmi_tatil_days_this_week

        # -------------------------------------------------
        # 3) Normal haftalık hedef
        # -------------------------------------------------

        normal_target = NORMAL_WORK_DAYS - len(hedef_dusulecek_gunler)
        normal_target = max(0, normal_target)

        # Eksik hafta koruması
        normal_target = min(normal_target, len(work_vars))

        # -------------------------------------------------
        # 4) Weekly sapma değişkenleri
        # -------------------------------------------------

        weekly_under[(a, wk)] = model.NewIntVar(
            0,
            len(work_vars),
            f"weekly_under_{a}_{wk}"
        )

        weekly_over[(a, wk)] = model.NewIntVar(
            0,
            len(work_vars),
            f"weekly_over_{a}_{wk}"
        )

        model.Add(
            sum(work_vars)
            + weekly_under[(a, wk)]
            - weekly_over[(a, wk)]
            ==
            normal_target + overtime_week[(a, wk)]
        )

        weekly_work_constraints += 1

        # -------------------------------------------------
        # 5) Mesaiye kalamaz agent mesai alamaz
        # -------------------------------------------------

        if a in mesaiye_kalamaz_agents:
            model.Add(overtime_week[(a, wk)] == 0)
            weekly_overtime_block_constraints += 1

        weekly_target_debug_rows.append({
            "agent_user_code": a,
            "week": wk,
            "normal_target": normal_target,
            "work_var_count": len(work_vars),
            "izin_count": len(izin_days_this_week),
            "resmi_tatil_count": len(resmi_tatil_days_this_week),
            "hedef_dusulecek_gun_count": len(hedef_dusulecek_gunler),
            "mesaiye_kalamaz": a in mesaiye_kalamaz_agents
        })


# -------------------------------------------------
# 6) Ayda max mesai hard kuralı
# -------------------------------------------------

for a in AGENTS:
    a = str(a).strip()

    model.Add(
        sum(
            overtime_week[(a, wk)]
            for wk in WEEKS
            if (a, wk) in overtime_week
        ) <= MAX_OVERTIME_PER_MONTH
    )

    monthly_overtime_constraints += 1


weekly_target_debug_df = pd.DataFrame(weekly_target_debug_rows)

print("Haftalık çalışma soft kısıtı:", weekly_work_constraints)
print("Haftalık mesai kapatma kısıtı:", weekly_overtime_block_constraints)
print("Aylık max mesai kısıtı:", monthly_overtime_constraints)
print("weekly_under değişken sayısı:", len(weekly_under))
print("weekly_over değişken sayısı:", len(weekly_over))

print("Resmi tatil haftası hedef kontrol:")
display(
    weekly_target_debug_df[
        weekly_target_debug_df["resmi_tatil_count"] > 0
    ]
    .sort_values(["week", "agent_user_code"])
    .head(100)
)