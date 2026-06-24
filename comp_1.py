# %% [KONTROL 3] - AYNI GÜN BİRDEN FAZLA VARDİYA

same_day_check = (
    work_roster
    .groupby(["agent", "tarih"])
    .size()
    .reset_index(name="shift_count")
)

same_day_problem_df = same_day_check[same_day_check["shift_count"] > 1]

display(same_day_problem_df)
print("Aynı gün birden fazla vardiya problemi:", len(same_day_problem_df))


# %% [KONTROL 4] - GÜNDÜZ DIŞI ÇALIŞAMAZ KONTROLÜ

def time_to_minutes(t):
    h, m = map(int, str(t).split(":"))
    return h * 60 + m


def is_day_only_shift_allowed(baslangic, bitis):
    start_min = time_to_minutes(baslangic)
    end_min = time_to_minutes(bitis)

    # geceye dönen vardiya yasak: 15:00-00:00, 18:00-02:00
    if end_min <= start_min:
        return False

    # çok erken başlayan vardiya yasak: 00:00-08:00
    if start_min < time_to_minutes("07:00"):
        return False

    # 20:00 sonrası bitiş yasak
    if end_min > time_to_minutes("20:00"):
        return False

    return True


day_only_check = work_roster.copy()

day_only_check["day_only_flg"] = (
    (day_only_check["sabah_calisir_flg"].astype(int) == 1) |
    (day_only_check["hamile_flg"].astype(int) == 1) |
    (day_only_check["sut_izni_flg"].astype(int) == 1)
).astype(int)

day_only_check["allowed_shift"] = day_only_check.apply(
    lambda r: is_day_only_shift_allowed(r["baslangic"], r["bitis"]),
    axis=1
)

day_only_problem_df = day_only_check[
    (day_only_check["day_only_flg"] == 1) &
    (day_only_check["allowed_shift"] == False)
]

display(day_only_problem_df)
print("Gündüz dışı çalışma problemi:", len(day_only_problem_df))

# %% [KONTROL 5] - HAMİLE / SÜT İZNİ HAFTA SONU KONTROLÜ

weekend_check = work_roster.copy()
weekend_check["tarih_dt"] = pd.to_datetime(weekend_check["tarih"])
weekend_check["weekday"] = weekend_check["tarih_dt"].dt.weekday

weekend_special_problem_df = weekend_check[
    (
        (weekend_check["hamile_flg"].astype(int) == 1) |
        (weekend_check["sut_izni_flg"].astype(int) == 1)
    )
    &
    (weekend_check["weekday"].isin([5, 6]))
]

display(weekend_special_problem_df)
print("Hamile / süt izni hafta sonu çalışma problemi:", len(weekend_special_problem_df))


# %% [KONTROL 6] - 11 SAAT DİNLENME KONTROLÜ

def make_shift_datetime(tarih, baslangic, bitis):
    start_dt = pd.to_datetime(f"{tarih} {baslangic}")
    end_dt = pd.to_datetime(f"{tarih} {bitis}")

    if end_dt <= start_dt:
        end_dt = end_dt + pd.Timedelta(days=1)

    return start_dt, end_dt


rest_check = work_roster.copy()

rest_check[["start_dt", "end_dt"]] = rest_check.apply(
    lambda r: pd.Series(make_shift_datetime(r["tarih"], r["baslangic"], r["bitis"])),
    axis=1
)

rest_check = rest_check.sort_values(["agent", "start_dt"])

rest_problems = []

for agent, g in rest_check.groupby("agent"):
    g = g.sort_values("start_dt").reset_index(drop=True)

    for i in range(len(g) - 1):
        curr = g.loc[i]
        nxt = g.loc[i + 1]

        rest_hours = (nxt["start_dt"] - curr["end_dt"]).total_seconds() / 3600

        if rest_hours < 11:
            rest_problems.append({
                "agent": agent,
                "current_date": curr["tarih"],
                "current_vardiya": curr["vardiya"],
                "next_date": nxt["tarih"],
                "next_vardiya": nxt["vardiya"],
                "rest_hours": rest_hours
            })

rest_problem_df = pd.DataFrame(rest_problems)

display(rest_problem_df)
print("11 saat dinlenme problemi:", len(rest_problem_df))

# %% [KONTROL 7] - MAX 6 GÜN ÜST ÜSTE ÇALIŞMA KONTROLÜ

consecutive_problems = []

all_dates = sorted(pd.to_datetime(PLAN_GUNLER).date)

work_dates_by_agent = (
    work_roster
    .assign(tarih_dt=pd.to_datetime(work_roster["tarih"]).dt.date)
    .groupby("agent")["tarih_dt"]
    .apply(set)
    .to_dict()
)

for agent, worked_dates in work_dates_by_agent.items():
    for i in range(0, len(all_dates) - 7 + 1):
        window = all_dates[i:i + 7]
        worked_in_window = [d for d in window if d in worked_dates]

        if len(worked_in_window) > 6:
            consecutive_problems.append({
                "agent": agent,
                "window_start": window[0],
                "window_end": window[-1],
                "worked_days_count": len(worked_in_window),
                "worked_days": worked_in_window
            })

consecutive_problem_df = pd.DataFrame(consecutive_problems)

display(consecutive_problem_df)
print("Max 6 gün üst üste çalışma problemi:", len(consecutive_problem_df))


# %% [KONTROL 8] - HER AGENT EN AZ 1 VARDİYA ALMIŞ MI?

work_count_by_agent = (
    work_roster
    .groupby("agent")
    .size()
    .reset_index(name="work_day_count")
)

all_agents_df = pd.DataFrame({"agent": AGENTS})

min_work_check = all_agents_df.merge(
    work_count_by_agent,
    on="agent",
    how="left"
)

min_work_check["work_day_count"] = min_work_check["work_day_count"].fillna(0).astype(int)

min_work_problem_df = min_work_check[min_work_check["work_day_count"] == 0]

display(min_work_problem_df)
print("Hiç vardiya almayan agent sayısı:", len(min_work_problem_df))
