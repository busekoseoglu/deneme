# %% [HÜCRE 11] - GÜNDE MAX 1 VARDİYA + WORK BAĞLANTISI
# Bir agent bir günde ya hiç çalışmaz ya da tek vardiyada çalışır.
# work[a, ds] = o gün seçilen vardiya toplamı

daily_one_shift_constraints = 0

for a in AGENTS:
    for ds in PLAN_GUNLER:
        vars_day = [
            x[(a, ds, v)]
            for v in gun_vardiyalari.get(ds, [])
            if (a, ds, v) in x
        ]

        if vars_day:
            model.Add(sum(vars_day) == work[(a, ds)])
        else:
            model.Add(work[(a, ds)] == 0)

        daily_one_shift_constraints += 1

print(f"günde max 1 vardiya/work kısıtı: {daily_one_shift_constraints} agent-gün")
