# %% [KISIT] - PARTIAL END HAFTA İÇİ HAMİLE / SÜT İZNİ ÇALIŞMA ZORUNLULUĞU
# Amaç:
# Ay sonu partial week hafta içi günlerde bitiyorsa,
# hamile veya süt izni olan agentlar o görünen hafta içi günlerde OFF bırakılmasın.
#
# Örnek:
# Haziran 2026:
# 2026-06-29 Pazartesi
# 2026-06-30 Salı
# Bu günler 2026-W27 partial_end haftasına denk geliyor.
#
# Hamile / süt izni olan kişiler hafta sonu çalışamadığı için,
# bu görünen hafta içi günlerde izinli değillerse çalıştırılmalı.
#
# DİKKAT:
# - izin_map'e dokunmuyoruz.
# - Pazartesi/Cuma izin flag'i varsa agent_izinli_mi(a, ds) True döner ve kişi zorlanmaz.
# - Yıllık izin / doğum izni / idari izin varsa kişi zorlanmaz.
# - Resmi tatil günleri zorlanmaz.
# - Sadece izinli olmayan hamile/süt izni agentlar için work[(a, ds)] = 1 kurulur.

# --------------------------------------------------
# 1) Partial end week setini garantiye al
# --------------------------------------------------

if "partial_end_weeks" not in globals():

    if "week_boundary_df" in globals() and isinstance(week_boundary_df, pd.DataFrame):
        partial_end_weeks = set(
            week_boundary_df.loc[
                week_boundary_df["partial_type"] == "partial_end",
                "week"
            ].astype(str).str.strip()
        )
    else:
        partial_end_weeks = set()

else:
    partial_end_weeks = set(str(w).strip() for w in partial_end_weeks)

print("Partial end haftalar:", partial_end_weeks)


# --------------------------------------------------
# 2) Hamile veya süt izni olan agent seti
# --------------------------------------------------

hamile_sut_agents = set(
    df_tam.loc[
        (
            pd.to_numeric(df_tam["hamile_flg"], errors="coerce")
            .fillna(0)
            .astype(int) == 1
        )
        |
        (
            pd.to_numeric(df_tam["sut_izni_flg"], errors="coerce")
            .fillna(0)
            .astype(int) == 1
        ),
        "agent_user_code"
    ]
    .astype(str)
    .str.strip()
)

print("Hamile / süt izni agent sayısı:", len(hamile_sut_agents))


# --------------------------------------------------
# 3) Resmi tatil gün seti
# --------------------------------------------------

resmi_tatil_days_for_partial_end = set()

if "resmi_tatil_plan_gunleri" in globals():
    resmi_tatil_days_for_partial_end = set(resmi_tatil_plan_gunleri)

elif "RESMI_TATIL_GUNLERI" in globals():
    resmi_tatil_key_set = set(
        pd.to_datetime(d).strftime("%Y-%m-%d")
        for d in RESMI_TATIL_GUNLERI
    )

    for ds in PLAN_GUNLER:
        if pd.to_datetime(ds).strftime("%Y-%m-%d") in resmi_tatil_key_set:
            resmi_tatil_days_for_partial_end.add(ds)

print("Partial end kuralında hariç tutulacak resmi tatil günleri:", resmi_tatil_days_for_partial_end)


# --------------------------------------------------
# 4) Ön kontrol
# --------------------------------------------------
# Bu kontrol sadece uyarı verir.
# Eğer bir partial_end gününde çalışması zorlanan hamile/süt agent sayısı,
# o günün toplam required sayısından fazlaysa model infeasible olabilir.
#
# Çünkü partial week fazla atama limiti 0 ise:
# assigned <= required
# olduğu için herkesi çalıştıracak yer olmayabilir.

partial_end_hamile_sut_precheck_rows = []

for ds in PLAN_GUNLER:

    wk = str(day_week.get(ds)).strip() if "day_week" in globals() else None
    weekday = pd.to_datetime(ds).weekday()

    if wk not in partial_end_weeks:
        continue

    if weekday not in [0, 1, 2, 3, 4]:
        continue

    if ds in resmi_tatil_days_for_partial_end:
        continue

    forced_candidate_agents = []

    for a in hamile_sut_agents:

        if agent_izinli_mi(a, ds):
            continue

        if (a, ds) not in work:
            continue

        forced_candidate_agents.append(a)

    total_required_this_day = sum(
        int(talep[(ds, v)])
        for v in gun_vardiyalari.get(ds, [])
        if (ds, v) in talep
    )

    partial_end_hamile_sut_precheck_rows.append({
        "date": pd.to_datetime(ds).strftime("%Y-%m-%d"),
        "week": wk,
        "gun": safe_day_name(ds) if "safe_day_name" in globals() else pd.to_datetime(ds).day_name(),
        "forced_candidate_agent_count": len(forced_candidate_agents),
        "total_required_this_day": total_required_this_day,
        "risk_infeasible": len(forced_candidate_agents) > total_required_this_day,
    })

partial_end_hamile_sut_precheck_df = pd.DataFrame(partial_end_hamile_sut_precheck_rows)

print("Partial end hamile/süt ön kontrol:")
display(partial_end_hamile_sut_precheck_df)


# --------------------------------------------------
# 5) Hard constraint
# --------------------------------------------------
# Partial end hafta içi günlerde:
# hamile/süt izni agent
# + resmi tatil değil
# + izinli değil
# => çalışmak zorunda.

partial_end_hamile_sut_work_constraints = 0
partial_end_hamile_sut_work_debug_rows = []

for a in hamile_sut_agents:

    a = str(a).strip()

    for ds in PLAN_GUNLER:

        wk = str(day_week.get(ds)).strip() if "day_week" in globals() else None
        weekday = pd.to_datetime(ds).weekday()

        if wk not in partial_end_weeks:
            continue

        if weekday not in [0, 1, 2, 3, 4]:
            continue

        if ds in resmi_tatil_days_for_partial_end:
            partial_end_hamile_sut_work_debug_rows.append({
                "agent_user_code": a,
                "date": pd.to_datetime(ds).strftime("%Y-%m-%d"),
                "week": wk,
                "constraint_added": False,
                "reason": "resmi_tatil"
            })
            continue

        if agent_izinli_mi(a, ds):
            partial_end_hamile_sut_work_debug_rows.append({
                "agent_user_code": a,
                "date": pd.to_datetime(ds).strftime("%Y-%m-%d"),
                "week": wk,
                "constraint_added": False,
                "reason": "izinli"
            })
            continue

        if (a, ds) not in work:
            partial_end_hamile_sut_work_debug_rows.append({
                "agent_user_code": a,
                "date": pd.to_datetime(ds).strftime("%Y-%m-%d"),
                "week": wk,
                "constraint_added": False,
                "reason": "work_variable_yok"
            })
            continue

        model.Add(work[(a, ds)] == 1)

        partial_end_hamile_sut_work_constraints += 1

        partial_end_hamile_sut_work_debug_rows.append({
            "agent_user_code": a,
            "date": pd.to_datetime(ds).strftime("%Y-%m-%d"),
            "week": wk,
            "constraint_added": True,
            "reason": "partial_end_weekday_force_work"
        })

partial_end_hamile_sut_work_debug_df = pd.DataFrame(
    partial_end_hamile_sut_work_debug_rows
)

print(
    "Partial end hafta içi hamile/süt izni çalışma zorunluluğu kısıt sayısı:",
    partial_end_hamile_sut_work_constraints
)

display(
    partial_end_hamile_sut_work_debug_df
    .sort_values(["date", "agent_user_code"])
    .head(30)
)



# %% [KONTROL] - PARTIAL END HAMİLE/SÜT KURALI SONUÇ KONTROLÜ
# Amaç:
# Constraint eklenen agent-günlerde gerçekten çalışmış mı görmek.

partial_end_hamile_sut_result_rows = []

for _, r in partial_end_hamile_sut_work_debug_df.iterrows():

    if r["constraint_added"] != True:
        continue

    a = str(r["agent_user_code"]).strip()
    ds = r["date"]

    # PLAN_GUNLER içindeki gerçek ds objesini bul
    ds_obj = None
    for d in PLAN_GUNLER:
        if pd.to_datetime(d).strftime("%Y-%m-%d") == ds:
            ds_obj = d
            break

    if ds_obj is None:
        continue

    worked = 0

    if (a, ds_obj) in work:
        worked = int(solver.Value(work[(a, ds_obj)]))

    assigned_shift = None
    shift_start = None
    shift_end = None

    for v in gun_vardiyalari.get(ds_obj, []):
        if (a, ds_obj, v) in x and int(solver.Value(x[(a, ds_obj, v)])) == 1:
            assigned_shift = v
            shift_start, shift_end = get_shift_time(ds_obj, v) if "get_shift_time" in globals() else (None, None)
            break

    partial_end_hamile_sut_result_rows.append({
        "agent_user_code": a,
        "date": ds,
        "week": r["week"],
        "worked": worked,
        "assigned_shift": assigned_shift,
        "shift_start": shift_start,
        "shift_end": shift_end,
        "kontrol_ok": worked == 1,
    })

partial_end_hamile_sut_result_df = pd.DataFrame(
    partial_end_hamile_sut_result_rows
)

print(
    "Partial end hamile/süt kuralı ihlal sayısı:",
    (
        partial_end_hamile_sut_result_df["kontrol_ok"] == False
    ).sum()
    if not partial_end_hamile_sut_result_df.empty
    else 0
)

display(
    partial_end_hamile_sut_result_df
    .sort_values(["kontrol_ok", "date", "agent_user_code"])
)
