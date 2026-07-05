# %% [HÜCRE] - HAFTALIK ÇALIŞMA + MESAİ
# Resmi tatili weekly normal çalışma eşitliğinden ayıran versiyon.
#
# Mantık:
# - Resmi tatil normal haftalık çalışma gününden düşer.
# - Normal günlerde çalışma = normal_target + overtime_week
# - Resmi tatil çalışması bu eşitliğin dışında takip edilir.
# - Resmi tatilde çalışanlar ayrıca resmi_tatil_work_week ile işaretlenir.

# -------------------------------------------------
# Hafta yapısı yoksa oluştur
# -------------------------------------------------

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


# -------------------------------------------------
# Mesaiye kalamaz agentlar
# -------------------------------------------------

mesaiye_kalamaz_agents = set(
    df_tam[
        pd.to_numeric(df_tam["mesaiye_kalamaz_flg"], errors="coerce")
        .fillna(0)
        .astype(int) == 1
    ]["agent_user_code"].astype(str).str.strip()
)


# -------------------------------------------------
# Tatil kısıtlı agentlar yoksa oluştur
# -------------------------------------------------

if "tatil_kisitli_agents" not in globals():

    tatil_kisitli_agents = set(
        df_tam[
            (pd.to_numeric(df_tam["hamile_flg"], errors="coerce").fillna(0).astype(int) == 1) |
            (pd.to_numeric(df_tam["sut_izni_flg"], errors="coerce").fillna(0).astype(int) == 1) |
            (pd.to_numeric(df_tam["mesaiye_kalamaz_flg"], errors="coerce").fillna(0).astype(int) == 1)
        ]["agent_user_code"].astype(str).str.strip()
    )


# -------------------------------------------------
# Resmi tatil günlerini güvenli al
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


print("Hafta sayısı:", len(WEEKS))
print("Haftalar:", WEEKS)
print("Mesaiye kalamaz agent sayısı:", len(mesaiye_kalamaz_agents))
print("Tatil kısıtlı agent sayısı:", len(tatil_kisitli_agents))
print("Weekly normal çalışmadan ayrılacak resmi tatil günleri:", resmi_tatil_gunleri_for_weekly)


# -------------------------------------------------
# Haftalık çalışma + mesai kısıtları
# -------------------------------------------------

weekly_work_constraints = 0
weekly_overtime_block_constraints = 0
monthly_overtime_constraints = 0
resmi_tatil_work_week_constraints = 0

weekly_target_debug_rows = []

# Resmi tatil çalışmasını ayrıca takip edeceğiz.
resmi_tatil_work_week = {}

for a in AGENTS:
    a = str(a).strip()

    for wk in WEEKS:

        week_days_list = week_days[wk]

        if (a, wk) not in overtime_week:
            continue

        # -------------------------------------------------
        # 1) Haftanın resmi tatil günleri
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

        # Resmi tatilde izin varsa, normal hedeften iki kere düşmeyelim.
        izin_non_resmi_tatil_days = izin_days_this_week - resmi_tatil_days_this_week

        # -------------------------------------------------
        # 3) Normal çalışma günleri
        # -------------------------------------------------
        # Resmi tatil günlerini weekly normal work eşitliğinden çıkarıyoruz.
        # Çünkü resmi tatil çalışması ayrı mesai olarak takip edilecek.

        normal_work_days_this_week = [
            ds
            for ds in week_days_list
            if ds not in resmi_tatil_days_this_week
            and (a, ds) in work
        ]

        normal_work_vars = [
            work[(a, ds)]
            for ds in normal_work_days_this_week
        ]

        if not normal_work_vars:
            continue

        # -------------------------------------------------
        # 4) Normal hedef
        # -------------------------------------------------
        # Normal hedef:
        # 5 - resmi tatil sayısı - normal gün izni sayısı

        normal_target = NORMAL_WORK_DAYS
        normal_target -= len(resmi_tatil_days_this_week)
        normal_target -= len(izin_non_resmi_tatil_days)

        normal_target = max(0, normal_target)

        # -------------------------------------------------
        # 5) Fiziksel çalışılabilir normal gün sayısı
        # -------------------------------------------------

        feasible_normal_days = [
            ds
            for ds in normal_work_days_this_week
            if ds not in izin_non_resmi_tatil_days
        ]

        feasible_normal_day_count = len(feasible_normal_days)

        normal_target = min(normal_target, feasible_normal_day_count)

        # -------------------------------------------------
        # 6) Normal weekly eşitlik
        # -------------------------------------------------
        # DİKKAT:
        # Burada resmi tatil günü yok.
        # Sadece normal günler var.

        model.Add(
            sum(normal_work_vars) == normal_target + overtime_week[(a, wk)]
        )

        weekly_work_constraints += 1

        # -------------------------------------------------
        # 7) Mesaiye kalamaz agent normal mesai alamaz
        # -------------------------------------------------

        if a in mesaiye_kalamaz_agents:
            model.Add(overtime_week[(a, wk)] == 0)
            weekly_overtime_block_constraints += 1

        # -------------------------------------------------
        # 8) Normal günlerde +1 mesai yapacak yer yoksa overtime kapat
        # -------------------------------------------------

        if normal_target + 1 > feasible_normal_day_count:
            model.Add(overtime_week[(a, wk)] == 0)
            weekly_overtime_block_constraints += 1

        # -------------------------------------------------
        # 9) Resmi tatil çalışmasını ayrıca takip et
        # -------------------------------------------------

        resmi_tatil_work_vars = [
            work[(a, ds)]
            for ds in resmi_tatil_days_this_week
            if (a, ds) in work
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

            resmi_tatil_work_week_constraints += 1

        weekly_target_debug_rows.append({
            "agent_user_code": a,
            "week": wk,
            "normal_target": normal_target,
            "feasible_normal_day_count": feasible_normal_day_count,
            "resmi_tatil_days_count": len(resmi_tatil_days_this_week),
            "izin_days_count": len(izin_days_this_week),
            "izin_non_resmi_tatil_days_count": len(izin_non_resmi_tatil_days),
            "mesaiye_kalamaz": a in mesaiye_kalamaz_agents,
            "tatil_kisitli_agent": a in tatil_kisitli_agents,
        })


# -------------------------------------------------
# 10) Ayda max normal mesai hard kuralı
# -------------------------------------------------
# Şimdilik sadece overtime_week'i sayıyoruz.
# Resmi tatil mesaisini bu limite dahil etmiyoruz.
# Çünkü önce modeli feasible hale getirip resmi tatil çalışmasını ayrıca göreceğiz.

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

print("Haftalık normal çalışma kısıtı:", weekly_work_constraints)
print("Haftalık normal mesai kapatma kısıtı:", weekly_overtime_block_constraints)
print("Aylık max normal mesai kısıtı:", monthly_overtime_constraints)
print("Resmi tatil work-week takip kısıtı:", resmi_tatil_work_week_constraints)

print("Resmi tatil haftası weekly hedef debug:")
display(
    weekly_target_debug_df[
        weekly_target_debug_df["resmi_tatil_days_count"] > 0
    ]
    .sort_values(["week", "agent_user_code"])
    .head(100)
)
