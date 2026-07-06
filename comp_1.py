# %% [HÜCRE] - HAFTALIK ÇALIŞMA + NORMAL MESAİ - RESMİ TATİL AYRI
# Mantık:
# - Normal haftalık çalışma sadece resmi tatil olmayan günlerden hesaplanır.
# - Normal mesai = overtime_week
# - Resmi tatilde çalışma bu eşitliğe girmez.
# - Resmi tatil mesaisi, ayda max 2 normal mesai limitine dahil değildir.
# - Şimdilik weekly_under / weekly_over soft debug kalsın.

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

print("Normal haftalık çalışmadan ayrı tutulacak resmi tatil günleri:", resmi_tatil_gunleri_for_weekly)


weekly_work_constraints = 0
weekly_overtime_block_constraints = 0
monthly_overtime_constraints = 0

weekly_under = {}
weekly_over = {}
resmi_tatil_work_week = {}

weekly_target_debug_rows = []


for a in AGENTS:
    a = str(a).strip()

    for wk in WEEKS:

        week_days_list = week_days[wk]

        if (a, wk) not in overtime_week:
            continue

        # -------------------------------------------------
        # 1) Bu haftanın resmi tatil günleri
        # -------------------------------------------------

        resmi_tatil_days_this_week = set(
            ds
            for ds in week_days_list
            if ds in resmi_tatil_gunleri_for_weekly
        )

        # -------------------------------------------------
        # 2) İzin günleri
        # -------------------------------------------------

        izin_days_this_week = set(
            ds
            for ds in week_days_list
            if ds in izin_map.get(a, set())
        )

        # Resmi tatilde izin varsa, normal hedefte iki kere düşmeyelim.
        izin_normal_days_this_week = izin_days_this_week - resmi_tatil_days_this_week

        # -------------------------------------------------
        # 3) Normal günlerdeki work değişkenleri
        # -------------------------------------------------
        # DİKKAT:
        # Resmi tatil günleri burada yok.
        # Bu yüzden resmi tatilde çalışmak overtime_week tüketmez.

        normal_work_vars = [
            work[(a, ds)]
            for ds in week_days_list
            if (a, ds) in work
            and ds not in resmi_tatil_days_this_week
        ]

        if not normal_work_vars:
            continue

        # -------------------------------------------------
        # 4) Resmi tatil work değişkenleri
        # -------------------------------------------------

        resmi_tatil_work_vars = [
            work[(a, ds)]
            for ds in week_days_list
            if (a, ds) in work
            and ds in resmi_tatil_days_this_week
        ]

        if resmi_tatil_work_vars:
            resmi_tatil_work_week[(a, wk)] = model.NewIntVar(
                0,
                len(resmi_tatil_work_vars),
                f"resmi_tatil_work_week_{a}_{wk}"
            )

            model.Add(
                resmi_tatil_work_week[(a, wk)] == sum(resmi_tatil_work_vars)
            )

        # -------------------------------------------------
        # 5) Normal haftalık hedef
        # -------------------------------------------------
        # Normal hedef:
        # 5 - resmi tatil gün sayısı - normal izin gün sayısı

        normal_target = NORMAL_WORK_DAYS
        normal_target -= len(resmi_tatil_days_this_week)
        normal_target -= len(izin_normal_days_this_week)

        normal_target = max(0, normal_target)
        normal_target = min(normal_target, len(normal_work_vars))

        # -------------------------------------------------
        # 6) Weekly sapma değişkenleri
        # -------------------------------------------------

        weekly_under[(a, wk)] = model.NewIntVar(
            0,
            len(normal_work_vars),
            f"weekly_under_{a}_{wk}"
        )

        weekly_over[(a, wk)] = model.NewIntVar(
            0,
            len(normal_work_vars),
            f"weekly_over_{a}_{wk}"
        )

        # DİKKAT:
        # Sadece normal günler eşitlikte.
        # Resmi tatil çalışması burada yok.
        model.Add(
            sum(normal_work_vars)
            + weekly_under[(a, wk)]
            - weekly_over[(a, wk)]
            ==
            normal_target + overtime_week[(a, wk)]
        )

        weekly_work_constraints += 1

        # -------------------------------------------------
        # 7) Mesaiye kalamaz agent normal mesai alamaz
        # -------------------------------------------------

        if a in mesaiye_kalamaz_agents:
            model.Add(overtime_week[(a, wk)] == 0)
            weekly_overtime_block_constraints += 1

        weekly_target_debug_rows.append({
            "agent_user_code": a,
            "week": wk,
            "normal_target": normal_target,
            "normal_work_var_count": len(normal_work_vars),
            "resmi_tatil_work_var_count": len(resmi_tatil_work_vars),
            "izin_normal_count": len(izin_normal_days_this_week),
            "resmi_tatil_count": len(resmi_tatil_days_this_week),
            "mesaiye_kalamaz": a in mesaiye_kalamaz_agents
        })


# -------------------------------------------------
# 8) Ayda max NORMAL mesai hard kuralı
# -------------------------------------------------
# Resmi tatil mesaisi bu limite dahil değildir.

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

print("Haftalık normal çalışma soft kısıtı:", weekly_work_constraints)
print("Haftalık normal mesai kapatma kısıtı:", weekly_overtime_block_constraints)
print("Aylık max normal mesai kısıtı:", monthly_overtime_constraints)
print("weekly_under değişken sayısı:", len(weekly_under))
print("weekly_over değişken sayısı:", len(weekly_over))
print("resmi_tatil_work_week değişken sayısı:", len(resmi_tatil_work_week))

print("Resmi tatil haftası hedef kontrol:")
display(
    weekly_target_debug_df[
        weekly_target_debug_df["resmi_tatil_count"] > 0
    ]
    .sort_values(["week", "agent_user_code"])
    .head(100)
)

RESMI_TATIL_MESAI_W = 0
IKINCI_MESAI_W = 0
OVERTIME_W = 1000

print("Weekly under toplam:", sum(
    solver.Value(v)
    for v in weekly_under.values()
))

print("Weekly over toplam:", sum(
    solver.Value(v)
    for v in weekly_over.values()
))

print("Normal mesai toplam:", sum(
    solver.Value(v)
    for v in overtime_week.values()
))

print("Resmi tatil work toplam:", sum(
    solver.Value(v)
    for v in resmi_tatil_work_week.values()
) if "resmi_tatil_work_week" in globals() else 0)

print("Resmi tatil kısıtlı ihlal toplam:", sum(
    solver.Value(v)
    for v in resmi_tatil_kisitli_ihlal.values()
) if "resmi_tatil_kisitli_ihlal" in globals() else 0)