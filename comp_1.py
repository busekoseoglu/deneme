# %% [HÜCRE] - HAFTALIK ÇALIŞMA + MESAİ
# Amaç:
# Her agent haftalık normal çalışma hedefi kadar çalışır.
# İzin günleri hedeften düşer.
# Resmi tatilde çalışamayan kısıtlı agentlar için resmi tatil günü de hedeften düşer.
#
# Mesai:
# overtime_week[(a, wk)] = 1 ise agent o hafta normal hedefin 1 gün üstünde çalışır.
# mesaiye_kalamaz_flg = 1 olan agent mesai alamaz.

weekly_work_constraints = 0
weekly_overtime_constraints = 0
weekly_target_debug_rows = []

# Mesaiye kalamaz agentlar
mesaiye_kalamaz_agents = set(
    df_tam[
        pd.to_numeric(df_tam["mesaiye_kalamaz_flg"], errors="coerce")
        .fillna(0)
        .astype(int) == 1
    ]["agent_user_code"].astype(str).str.strip()
)

for a in AGENTS:
    a = str(a).strip()

    for wk in WEEKS:

        week_days_list = week_days[wk]

        # Bu hafta modelde gerçekten var olan work değişkenleri
        work_vars = [
            work[(a, ds)]
            for ds in week_days_list
            if (a, ds) in work
        ]

        if not work_vars:
            continue

        # -------------------------------------------------
        # 1) Normal izin günleri
        # -------------------------------------------------
        izin_days_this_week = set(
            ds
            for ds in week_days_list
            if ds in izin_map.get(a, set())
        )

        # -------------------------------------------------
        # 2) Resmi tatil nedeniyle çalışamayacağı günler
        # -------------------------------------------------
        # Hamile / süt izni / mesaiye kalamaz agentlar resmi tatilde çalışamaz.
        # Bu günleri haftalık hedeften düşmezsek infeasible olur.
        resmi_tatil_off_days_this_week = set()

        if "resmi_tatil_plan_gunleri" in globals() and "tatil_kisitli_agents" in globals():

            if a in tatil_kisitli_agents:

                resmi_tatil_off_days_this_week = set(
                    ds
                    for ds in week_days_list
                    if ds in resmi_tatil_plan_gunleri
                )

        # Aynı gün hem izin hem resmi tatilse iki kere düşmeyelim.
        hedef_dusulecek_gunler = izin_days_this_week | resmi_tatil_off_days_this_week

        # -------------------------------------------------
        # 3) Haftalık normal hedef
        # -------------------------------------------------
        normal_target = NORMAL_WORK_DAYS - len(hedef_dusulecek_gunler)
        normal_target = max(0, normal_target)

        # Agentın gerçekten çalışabileceği gün sayısı
        # İzin günleri ve resmi tatil-off günleri çıkarılır.
        feasible_days = [
            ds
            for ds in week_days_list
            if (a, ds) in work
            and ds not in hedef_dusulecek_gunler
        ]

        feasible_day_count = len(feasible_days)

        # Eğer hedef, uygun gün sayısından büyükse hedefi kırp.
        # Bu özellikle kısmi plan haftaları veya özel tatil haftaları için koruma sağlar.
        normal_target = min(normal_target, feasible_day_count)

        # -------------------------------------------------
        # 4) Haftalık çalışma eşitliği
        # -------------------------------------------------
        # Haftalık çalışma = normal hedef + mesai
        model.Add(
            sum(work_vars) == normal_target + overtime_week[(a, wk)]
        )
        weekly_work_constraints += 1

        # -------------------------------------------------
        # 5) Mesaiye kalamaz agent mesai alamaz
        # -------------------------------------------------
        if a in mesaiye_kalamaz_agents:
            model.Add(overtime_week[(a, wk)] == 0)
            weekly_overtime_constraints += 1

        # -------------------------------------------------
        # 6) Eğer normal_target + 1 uygun gün sayısını aşıyorsa mesai alamaz
        # -------------------------------------------------
        if normal_target + 1 > feasible_day_count:
            model.Add(overtime_week[(a, wk)] == 0)
            weekly_overtime_constraints += 1

        # -------------------------------------------------
        # 7) Ayda max mesai
        # -------------------------------------------------
        # Bunu her hafta içinde tekrar eklemiyoruz.
        # Aşağıda agent bazında bir kere eklenecek.

        weekly_target_debug_rows.append({
            "agent_user_code": a,
            "week": wk,
            "normal_target": normal_target,
            "feasible_day_count": feasible_day_count,
            "izin_days_count": len(izin_days_this_week),
            "resmi_tatil_off_days_count": len(resmi_tatil_off_days_this_week),
            "hedef_dusulecek_gun_count": len(hedef_dusulecek_gunler),
            "mesaiye_kalamaz": a in mesaiye_kalamaz_agents
        })


# -------------------------------------------------
# 8) Ayda max mesai hard kuralı
# -------------------------------------------------

monthly_overtime_constraints = 0

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
print("Haftalık mesai engel kısıtı:", weekly_overtime_constraints)
print("Aylık max mesai kısıtı:", monthly_overtime_constraints)

print("Resmi tatil nedeniyle hedef düşen agent-week sayısı:")
display(
    weekly_target_debug_df[
        weekly_target_debug_df["resmi_tatil_off_days_count"] > 0
    ]
    .sort_values(["week", "agent_user_code"])
    .head(100)
)
