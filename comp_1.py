# %% [HÜCRE] - HAFTALIK ÇALIŞMA + MESAİ - SOFT DEBUG
# Amaç:
# Haftalık hedef infeasible yapmasın.
# Hedef tutmazsa weekly_under / weekly_over değişkenleriyle sapmayı gösterelim.

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

        izin_count = sum(
            1
            for ds in week_days_list
            if ds in izin_map.get(a, set())
        )

        normal_target = NORMAL_WORK_DAYS - izin_count
        normal_target = max(0, normal_target)

        # Eksik hafta koruması
        normal_target = min(normal_target, len(work_vars))

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

        # ESKİ HARD:
        # sum(work_vars) == normal_target + overtime_week[(a, wk)]
        #
        # YENİ SOFT:
        # Eğer hedef tutmazsa weekly_under / weekly_over ile sapmayı yakalıyoruz.

        model.Add(
            sum(work_vars)
            + weekly_under[(a, wk)]
            - weekly_over[(a, wk)]
            ==
            normal_target + overtime_week[(a, wk)]
        )

        weekly_work_constraints += 1

        # Mesaiye kalamaz agent mesai alamaz.
        if a in mesaiye_kalamaz_agents:
            model.Add(overtime_week[(a, wk)] == 0)
            weekly_overtime_block_constraints += 1

        weekly_target_debug_rows.append({
            "agent_user_code": a,
            "week": wk,
            "normal_target": normal_target,
            "work_var_count": len(work_vars),
            "izin_count": izin_count,
            "mesaiye_kalamaz": a in mesaiye_kalamaz_agents
        })


# Ayda max mesai hard kalsın.
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

display(
    weekly_target_debug_df
    .sort_values(["week", "agent_user_code"])
    .head(10)
)


# -------------------------------------------------
# HAFTALIK HEDEF SAPMA CEZASI
# -------------------------------------------------

WEEKLY_UNDER_W = 200000
WEEKLY_OVER_W = 50000

if "weekly_under" in globals():
    for (a, wk), var in weekly_under.items():
        objective_terms.append(WEEKLY_UNDER_W * var)

if "weekly_over" in globals():
    for (a, wk), var in weekly_over.items():
        objective_terms.append(WEEKLY_OVER_W * var)

print("WEEKLY_UNDER_W:", WEEKLY_UNDER_W)
print("WEEKLY_OVER_W:", WEEKLY_OVER_W)


# %% KONTROL - HAFTALIK HEDEF SAPMALARI

weekly_deviation_rows = []

for (a, wk), under_var in weekly_under.items():

    under_val = solver.Value(under_var)
    over_val = solver.Value(weekly_over[(a, wk)])

    if under_val == 0 and over_val == 0:
        continue

    week_days_list = week_days[wk]

    actual_work_days = sum(
        solver.Value(work[(a, ds)])
        for ds in week_days_list
        if (a, ds) in work
    )

    overtime_val = (
        solver.Value(overtime_week[(a, wk)])
        if (a, wk) in overtime_week
        else None
    )

    weekly_deviation_rows.append({
        "agent_user_code": a,
        "week": wk,
        "actual_work_days": actual_work_days,
        "overtime_week": overtime_val,
        "weekly_under": under_val,
        "weekly_over": over_val,
    })

weekly_deviation_df = pd.DataFrame(weekly_deviation_rows)

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

if len(weekly_deviation_df) > 0:
    weekly_deviation_df = weekly_deviation_df.merge(
        agent_info,
        on="agent_user_code",
        how="left"
    )

print("Haftalık hedef sapması olan agent-week sayısı:", len(weekly_deviation_df))

display(
    weekly_deviation_df
    .sort_values(["weekly_under", "weekly_over", "week", "takim"], ascending=[False, False, True, True])
    .head(200)
)


print("Weekly under toplam:", sum(
    solver.Value(v)
    for v in weekly_under.values()
))

print("Weekly over toplam:", sum(
    solver.Value(v)
    for v in weekly_over.values()
))

print("Resmi tatil kısıtlı ihlal toplam:", sum(
    solver.Value(v)
    for v in resmi_tatil_kisitli_ihlal.values()
) if "resmi_tatil_kisitli_ihlal" in globals() else 0)

print("Arife 13 sonrası ihlal kontrolü:")
arife_ihlal_sayisi = 0

for a in AGENTS:
    a = str(a).strip()
    if a not in tatil_kisitli_agents:
        continue

    for ds in arife_plan_gunleri:
        for v in gun_vardiyalari.get(ds, []):
            if (a, ds, v) not in x:
                continue

            if arife_kisitli_yasak_vardiya_mi.get((ds, v), False):
                if solver.Value(x[(a, ds, v)]) == 1:
                    arife_ihlal_sayisi += 1

print("Arife 13 sonrası ihlal sayısı:", arife_ihlal_sayisi)
