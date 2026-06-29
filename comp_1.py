# %% KONTROL 1 - COVERAGE / GAP / BUFFER

coverage_check_rows = []

for ds in PLAN_GUNLER:
    for v in gun_vardiyalari.get(ds, []):

        assigned = sum(
            solver.Value(x[(a, ds, v)])
            for a in AGENTS
            if (a, ds, v) in x
        )

        required = int(talep[(ds, v)])
        lower_req = coverage_lower[(ds, v)]
        upper_req = coverage_upper[(ds, v)]

        coverage_check_rows.append({
            "tarih": str(ds),
            "gun": DAY_TR[pd.to_datetime(ds).weekday()],
            "weekday": pd.to_datetime(ds).weekday(),
            "hafta_ici": pd.to_datetime(ds).weekday() in [0, 1, 2, 3, 4],
            "hafta": day_week[ds],
            "vardiya": v,
            "baslangic": saat[(ds, v)][0],
            "bitis": saat[(ds, v)][1],
            "talep": required,
            "atanan": assigned,
            "gap_to_required": assigned - required,
            "lower_buffer": lower_req,
            "upper_buffer": upper_req,
            "gap_to_lower": assigned - lower_req,
            "gap_to_upper": assigned - upper_req,
            "buffer_ici": lower_req <= assigned <= upper_req,
            "under_buffer": solver.Value(under_buffer[(ds, v)]),
            "over_buffer": solver.Value(over_buffer[(ds, v)]),
            "missing_to_required": solver.Value(missing_to_required[(ds, v)]),
            "excess_to_required": solver.Value(excess_to_required[(ds, v)])
        })

coverage_check = pd.DataFrame(coverage_check_rows)

print("Toplam under_buffer:", coverage_check["under_buffer"].sum())
print("Toplam over_buffer:", coverage_check["over_buffer"].sum())
print("Toplam missing_to_required:", coverage_check["missing_to_required"].sum())
print("Toplam excess_to_required:", coverage_check["excess_to_required"].sum())

print("Minimum gap_to_required:", coverage_check["gap_to_required"].min())
print("Maximum gap_to_required:", coverage_check["gap_to_required"].max())

print("Buffer dışı vardiya sayısı:", len(coverage_check[coverage_check["buffer_ici"] == False]))
print("Buffer altı vardiya sayısı:", len(coverage_check[coverage_check["under_buffer"] > 0]))
print("Buffer üstü vardiya sayısı:", len(coverage_check[coverage_check["over_buffer"] > 0]))

display(
    coverage_check
    .sort_values(["under_buffer", "missing_to_required", "tarih", "baslangic"], ascending=[False, False, True, True])
)


# %% KONTROL 2 - PROBLEMLİ COVERAGE SATIRLARI

problem_coverage = coverage_check[
    (coverage_check["under_buffer"] > 0) |
    (coverage_check["over_buffer"] > 0) |
    (coverage_check["missing_to_required"] > 0)
].copy()

display(
    problem_coverage
    .sort_values(
        ["under_buffer", "missing_to_required", "over_buffer", "tarih", "baslangic"],
        ascending=[False, False, False, True, True]
    )
)

# %% KONTROL 3 - COVERAGE HAFTA İÇİ / HAFTA SONU ÖZET

coverage_weektype = (
    coverage_check
    .groupby("hafta_ici", as_index=False)
    .agg(
        toplam_talep=("talep", "sum"),
        toplam_atanan=("atanan", "sum"),
        toplam_gap=("gap_to_required", "sum"),
        toplam_under_buffer=("under_buffer", "sum"),
        toplam_over_buffer=("over_buffer", "sum"),
        toplam_missing_to_required=("missing_to_required", "sum"),
        toplam_excess_to_required=("excess_to_required", "sum"),
        min_gap=("gap_to_required", "min"),
        max_gap=("gap_to_required", "max")
    )
)

display(coverage_weektype)

# %% KONTROL 4 - GÜN / HAFTA BAZLI COVERAGE ÖZET

coverage_day_summary = (
    coverage_check
    .groupby(["hafta", "tarih", "gun", "hafta_ici"], as_index=False)
    .agg(
        toplam_talep=("talep", "sum"),
        toplam_atanan=("atanan", "sum"),
        toplam_gap=("gap_to_required", "sum"),
        toplam_under_buffer=("under_buffer", "sum"),
        toplam_over_buffer=("over_buffer", "sum"),
        toplam_missing_to_required=("missing_to_required", "sum"),
        toplam_excess_to_required=("excess_to_required", "sum"),
        min_gap=("gap_to_required", "min"),
        max_gap=("gap_to_required", "max")
    )
)

display(
    coverage_day_summary
    .sort_values(["toplam_under_buffer", "toplam_missing_to_required"], ascending=[False, False])
)

# %% KONTROL 5 - MESAİ

overtime_rows = []

for a in AGENTS:
    for wk in WEEKS:
        overtime_rows.append({
            "agent_user_code": a,
            "hafta": wk,
            "overtime_week": solver.Value(overtime_week[(a, wk)])
        })

overtime_check = pd.DataFrame(overtime_rows)

agent_info_cols = [
    "agent_user_code",
    "agent_name",
    "takim",
    "teamleader_name",
    "mesaiye_kalamaz_flg"
]

agent_info = df_tam[agent_info_cols].copy()
agent_info["agent_user_code"] = agent_info["agent_user_code"].astype(str).str.strip()

overtime_check = overtime_check.merge(agent_info, on="agent_user_code", how="left")

overtime_summary = (
    overtime_check
    .groupby(["agent_user_code", "agent_name", "takim", "teamleader_name", "mesaiye_kalamaz_flg"], as_index=False)
    .agg(toplam_mesai=("overtime_week", "sum"))
)

overtime_summary["aylik_max_2_mesai_ok"] = overtime_summary["toplam_mesai"] <= 2
overtime_summary["mesaiye_kalamaz_mesai_ok"] = ~(
    (pd.to_numeric(overtime_summary["mesaiye_kalamaz_flg"], errors="coerce").fillna(0).astype(int) == 1) &
    (overtime_summary["toplam_mesai"] > 0)
)

print("Toplam mesai:", overtime_summary["toplam_mesai"].sum())
print("Mesai yapan agent sayısı:", len(overtime_summary[overtime_summary["toplam_mesai"] > 0]))
print("Ayda 2'den fazla mesai yapan agent:", len(overtime_summary[overtime_summary["aylik_max_2_mesai_ok"] == False]))
print("Mesaiye kalamaz olup mesai yazılan agent:", len(overtime_summary[overtime_summary["mesaiye_kalamaz_mesai_ok"] == False]))

display(
    overtime_summary
    .sort_values("toplam_mesai", ascending=False)
    .head(50)
)

# %% KONTROL 6 - HAFTALIK ÇALIŞMA HEDEFİ

weekly_debug_rows = []

for a in AGENTS:
    izinli = izin_map.get(a, set())

    for wk, days_in_week in week_days.items():

        izin_count_this_week = sum(
            1
            for ds in days_in_week
            if pd.to_datetime(ds).date() in izinli
        )

        raw_normal_target = max(0, 5 - izin_count_this_week)

        feasible_days = []

        for ds in days_in_week:
            d_date = pd.to_datetime(ds).date()

            if d_date in izinli:
                continue

            has_option = any(
                (a, ds, v) in x
                for v in gun_vardiyalari.get(ds, [])
            )

            if has_option:
                feasible_days.append(ds)

        normal_target = min(raw_normal_target, len(feasible_days))

        worked_days = sum(
            solver.Value(work[(a, ds)])
            for ds in days_in_week
        )

        overtime_val = solver.Value(overtime_week[(a, wk)])

        weekly_debug_rows.append({
            "agent_user_code": a,
            "hafta": wk,
            "haftadaki_gun": len(days_in_week),
            "izin_count_this_week": izin_count_this_week,
            "raw_normal_target": raw_normal_target,
            "feasible_day_count": len(feasible_days),
            "normal_target": normal_target,
            "worked_days": worked_days,
            "overtime_week": overtime_val,
            "worked_minus_target": worked_days - normal_target,
            "haftalik_calisma_ok": worked_days == normal_target + overtime_val
        })

weekly_debug_df = pd.DataFrame(weekly_debug_rows)

print("Haftalık çalışma ihlali:", len(weekly_debug_df[weekly_debug_df["haftalik_calisma_ok"] == False]))

display(
    weekly_debug_df["worked_minus_target"]
    .value_counts()
    .sort_index()
)

display(
    weekly_debug_df[weekly_debug_df["haftalik_calisma_ok"] == False]
    .sort_values(["hafta", "agent_user_code"])
)

# %% KONTROL 7 - HAFTA İÇİ TAKIM BÜTÜNLÜĞÜ

roster_rows = []

for a in AGENTS:
    for ds in PLAN_GUNLER:
        for v in gun_vardiyalari.get(ds, []):
            if (a, ds, v) in x and solver.Value(x[(a, ds, v)]) == 1:
                roster_rows.append({
                    "agent_user_code": a,
                    "tarih": str(ds),
                    "gun": DAY_TR[pd.to_datetime(ds).weekday()],
                    "weekday": pd.to_datetime(ds).weekday(),
                    "hafta_ici": pd.to_datetime(ds).weekday() in [0, 1, 2, 3, 4],
                    "hafta": day_week[ds],
                    "takim": agent_team.get(a),
                    "vardiya": v,
                    "baslangic": saat[(ds, v)][0],
                    "bitis": saat[(ds, v)][1]
                })

roster_df = pd.DataFrame(roster_rows)

team_day_check = (
    roster_df
    .groupby(["hafta", "tarih", "gun", "weekday", "hafta_ici", "takim"], as_index=False)
    .agg(
        calisan_agent=("agent_user_code", "nunique"),
        vardiya_sayisi=("vardiya", "nunique")
    )
)

weekday_team_viol = team_day_check[
    (team_day_check["hafta_ici"] == True) &
    (team_day_check["vardiya_sayisi"] > 1)
]

weekend_team_split = team_day_check[
    (team_day_check["hafta_ici"] == False) &
    (team_day_check["vardiya_sayisi"] > 1)
]

print("Hafta içi bölünen takım-gün sayısı:", len(weekday_team_viol))
print("Hafta sonu bölünen takım-gün sayısı:", len(weekend_team_split))

display(weekday_team_viol.head(50))


# %% KONTROL 8 - CUMARTESİ PAZAR PEŞ PEŞE OFF

weekend_pairs_final = []

plan_dates = sorted([pd.to_datetime(ds).date() for ds in PLAN_GUNLER])
date_to_ds = {
    pd.to_datetime(ds).date(): ds
    for ds in PLAN_GUNLER
}

for d in plan_dates:
    if d.weekday() == 5:
        sunday = d + pd.Timedelta(days=1)

        if sunday in date_to_ds:
            weekend_pairs_final.append((date_to_ds[d], date_to_ds[sunday]))

weekend_off_rows = []

for a in AGENTS:
    for i, (sat_ds, sun_ds) in enumerate(weekend_pairs_final):
        sat_work = solver.Value(work[(a, sat_ds)])
        sun_work = solver.Value(work[(a, sun_ds)])

        weekend_off_rows.append({
            "agent_user_code": a,
            "pair_no": i + 1,
            "cumartesi": str(sat_ds),
            "pazar": str(sun_ds),
            "cumartesi_work": sat_work,
            "pazar_work": sun_work,
            "both_off": int((sat_work == 0) and (sun_work == 0))
        })

weekend_off_check = pd.DataFrame(weekend_off_rows)

weekend_off_summary = (
    weekend_off_check
    .groupby("agent_user_code", as_index=False)
    .agg(toplam_pes_pese_hafta_sonu_off=("both_off", "sum"))
)

weekend_off_summary["pes_pese_hafta_sonu_off_ok"] = (
    weekend_off_summary["toplam_pes_pese_hafta_sonu_off"] >= 1
)

viol_weekend_off = weekend_off_summary[
    weekend_off_summary["pes_pese_hafta_sonu_off_ok"] == False
]

print("Peş peşe Cumartesi-Pazar OFF almayan agent sayısı:", len(viol_weekend_off))

display(viol_weekend_off.head(50))


# %% KONTROL 9 - GECE / AKŞAM MAX 2 HAFTA

night_week_rows = []

for a in AGENTS:
    for wk in WEEKS:
        night_week_rows.append({
            "agent_user_code": a,
            "hafta": wk,
            "night_week": solver.Value(night_week[(a, wk)])
        })

night_week_check = pd.DataFrame(night_week_rows)

night_week_summary = (
    night_week_check
    .groupby("agent_user_code", as_index=False)
    .agg(toplam_gece_aksam_haftasi=("night_week", "sum"))
)

night_week_summary["max_2_gece_aksam_haftasi_ok"] = (
    night_week_summary["toplam_gece_aksam_haftasi"] <= 2
)

viol_night_week = night_week_summary[
    night_week_summary["max_2_gece_aksam_haftasi_ok"] == False
]

print("2 haftadan fazla gece/akşam vardiyası alan agent sayısı:", len(viol_night_week))

display(
    night_week_summary
    .sort_values("toplam_gece_aksam_haftasi", ascending=False)
    .head(50)
)

# %% KONTROL 10 - MAX 6 GÜN ÜST ÜSTE ÇALIŞMA

agent_day_rows = []

for a in AGENTS:
    for ds in PLAN_GUNLER:
        agent_day_rows.append({
            "agent_user_code": a,
            "tarih": str(ds),
            "tarih_dt": pd.to_datetime(ds),
            "work": solver.Value(work[(a, ds)])
        })

agent_day_work = pd.DataFrame(agent_day_rows)

streak_rows = []

for a, grp in agent_day_work.groupby("agent_user_code"):
    grp = grp.sort_values("tarih_dt")

    current_streak = 0
    max_streak = 0

    for _, r in grp.iterrows():
        if r["work"] == 1:
            current_streak += 1
        else:
            current_streak = 0

        max_streak = max(max_streak, current_streak)

    streak_rows.append({
        "agent_user_code": a,
        "max_ust_uste_calisma": max_streak,
        "max_6_gun_ok": max_streak <= 6
    })

streak_check = pd.DataFrame(streak_rows)

viol_streak = streak_check[streak_check["max_6_gun_ok"] == False]

print("Max 6 gün üst üste çalışma ihlali:", len(viol_streak))

display(
    streak_check
    .sort_values("max_ust_uste_calisma", ascending=False)
    .head(50)
)

# %% KONTROL 11 - 11 SAAT DİNLENME

def shift_start_end_dt(ds, baslangic, bitis):
    start_dt = pd.to_datetime(f"{ds} {baslangic}")
    end_dt = pd.to_datetime(f"{ds} {bitis}")

    if end_dt <= start_dt:
        end_dt += pd.Timedelta(days=1)

    return start_dt, end_dt

rest_rows = []

for _, r in roster_df.iterrows():
    start_dt, end_dt = shift_start_end_dt(r["tarih"], r["baslangic"], r["bitis"])

    rest_rows.append({
        "agent_user_code": r["agent_user_code"],
        "tarih": r["tarih"],
        "vardiya": r["vardiya"],
        "baslangic": r["baslangic"],
        "bitis": r["bitis"],
        "start_dt": start_dt,
        "end_dt": end_dt
    })

rest_df = pd.DataFrame(rest_rows).sort_values(["agent_user_code", "start_dt"])

rest_df["next_tarih"] = rest_df.groupby("agent_user_code")["tarih"].shift(-1)
rest_df["next_vardiya"] = rest_df.groupby("agent_user_code")["vardiya"].shift(-1)
rest_df["next_start_dt"] = rest_df.groupby("agent_user_code")["start_dt"].shift(-1)

rest_df["dinlenme_saat"] = (
    (rest_df["next_start_dt"] - rest_df["end_dt"])
    .dt.total_seconds() / 3600
)

rest_df["dinlenme_11_saat_ok"] = (
    rest_df["dinlenme_saat"].isna() |
    (rest_df["dinlenme_saat"] >= 11)
)

viol_rest = rest_df[rest_df["dinlenme_11_saat_ok"] == False]

print("11 saat dinlenme ihlali:", len(viol_rest))

display(viol_rest)

# %% KONTROL 12 - ÖZEL AGENT KURALLARI

special_check = roster_df.merge(
    df_tam[
        [
            "agent_user_code",
            "agent_name",
            "takim",
            "teamleader_name",
            "sabah_calisir_flg",
            "hamile_flg",
            "sut_izni_flg"
        ]
    ].assign(agent_user_code=lambda d: d["agent_user_code"].astype(str).str.strip()),
    on="agent_user_code",
    how="left"
)

def time_to_min(t):
    h, m = str(t)[:5].split(":")
    return int(h) * 60 + int(m)

special_check["bas_dk"] = special_check["baslangic"].apply(time_to_min)
special_check["bit_dk"] = special_check["bitis"].apply(time_to_min)

# Gece dönen vardiya ise bitişe 24 saat ekle
mask_night = special_check["bit_dk"] <= special_check["bas_dk"]
special_check.loc[mask_night, "bit_dk"] += 24 * 60

special_check["sabah_calisir_flg"] = pd.to_numeric(
    special_check["sabah_calisir_flg"], errors="coerce"
).fillna(0).astype(int)

special_check["hamile_flg"] = pd.to_numeric(
    special_check["hamile_flg"], errors="coerce"
).fillna(0).astype(int)

special_check["sut_izni_flg"] = pd.to_numeric(
    special_check["sut_izni_flg"], errors="coerce"
).fillna(0).astype(int)

# Sabah çalışır olanlar 20:00 sonrası biten vardiyada olamaz
sabah_viol = special_check[
    (special_check["sabah_calisir_flg"] == 1) &
    (special_check["bit_dk"] > time_to_min("20:00"))
]

# Hamile / süt izni hafta sonu çalışamaz
hamile_sut_weekend_viol = special_check[
    (
        (special_check["hamile_flg"] == 1) |
        (special_check["sut_izni_flg"] == 1)
    ) &
    (special_check["weekday"].isin([5, 6]))
]

# İzinli gün çalışma kontrolü
izin_viol_rows = []

for _, r in roster_df.iterrows():
    a = r["agent_user_code"]
    ds = r["tarih"]

    if pd.to_datetime(ds).date() in izin_map.get(a, set()):
        izin_viol_rows.append(r.to_dict())

izin_viol = pd.DataFrame(izin_viol_rows)

print("Sabah çalışır geç vardiya ihlali:", len(sabah_viol))
print("Hamile/süt izni hafta sonu ihlali:", len(hamile_sut_weekend_viol))
print("İzinli günde çalışma ihlali:", len(izin_viol))

display(sabah_viol.head(50))
display(hamile_sut_weekend_viol.head(50))
display(izin_viol.head(50))

# %% KONTROL 13 - AGENT AYLIK ÇALIŞMA GÜNÜ ÖZETİ

agent_work_rows = []

for a in AGENTS:
    izinli = izin_map.get(a, set())

    toplam_calisilan_gun = 0
    toplam_izinli_gun = 0
    toplam_off_gun = 0
    toplam_mesai = 0

    for ds in PLAN_GUNLER:
        worked = solver.Value(work[(a, ds)])
        is_izinli = pd.to_datetime(ds).date() in izinli

        toplam_calisilan_gun += worked

        if is_izinli:
            toplam_izinli_gun += 1

        if worked == 0 and not is_izinli:
            toplam_off_gun += 1

    for wk in WEEKS:
        toplam_mesai += solver.Value(overtime_week[(a, wk)])

    agent_work_rows.append({
        "agent_user_code": a,
        "toplam_calisilan_gun": toplam_calisilan_gun,
        "toplam_off_gun": toplam_off_gun,
        "toplam_izinli_gun": toplam_izinli_gun,
        "toplam_mesai": toplam_mesai,
        "plan_gun_sayisi": len(PLAN_GUNLER)
    })

agent_work_summary = pd.DataFrame(agent_work_rows)

agent_work_summary = agent_work_summary.merge(
    agent_info,
    on="agent_user_code",
    how="left"
)

display(
    agent_work_summary
    .sort_values("toplam_calisilan_gun", ascending=False)
)

display(
    agent_work_summary
    .groupby("toplam_calisilan_gun", as_index=False)
    .agg(agent_sayisi=("agent_user_code", "nunique"))
    .sort_values("toplam_calisilan_gun")
)

# %% KONTROL 14 - GENEL ÖZET

summary_rows = [
    {
        "kontrol": "toplam_under_buffer",
        "deger": coverage_check["under_buffer"].sum()
    },
    {
        "kontrol": "toplam_over_buffer",
        "deger": coverage_check["over_buffer"].sum()
    },
    {
        "kontrol": "toplam_missing_to_required",
        "deger": coverage_check["missing_to_required"].sum()
    },
    {
        "kontrol": "toplam_excess_to_required",
        "deger": coverage_check["excess_to_required"].sum()
    },
    {
        "kontrol": "min_gap_to_required",
        "deger": coverage_check["gap_to_required"].min()
    },
    {
        "kontrol": "max_gap_to_required",
        "deger": coverage_check["gap_to_required"].max()
    },
    {
        "kontrol": "toplam_mesai",
        "deger": overtime_summary["toplam_mesai"].sum()
    },
    {
        "kontrol": "mesai_yapan_agent_sayisi",
        "deger": len(overtime_summary[overtime_summary["toplam_mesai"] > 0])
    },
    {
        "kontrol": "haftalik_calisma_ihlali",
        "deger": len(weekly_debug_df[weekly_debug_df["haftalik_calisma_ok"] == False])
    },
    {
        "kontrol": "hafta_ici_takim_bolunme_ihlali",
        "deger": len(weekday_team_viol)
    },
    {
        "kontrol": "pes_pese_cmt_paz_off_almayan_agent",
        "deger": len(viol_weekend_off)
    },
    {
        "kontrol": "gece_aksam_2_hafta_ihlali",
        "deger": len(viol_night_week)
    },
    {
        "kontrol": "max_6_gun_ust_uste_ihlali",
        "deger": len(viol_streak)
    },
    {
        "kontrol": "11_saat_dinlenme_ihlali",
        "deger": len(viol_rest)
    },
    {
        "kontrol": "sabah_calisir_gec_vardiya_ihlali",
        "deger": len(sabah_viol)
    },
    {
        "kontrol": "hamile_sut_hafta_sonu_ihlali",
        "deger": len(hamile_sut_weekend_viol)
    },
    {
        "kontrol": "izinli_gunde_calisma_ihlali",
        "deger": len(izin_viol)
    }
]

final_summary = pd.DataFrame(summary_rows)

display(final_summary)
