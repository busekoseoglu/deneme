# %% [KONTROL 1] - ROSTER DF OLUŞTUR

roster_rows = []

for a in AGENTS:
    for ds in PLAN_GUNLER:
        for v in gun_vardiyalari.get(ds, []):
            if (a, ds, v) in x and solver.Value(x[(a, ds, v)]) == 1:
                roster_rows.append({
                    "agent_user_code": a,
                    "tarih": ds,
                    "gun": DAY_TR[pd.to_datetime(ds).weekday()],
                    "hafta": day_week[ds],
                    "vardiya": v,
                    "baslangic": saat[(ds, v)][0],
                    "bitis": saat[(ds, v)][1],
                    "takim": agent_team.get(a),
                    "is_exception": solver.Value(exception[(a, ds)])
                })

roster_df = pd.DataFrame(roster_rows)

print("roster satır sayısı:", len(roster_df))
display(roster_df.head())

# %% [KONTROL 2] - COVERAGE / BUFFER KONTROLÜ

coverage_rows = []

for ds in PLAN_GUNLER:
    for v in gun_vardiyalari.get(ds, []):
        assigned = sum(
            solver.Value(x[(a, ds, v)])
            for a in AGENTS
            if (a, ds, v) in x
        )

        req = int(talep[(ds, v)])
        lower_req = coverage_lower[(ds, v)]
        upper_req = coverage_upper[(ds, v)]

        under = solver.Value(under_buffer[(ds, v)])
        over = solver.Value(over_buffer[(ds, v)])

        coverage_rows.append({
            "tarih": ds,
            "gun": DAY_TR[pd.to_datetime(ds).weekday()],
            "hafta": day_week[ds],
            "vardiya": v,
            "baslangic": saat[(ds, v)][0],
            "bitis": saat[(ds, v)][1],
            "talep": req,
            "lower_10pct": lower_req,
            "upper_10pct": upper_req,
            "atanan": assigned,
            "gap": assigned - req,
            "under_buffer": under,
            "over_buffer": over,
            "buffer_ici": lower_req <= assigned <= upper_req
        })

coverage_df = pd.DataFrame(coverage_rows)

print("toplam talep:", coverage_df["talep"].sum())
print("toplam atanan:", coverage_df["atanan"].sum())
print("toplam under_buffer:", coverage_df["under_buffer"].sum())
print("toplam over_buffer:", coverage_df["over_buffer"].sum())

display(
    coverage_df[
        (coverage_df["under_buffer"] > 0) |
        (coverage_df["over_buffer"] > 0)
    ].sort_values(["tarih", "baslangic"])
)

# %% [KONTROL 3] - GÜNDE MAX 1 VARDİYA KONTROLÜ

daily_check = (
    roster_df
    .groupby(["agent_user_code", "tarih"])
    .size()
    .reset_index(name="vardiya_sayisi")
)

viol_daily = daily_check[daily_check["vardiya_sayisi"] > 1]

print("günde 1'den fazla vardiya ihlali:", len(viol_daily))
display(viol_daily.head(20))

# %% [KONTROL 4] - HAFTADA ÇALIŞMA GÜNÜ KONTROLÜ

weekly_check = (
    roster_df
    .groupby(["agent_user_code", "hafta"])
    .agg(calisilan_gun=("tarih", "nunique"))
    .reset_index()
)

display(
    weekly_check["calisilan_gun"]
    .value_counts()
    .sort_index()
    .reset_index()
    .rename(columns={"index": "haftalik_calisilan_gun", "calisilan_gun": "agent_hafta_sayisi"})
)

display(
    weekly_check[weekly_check["calisilan_gun"] != 5]
    .sort_values(["hafta", "agent_user_code"])
    .head(50)
)

# Tam 7 gün olan haftalarda 5 gün kontrolü

week_day_count = (
    pd.DataFrame({"tarih": PLAN_GUNLER})
    .assign(hafta=lambda d: d["tarih"].map(day_week))
    .groupby("hafta")
    .size()
    .reset_index(name="haftadaki_gun_sayisi")
)

full_weeks = week_day_count[week_day_count["haftadaki_gun_sayisi"] == 7]["hafta"].tolist()

viol_weekly_5 = weekly_check[
    (weekly_check["hafta"].isin(full_weeks)) &
    (weekly_check["calisilan_gun"] != 5)
]

print("tam haftalarda 5 gün çalışmayan agent-hafta:", len(viol_weekly_5))
display(viol_weekly_5.head(50))

# %% [KONTROL 5] - MAX 6 GÜN ÜST ÜSTE ÇALIŞMA KONTROLÜ

work_days = (
    roster_df[["agent_user_code", "tarih"]]
    .drop_duplicates()
    .copy()
)

work_days["tarih_dt"] = pd.to_datetime(work_days["tarih"])

viol_consecutive = []

for a, grp in work_days.groupby("agent_user_code"):
    dates = sorted(grp["tarih_dt"].dt.date.tolist())

    streak = 1

    for i in range(1, len(dates)):
        if (dates[i] - dates[i-1]).days == 1:
            streak += 1
        else:
            streak = 1

        if streak > 6:
            viol_consecutive.append({
                "agent_user_code": a,
                "ihlal_tarihi": dates[i],
                "ust_uste_gun": streak
            })

viol_consecutive_df = pd.DataFrame(viol_consecutive)

print("max 6 gün üst üste ihlali:", len(viol_consecutive_df))
display(viol_consecutive_df.head(20))

# %% [KONTROL 6] - İZİNLİ GÜNDE ÇALIŞMA KONTROLÜ

viol_izin = []

for _, row in roster_df.iterrows():
    a = row["agent_user_code"]
    ds = row["tarih"]
    d_date = pd.to_datetime(ds).date()

    if d_date in izin_map.get(a, set()):
        viol_izin.append(row)

viol_izin_df = pd.DataFrame(viol_izin)

print("izinli günde çalışma ihlali:", len(viol_izin_df))
display(viol_izin_df.head(20))

# %% [KONTROL 7] - SABAH ÇALIŞIR KONTROLÜ

def dk(t):
    h, m = str(t).split(":")
    return int(h) * 60 + int(m)

sabah_agents = set(
    df_tam[
        pd.to_numeric(df_tam["sabah_calisir_flg"], errors="coerce").fillna(0).astype(int) == 1
    ]["agent_user_code"].astype(str).str.strip()
)

viol_sabah = []

for _, row in roster_df.iterrows():
    a = row["agent_user_code"]

    if a not in sabah_agents:
        continue

    bas_dk = dk(row["baslangic"])
    bit_dk = dk(row["bitis"])

    if bit_dk <= bas_dk:
        bit_dk += 24 * 60

    if bit_dk > dk("20:00"):
        viol_sabah.append(row)

viol_sabah_df = pd.DataFrame(viol_sabah)

print("sabah çalışır ihlali:", len(viol_sabah_df))
display(viol_sabah_df.head(20))

# %% [KONTROL 8] - HAMİLE / SÜT İZNİ HAFTA SONU KONTROLÜ

special_weekend_agents = set(
    df_tam[
        (pd.to_numeric(df_tam["hamile_flg"], errors="coerce").fillna(0).astype(int) == 1) |
        (pd.to_numeric(df_tam["sut_izni_flg"], errors="coerce").fillna(0).astype(int) == 1)
    ]["agent_user_code"].astype(str).str.strip()
)

viol_special_weekend = []

for _, row in roster_df.iterrows():
    a = row["agent_user_code"]
    d = pd.to_datetime(row["tarih"]).date()

    if a in special_weekend_agents and d.weekday() in [5, 6]:
        viol_special_weekend.append(row)

viol_special_weekend_df = pd.DataFrame(viol_special_weekend)

print("hamile/süt izni hafta sonu ihlali:", len(viol_special_weekend_df))
display(viol_special_weekend_df.head(20))

# %% [KONTROL 9] - 11 SAAT DİNLENME KONTROLÜ

def shift_start_end(tarih, baslangic, bitis):
    start_dt = pd.to_datetime(f"{tarih} {baslangic}")
    end_dt = pd.to_datetime(f"{tarih} {bitis}")

    if end_dt <= start_dt:
        end_dt += pd.Timedelta(days=1)

    return start_dt, end_dt

tmp = roster_df.copy()

tmp[["start_dt", "end_dt"]] = tmp.apply(
    lambda r: pd.Series(shift_start_end(r["tarih"], r["baslangic"], r["bitis"])),
    axis=1
)

viol_rest = []

for a, grp in tmp.groupby("agent_user_code"):
    grp = grp.sort_values("start_dt")

    rows = grp.to_dict("records")

    for i in range(len(rows) - 1):
        curr = rows[i]
        nxt = rows[i + 1]

        rest_hours = (nxt["start_dt"] - curr["end_dt"]).total_seconds() / 3600

        if rest_hours < 11:
            viol_rest.append({
                "agent_user_code": a,
                "tarih_1": curr["tarih"],
                "vardiya_1": curr["vardiya"],
                "bitis_1": curr["bitis"],
                "tarih_2": nxt["tarih"],
                "vardiya_2": nxt["vardiya"],
                "baslangic_2": nxt["baslangic"],
                "dinlenme_saat": rest_hours
            })

viol_rest_df = pd.DataFrame(viol_rest)

print("11 saat dinlenme ihlali:", len(viol_rest_df))
display(viol_rest_df.head(20))

# %% [KONTROL 10] - TAKIM HAFTALIK BASE VARDİYA TABLOSU

team_base_rows = []

for t in TAKIMLAR:
    for wk in WEEKS:
        for v in week_vardiyalari[wk]:
            if (t, wk, v) in team_week_base and solver.Value(team_week_base[(t, wk, v)]) == 1:
                team_base_rows.append({
                    "takim": t,
                    "hafta": wk,
                    "base_vardiya": v
                })

team_base_df = pd.DataFrame(team_base_rows)

display(team_base_df.head(50))

# %% [KONTROL 11] - BASE VARDİYA DIŞINA ÇIKANLAR

roster_base_check = roster_df.merge(
    team_base_df,
    on=["takim", "hafta"],
    how="left"
)

roster_base_check["base_disi"] = (
    roster_base_check["vardiya"] != roster_base_check["base_vardiya"]
).astype(int)

print("base dışı çalışan satır sayısı:", roster_base_check["base_disi"].sum())
print("exception toplam:", roster_base_check["is_exception"].sum())

display(
    roster_base_check[roster_base_check["base_disi"] == 1]
    .sort_values(["hafta", "takim", "tarih"])
    .head(50)
)
