# %% [HÜCRE] - HAFTALIK ÇALIŞMA + MESAİ
# Resmi tatil düzeltmeli versiyon
#
# Mantık:
# - İzin günleri haftalık normal hedeften düşer.
# - Resmi tatil günleri HERKESİN normal haftalık hedefinden düşer.
# - Resmi tatilde çalışabilen agent resmi tatilde çalışırsa bu overtime_week ile mesai olur.
# - Hamile / süt izni / mesaiye kalamaz agentlar resmi tatilde zaten çalışamaz.

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
# Tatil kısıtlı agentlar
# -------------------------------------------------
# Kısıtlı agent:
# - hamile
# - süt izni
# - mesaiye kalamaz

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
print("Haftalık normal hedeften düşülecek resmi tatil günleri:", resmi_tatil_gunleri_for_weekly)


# -------------------------------------------------
# Haftalık çalışma + mesai kısıtları
# -------------------------------------------------

weekly_work_constraints = 0
weekly_overtime_block_constraints = 0
monthly_overtime_constraints = 0

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
        # DİKKAT:
        # Resmi tatil herkesin normal haftalık hedefinden düşer.
        # Çünkü resmi tatil normal mesai günü değildir.
        # O gün çalışan kişi ekstra/mesai çalışmış olur.

        resmi_tatil_days_this_week = set(
            ds
            for ds in week_days_list
            if ds in resmi_tatil_gunleri_for_weekly
        )

        # Normal hedeften düşülecek günler:
        # izin + resmi tatil
        # Aynı gün hem izin hem resmi tatilse 1 kere düşülür.
        hedef_dusulecek_gunler = izin_days_this_week | resmi_tatil_days_this_week

        normal_target = NORMAL_WORK_DAYS - len(hedef_dusulecek_gunler)
        normal_target = max(0, normal_target)

        # -------------------------------------------------
        # 3) Agentın fiziksel çalışabileceği günler
        # -------------------------------------------------
        # İzin günlerinde kimse çalışamaz.
        # Resmi tatilde kısıtlı agent çalışamaz.
        # Resmi tatilde kısıtlı olmayan agent çalışabilir; çalışırsa overtime_week = 1 olur.

        feasible_days = []

        for ds in week_days_list:

            if (a, ds) not in work:
                continue

            if ds in izin_days_this_week:
                continue

            if a in tatil_kisitli_agents and ds in resmi_tatil_days_this_week:
                continue

            feasible_days.append(ds)

        feasible_day_count = len(feasible_days)

        # Normal hedef fiziksel mümkün gün sayısını aşmasın.
        normal_target = min(normal_target, feasible_day_count)

        # -------------------------------------------------
        # 4) Haftalık çalışma eşitliği
        # -------------------------------------------------
        # Resmi tatilde çalışan normal agent için:
        # normal_target = 4
        # toplam work = 5
        # overtime_week = 1 olur.

        model.Add(
            sum(work_vars) == normal_target + overtime_week[(a, wk)]
        )

        weekly_work_constraints += 1

        # -------------------------------------------------
        # 5) Mesaiye kalamaz agent mesai alamaz
        # -------------------------------------------------

        if a in mesaiye_kalamaz_agents:
            model.Add(overtime_week[(a, wk)] == 0)
            weekly_overtime_block_constraints += 1

        # -------------------------------------------------
        # 6) Fiziksel olarak +1 mesai yapacak gün yoksa mesaiyi kapat
        # -------------------------------------------------

        if normal_target + 1 > feasible_day_count:
            model.Add(overtime_week[(a, wk)] == 0)
            weekly_overtime_block_constraints += 1

        weekly_target_debug_rows.append({
            "agent_user_code": a,
            "week": wk,
            "normal_target": normal_target,
            "feasible_day_count": feasible_day_count,
            "izin_days_count": len(izin_days_this_week),
            "resmi_tatil_days_count": len(resmi_tatil_days_this_week),
            "hedef_dusulecek_gun_count": len(hedef_dusulecek_gunler),
            "mesaiye_kalamaz": a in mesaiye_kalamaz_agents,
            "tatil_kisitli_agent": a in tatil_kisitli_agents,
        })


# -------------------------------------------------
# 7) Ayda max mesai hard kuralı
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

print("Haftalık çalışma kısıtı:", weekly_work_constraints)
print("Haftalık mesai kapatma kısıtı:", weekly_overtime_block_constraints)
print("Aylık max mesai kısıtı:", monthly_overtime_constraints)

print("Resmi tatil olan haftalarda hedefler:")
display(
    weekly_target_debug_df[
        weekly_target_debug_df["resmi_tatil_days_count"] > 0
    ]
    .sort_values(["week", "agent_user_code"])
    .head(100)
)
