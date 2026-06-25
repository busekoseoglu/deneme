# %% [HÜCRE] - TAKIM HAFTALIK BASE VARDİYA - HAFTA İÇİ HARD / HAFTA SONU SERBEST
# Yeni iş kuralı:
# Pazartesi-Cuma: Takım bütünlüğü korunur. Takımdaki herkes o hafta seçilen base vardiyada çalışır.
# Cumartesi-Pazar: Takım bütünlüğü zorunlu değildir. Agentlar ihtiyaca göre farklı vardiyalara dağılabilir.

team_base_constraints = 0
team_weekday_link_constraints = 0
weekend_free_count = 0

# 1. Her takım-her hafta için tek base vardiya seç
for t in TAKIMLAR:
    for wk in WEEKS:
        vars_base = [
            team_week_base[(t, wk, v)]
            for v in week_vardiyalari[wk]
            if (t, wk, v) in team_week_base
        ]

        if vars_base:
            model.Add(sum(vars_base) == 1)
            team_base_constraints += 1


# 2. Sadece hafta içi günlerde agent takımının base vardiyasında çalışabilir
for a in AGENTS:
    t = agent_team.get(a)

    if t is None or pd.isna(t):
        continue

    t = str(t).strip()

    for ds in PLAN_GUNLER:
        weekday = pd.to_datetime(ds).weekday()
        wk = day_week[ds]

        for v in gun_vardiyalari.get(ds, []):

            if (a, ds, v) not in x:
                continue

            # Hafta içi: takım base vardiyası hard
            if weekday in [0, 1, 2, 3, 4]:
                model.Add(
                    x[(a, ds, v)] <= team_week_base[(t, wk, v)]
                )
                team_weekday_link_constraints += 1

            # Hafta sonu: takım serbest, constraint eklemiyoruz
            else:
                weekend_free_count += 1


print("takım-hafta tek base vardiya kısıtı:", team_base_constraints)
print("hafta içi takım hard bağlantı kısıtı:", team_weekday_link_constraints)
print("hafta sonu serbest bırakılan agent-gün-vardiya opsiyonu:", weekend_free_count)


# %% HIZLI KONTROL - HAFTA İÇİ TAKIM / HAFTA SONU SERBEST / BUFFER / MESAİ

# Roster oluştur
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
                    "hafta": day_week[ds],
                    "takim": agent_team.get(a),
                    "vardiya": v,
                    "baslangic": saat[(ds, v)][0],
                    "bitis": saat[(ds, v)][1]
                })

roster_df = pd.DataFrame(roster_rows)

# Takım-gün bölünme kontrolü
team_day_split = (
    roster_df
    .groupby(["hafta", "tarih", "gun", "weekday", "takim"], as_index=False)
    .agg(
        calisan_sayi=("agent_user_code", "nunique"),
        vardiya_sayisi=("vardiya", "nunique")
    )
)

team_day_split["hafta_ici"] = team_day_split["weekday"].isin([0, 1, 2, 3, 4])

weekday_team_viol = team_day_split[
    (team_day_split["hafta_ici"]) &
    (team_day_split["vardiya_sayisi"] > 1)
]

weekend_team_split = team_day_split[
    (~team_day_split["hafta_ici"]) &
    (team_day_split["vardiya_sayisi"] > 1)
]

print("Hafta içi bölünen takım-gün sayısı:", len(weekday_team_viol))
print("Hafta sonu bölünen takım-gün sayısı:", len(weekend_team_split))

display(weekday_team_viol.head(20))
display(weekend_team_split.head(20))


# Coverage under/over kontrolü
coverage_rows = []

for ds in PLAN_GUNLER:
    for v in gun_vardiyalari.get(ds, []):
        assigned = sum(
            solver.Value(x[(a, ds, v)])
            for a in AGENTS
            if (a, ds, v) in x
        )

        req = int(talep[(ds, v)])

        coverage_rows.append({
            "tarih": str(ds),
            "gun": DAY_TR[pd.to_datetime(ds).weekday()],
            "hafta": day_week[ds],
            "vardiya": v,
            "baslangic": saat[(ds, v)][0],
            "bitis": saat[(ds, v)][1],
            "talep": req,
            "lower_10pct": coverage_lower[(ds, v)],
            "upper_10pct": coverage_upper[(ds, v)],
            "atanan": assigned,
            "gap": assigned - req,
            "under_buffer": solver.Value(under_buffer[(ds, v)]),
            "over_buffer": solver.Value(over_buffer[(ds, v)]),
            "buffer_ici": coverage_lower[(ds, v)] <= assigned <= coverage_upper[(ds, v)]
        })

coverage_for_excel = pd.DataFrame(coverage_rows)

print("Toplam under_buffer:", coverage_for_excel["under_buffer"].sum())
print("Toplam over_buffer:", coverage_for_excel["over_buffer"].sum())


# Mesai kontrolü
total_overtime = sum(
    solver.Value(overtime_week[(a, wk)])
    for a in AGENTS
    for wk in WEEKS
)

overtime_agent_count = sum(
    1
    for a in AGENTS
    if sum(solver.Value(overtime_week[(a, wk)]) for wk in WEEKS) > 0
)

print("Toplam mesai günü:", total_overtime)
print("Mesai yapan agent sayısı:", overtime_agent_count)
