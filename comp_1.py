# %% [KISIT] - PARTIAL END HAFTA İÇİ HAMİLE / SÜT İZNİ ÇALIŞMA ZORUNLULUĞU
#
# Amaç:
# Ay sonundaki partial_end haftasında görünen hafta içi günlerde,
# hamile veya süt izni olan agentlar izinli/hard OFF değilse çalıştırılır.
#
# Çalışmaya zorlanmayacak günler:
# - Resmî tatil
# - izin_map içindeki izin günleri
# - hard_off_map içindeki off_t2 / hard yapılmış off_t günleri


# ------------------------------------------------------------
# 1) PARTIAL END HAFTALARINI HAZIRLA
# ------------------------------------------------------------

if "partial_end_weeks" not in globals():

    if (
        "week_boundary_df" in globals()
        and isinstance(week_boundary_df, pd.DataFrame)
        and not week_boundary_df.empty
    ):
        partial_end_weeks = set(
            week_boundary_df.loc[
                week_boundary_df["partial_type"] == "partial_end",
                "week",
            ]
            .astype(str)
            .str.strip()
        )
    else:
        partial_end_weeks = set()

else:
    partial_end_weeks = {
        str(w).strip()
        for w in partial_end_weeks
    }


# ------------------------------------------------------------
# 2) HAMİLE / SÜT İZNİ AGENT SETİ
# ------------------------------------------------------------

hamile_flg = (
    pd.to_numeric(
        df_tam["hamile_flg"],
        errors="coerce",
    )
    .fillna(0)
    .astype(int)
)

sut_izni_flg = (
    pd.to_numeric(
        df_tam["sut_izni_flg"],
        errors="coerce",
    )
    .fillna(0)
    .astype(int)
)

hamile_sut_agents = set(
    df_tam.loc[
        (hamile_flg == 1) | (sut_izni_flg == 1),
        "agent_user_code",
    ]
    .astype(str)
    .str.strip()
)


# ------------------------------------------------------------
# 3) RESMÎ TATİL GÜNLERİ
# ------------------------------------------------------------

resmi_tatil_days_for_partial_end = set()

if "resmi_tatil_plan_gunleri" in globals():

    resmi_tatil_days_for_partial_end = {
        pd.to_datetime(ds).date()
        for ds in resmi_tatil_plan_gunleri
    }

elif "RESMI_TATIL_GUNLERI" in globals():

    resmi_tatil_key_set = {
        pd.to_datetime(d).strftime("%Y-%m-%d")
        for d in RESMI_TATIL_GUNLERI
    }

    resmi_tatil_days_for_partial_end = {
        pd.to_datetime(ds).date()
        for ds in PLAN_GUNLER
        if pd.to_datetime(ds).strftime("%Y-%m-%d")
        in resmi_tatil_key_set
    }


# ------------------------------------------------------------
# 4) HARD KISITLAR
# ------------------------------------------------------------

partial_end_hamile_sut_work_constraints = 0
partial_end_hamile_sut_work_debug_rows = []

for a_raw in hamile_sut_agents:

    a = str(a_raw).strip()

    izin_gunleri = {
        pd.to_datetime(d).date()
        for d in izin_map.get(a, set())
    }

    hard_off_gunleri = {
        pd.to_datetime(d).date()
        for d in hard_off_map.get(a, set())
    }

    for ds in PLAN_GUNLER:

        ds_date = pd.to_datetime(ds).date()
        wk = str(day_week[ds]).strip()
        weekday = pd.to_datetime(ds).weekday()

        # Sadece ay sonundaki partial_end hafta
        if wk not in partial_end_weeks:
            continue

        # Sadece Pazartesi-Cuma
        if weekday not in [0, 1, 2, 3, 4]:
            continue

        # Resmî tatilde zorunlu çalışma kurulmaz
        if ds_date in resmi_tatil_days_for_partial_end:

            partial_end_hamile_sut_work_debug_rows.append({
                "agent_user_code": a,
                "date": pd.to_datetime(ds).strftime("%Y-%m-%d"),
                "week": wk,
                "constraint_added": False,
                "reason": "resmi_tatil",
            })

            continue

        # Normal izin gününde zorunlu çalışma kurulmaz
        if ds_date in izin_gunleri:

            partial_end_hamile_sut_work_debug_rows.append({
                "agent_user_code": a,
                "date": pd.to_datetime(ds).strftime("%Y-%m-%d"),
                "week": wk,
                "constraint_added": False,
                "reason": "izinli",
            })

            continue

        # off_t2 veya hard yapılmış off_t gününde zorlanmaz
        if ds_date in hard_off_gunleri:

            partial_end_hamile_sut_work_debug_rows.append({
                "agent_user_code": a,
                "date": pd.to_datetime(ds).strftime("%Y-%m-%d"),
                "week": wk,
                "constraint_added": False,
                "reason": "hard_off",
            })

            continue

        # Karar değişkeni yoksa zorunlu çalışma kuramayız
        if (a, ds) not in work:

            partial_end_hamile_sut_work_debug_rows.append({
                "agent_user_code": a,
                "date": pd.to_datetime(ds).strftime("%Y-%m-%d"),
                "week": wk,
                "constraint_added": False,
                "reason": "work_variable_yok",
            })

            continue

        # İzinli/hard OFF değilse çalışmak zorunda
        model.Add(work[(a, ds)] == 1)

        partial_end_hamile_sut_work_constraints += 1

        partial_end_hamile_sut_work_debug_rows.append({
            "agent_user_code": a,
            "date": pd.to_datetime(ds).strftime("%Y-%m-%d"),
            "week": wk,
            "constraint_added": True,
            "reason": "partial_end_weekday_force_work",
        })


# ------------------------------------------------------------
# 5) DEBUG DATAFRAME
# ------------------------------------------------------------

partial_end_hamile_sut_work_debug_df = pd.DataFrame(
    partial_end_hamile_sut_work_debug_rows
)

print("Partial end haftalar:", partial_end_weeks)
print("Hamile / süt izni agent sayısı:", len(hamile_sut_agents))
print(
    "Partial end hafta içi hamile/süt izni çalışma zorunluluğu kısıt sayısı:",
    partial_end_hamile_sut_work_constraints,
)

if not partial_end_hamile_sut_work_debug_df.empty:

    display(
        partial_end_hamile_sut_work_debug_df
        .sort_values(
            ["date", "agent_user_code"]
        )
        .head(30)
    )
