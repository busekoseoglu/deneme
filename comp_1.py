# %% [HÜCRE 16] - TAKIM HAFTALIK BASE VARDİYA
# Her takım her hafta için bir tane ana vardiya seçer.
# Agent çalıştığı gün takımının o haftaki base vardiyasında değilse exception açılır.

team_base_constraints = 0
exception_link_constraints = 0

# Her takım-her hafta için tek base vardiya
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


# Agent ataması takımın haftalık base vardiyasına bağlanır
for a in AGENTS:
    t = agent_team.get(a)

    if pd.isna(t) or t is None:
        continue

    t = str(t).strip()

    for ds in PLAN_GUNLER:
        wk = day_week[ds]

        for v in gun_vardiyalari.get(ds, []):
            if (a, ds, v) not in x:
                continue

            if (t, wk, v) in team_week_base:
                model.Add(
                    x[(a, ds, v)] <= team_week_base[(t, wk, v)] + exception[(a, ds)]
                )
                exception_link_constraints += 1
            else:
                # Eğer o vardiya o haftanın base seçeneklerinde yoksa,
                # bu vardiyada çalışmak direkt exception sayılır.
                model.Add(
                    x[(a, ds, v)] <= exception[(a, ds)]
                )
                exception_link_constraints += 1

print(f"takım-hafta tek base vardiya kısıtı: {team_base_constraints}")
print(f"base vardiya/exception bağlantı kısıtı: {exception_link_constraints}")
