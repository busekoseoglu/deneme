weekday_team_rows = []
weekend_team_rows = []

for ds in PLAN_GUNLER:

    # Arife / resmi tatil özel planlanıyor, takım base kontrolünden hariç
    if "ozel_tatil_plan_gunleri" in globals() and ds in ozel_tatil_plan_gunleri:
        continue

    weekday = pd.to_datetime(ds).weekday()

    for t in TAKIMLAR:
        t = str(t).strip()

        team_agents = [
            str(a).strip()
            for a in AGENTS
            if str(agent_team.get(str(a).strip(), "")).strip() == t
        ]

        çalışan_shiftler = []

        for a in team_agents:
            for v in gun_vardiyalari.get(ds, []):
                if (a, ds, v) in x and solver.Value(x[(a, ds, v)]) == 1:
                    çalışan_shiftler.append(v)

        if not çalışan_shiftler:
            continue

        vardiya_sayisi = len(set(çalışan_shiftler))
        calisan_agent = len(çalışan_shiftler)

        row = {
            "hafta": day_week[ds],
            "tarih": ds,
            "gun": pd.to_datetime(ds).day_name(),
            "weekday": weekday,
            "hafta_ici": weekday in [0, 1, 2, 3, 4],
            "takim": t,
            "calisan_agent": calisan_agent,
            "vardiya_sayisi": vardiya_sayisi,
        }

        if weekday in [0, 1, 2, 3, 4]:
            if vardiya_sayisi > 1:
                weekday_team_rows.append(row)
        else:
            if vardiya_sayisi > 1:
                weekend_team_rows.append(row)

weekday_team_viol = pd.DataFrame(weekday_team_rows)
weekend_team_split = pd.DataFrame(weekend_team_rows)

print("Özel günler hariç hafta içi bölünen takım-gün sayısı:", len(weekday_team_viol))
print("Hafta sonu bölünen takım-gün sayısı:", len(weekend_team_split))

if len(weekday_team_viol) > 0:
    display(
        weekday_team_viol
        .sort_values(["hafta", "tarih", "takim"])
        .head(100)
    )