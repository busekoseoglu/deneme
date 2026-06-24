# %% [HÜCRE] - WEEK + PATTERN İÇİN YETERLİ AGENT PATTERN SEÇSİN

pattern_capacity_constraints = 0

for wk, days in week_days.items():

    patterns = sorted({
        get_shift_pattern(ds, v)
        for ds in days
        for v in gun_vardiyalari.get(ds, [])
    })

    for p in patterns:

        total_required = 0

        for ds in days:
            for v in gun_vardiyalari.get(ds, []):
                if get_shift_pattern(ds, v) == p:
                    total_required += int(talep[(ds, v)])

        required_agent_count = int((total_required + WEEKLY_WORK_DAYS - 1) // WEEKLY_WORK_DAYS)

        pattern_agent_vars = [
            agent_week_pattern[(str(a).strip(), wk, p)]
            for a in AGENTS
            if (str(a).strip(), wk, p) in agent_week_pattern
        ]

        if pattern_agent_vars:
            model.Add(sum(pattern_agent_vars) >= required_agent_count)
            pattern_capacity_constraints += 1

print("week-pattern yeterli agent seçimi kısıtı:", pattern_capacity_constraints)
