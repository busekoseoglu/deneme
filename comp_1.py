# %% [HÜCRE 16] - TAKIM HAFTALIK BASE VARDİYA - HARD
# Her takım-her hafta için bir tane ana vardiya seçer.
# Takımdaki herkes o hafta çalıştığı günlerde sadece bu base vardiyada çalışabilir.
# Böylece aynı gün takımın farklı vardiyalara bölünmesi engellenir.

team_base_constraints = 0
team_hard_link_constraints = 0

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


# Agent sadece takımının haftalık base vardiyasında çalışabilir
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

            # HARD bağlantı:
            # team_week_base[(t, wk, v)] = 1 ise bu vardiya takımın base vardiyasıdır.
            # 0 ise agent bu vardiyaya atanamaz.
            model.Add(
                x[(a, ds, v)] <= team_week_base[(t, wk, v)]
            )

            team_hard_link_constraints += 1

print(f"takım-hafta tek base vardiya kısıtı: {team_base_constraints}")
print(f"takım hard base bağlantı kısıtı: {team_hard_link_constraints}")
