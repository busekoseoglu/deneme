# %% [HÜCRE] - HAFTALIK ÇALIŞMA + MESAİ - BASELINE VERSİYON
# Bu versiyon resmi tatili haftalık hedefe karıştırmaz.
# Amacımız önce modeli tekrar feasible hale getirmek.
#
# Mantık:
# - Haftalık çalışma = normal hedef + overtime_week
# - İzin günleri normal hedeften düşer
# - mesaiye_kalamaz agent overtime alamaz
# - ayda max mesai hard kalır

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

        izin_count = sum(
            1
            for ds in week_days_list
            if ds in izin_map.get(a, set())
        )

        # -------------------------------------------------
        # 2) Normal hedef
        # -------------------------------------------------

        normal_target = NORMAL_WORK_DAYS - izin_count
        normal_target = max(0, normal_target)

        # Bu hafta modelde gerçekten çalışabileceği gün sayısı
        feasible_day_count = len(work_vars)

        # Plan ayının başı/sonu gibi eksik haftalarda hedefi kırp
        normal_target = min(normal_target, feasible_day_count)

        # -------------------------------------------------
        # 3) Haftalık çalışma eşitliği
        # -------------------------------------------------

        model.Add(
            sum(work_vars) == normal_target + overtime_week[(a, wk)]
        )

        weekly_work_constraints += 1

        # -------------------------------------------------
        # 4) Mesaiye kalamaz agent mesai alamaz
        # -------------------------------------------------

        if a in mesaiye_kalamaz_agents:
            model.Add(overtime_week[(a, wk)] == 0)
            weekly_overtime_block_constraints += 1

        # Eğer +1 mesai koyacak fiziksel gün yoksa overtime kapat
        if normal_target + 1 > feasible_day_count:
            model.Add(overtime_week[(a, wk)] == 0)
            weekly_overtime_block_constraints += 1

        weekly_target_debug_rows.append({
            "agent_user_code": a,
            "week": wk,
            "normal_target": normal_target,
            "feasible_day_count": feasible_day_count,
            "izin_count": izin_count,
            "mesaiye_kalamaz": a in mesaiye_kalamaz_agents
        })


# -------------------------------------------------
# 5) Ayda max mesai hard kuralı
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

display(
    weekly_target_debug_df
    .sort_values(["week", "agent_user_code"])
    .head(100)
)


# %% [HÜCRE] - ARİFE HARD / RESMİ TATİL SOFT DEBUG ÇALIŞMA KURALLARI

arife_mesai = {}
resmi_tatil_mesai = {}
resmi_tatil_kisitli_ihlal = {}

tatil_constraints = 0
arife_09_13_zorunlu_constraints = 0
arife_13_sonrasi_yasak_constraints = 0
arife_non_kisitli_ozel_vardiya_yasak_constraints = 0
resmi_tatil_kisitli_soft_constraints = 0
tatil_skip_rows = []


for a in AGENTS:
    a = str(a).strip()

    # -------------------------------------------------
    # 1) ARİFE KURALLARI - HARD
    # -------------------------------------------------
    for ds in arife_plan_gunleri:

        ds_key = tatil_ds_key(ds)
        ozel_v = ARIFE_GUNLERI[ds_key]["ozel_vardiya_kodu"]

        if a in tatil_kisitli_agents:

            # Kısıtlı agent izinliyse arife 09-13'e zorlamıyoruz.
            if ds in izin_map.get(a, set()):
                tatil_skip_rows.append({
                    "agent_user_code": a,
                    "date": ds,
                    "rule": "arife_09_13",
                    "reason": "izinli"
                })

            else:
                # Kısıtlı agent arife özel 09-13 vardiyasına hard atanır.
                if (a, ds, ozel_v) in x:
                    model.Add(x[(a, ds, ozel_v)] == 1)
                    arife_09_13_zorunlu_constraints += 1
                else:
                    tatil_skip_rows.append({
                        "agent_user_code": a,
                        "date": ds,
                        "rule": "arife_09_13",
                        "reason": "ozel_09_13_x_yok"
                    })

            # Kısıtlı agentlar arife günü 13 sonrasına sarkan vardiyada çalışamaz.
            for v in gun_vardiyalari.get(ds, []):

                if (a, ds, v) not in x:
                    continue

                if arife_kisitli_yasak_vardiya_mi.get((ds, v), False):
                    model.Add(x[(a, ds, v)] == 0)
                    arife_13_sonrasi_yasak_constraints += 1

        else:
            # Kısıtlı olmayan agentlar özel ARIFE_09_13 vardiyasına atanamaz.
            if (a, ds, ozel_v) in x:
                model.Add(x[(a, ds, ozel_v)] == 0)
                arife_non_kisitli_ozel_vardiya_yasak_constraints += 1

        # Arife mesai etiketi
        for v in gun_vardiyalari.get(ds, []):

            if (a, ds, v) not in x:
                continue

            if arife_mesai_vardiyasi_mi.get((ds, v), False):

                arife_mesai[(a, ds, v)] = model.NewBoolVar(
                    f"arife_mesai_{a}_{ds}_{v}"
                )

                model.Add(arife_mesai[(a, ds, v)] == x[(a, ds, v)])
                tatil_constraints += 1


    # -------------------------------------------------
    # 2) RESMİ TATİL KURALLARI - SOFT DEBUG
    # -------------------------------------------------
    for ds in resmi_tatil_plan_gunleri:

        for v in gun_vardiyalari.get(ds, []):

            if (a, ds, v) not in x:
                continue

            # Kısıtlı agentlar resmi tatilde normalde çalışamaz.
            # Şimdilik hard yasak değil, soft ihlal.
            if a in tatil_kisitli_agents:

                resmi_tatil_kisitli_ihlal[(a, ds, v)] = model.NewBoolVar(
                    f"resmi_tatil_kisitli_ihlal_{a}_{ds}_{v}"
                )

                model.Add(
                    resmi_tatil_kisitli_ihlal[(a, ds, v)] >= x[(a, ds, v)]
                )

                resmi_tatil_kisitli_soft_constraints += 1

            # Resmi tatilde çalışan herkes resmi tatil mesaisi olarak etiketlenir.
            if resmi_tatil_mesai_vardiyasi_mi.get((ds, v), False):

                resmi_tatil_mesai[(a, ds, v)] = model.NewBoolVar(
                    f"resmi_tatil_mesai_{a}_{ds}_{v}"
                )

                model.Add(resmi_tatil_mesai[(a, ds, v)] == x[(a, ds, v)])
                tatil_constraints += 1


print("Arife 09-13 zorunlu atama kısıtı:", arife_09_13_zorunlu_constraints)
print("Arife 13 sonrası hard yasak kısıtı:", arife_13_sonrasi_yasak_constraints)
print("Arife non-kısıtlı özel vardiya yasak kısıtı:", arife_non_kisitli_ozel_vardiya_yasak_constraints)
print("Arife mesai değişken sayısı:", len(arife_mesai))

print("Resmi tatil kısıtlı soft ihlal kısıtı:", resmi_tatil_kisitli_soft_constraints)
print("Resmi tatil kısıtlı ihlal değişken sayısı:", len(resmi_tatil_kisitli_ihlal))
print("Resmi tatil mesai değişken sayısı:", len(resmi_tatil_mesai))

print("Toplam tatil yardımcı kısıtı:", tatil_constraints)

if tatil_skip_rows:
    tatil_skip_df = pd.DataFrame(tatil_skip_rows)
    print("Tatil skip sayısı:", len(tatil_skip_df))
    display(tatil_skip_df.head(100))
