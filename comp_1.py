# %% [HÜCRE] - AGENT HAFTA BOYUNCA AYNI VARDİYADA KALSIN
# HARD CONSTRAINT - daha güvenli versiyon

agent_week_same_shift_constraints = 0
agent_week_pattern_choice_constraints = 0
skipped_agent_weeks = 0

def get_week_key(ds):
    d = pd.to_datetime(ds)
    iso = d.isocalendar()
    return f"{iso.year}-W{str(iso.week).zfill(2)}"


def get_shift_pattern(ds, v):
    bas, bit = saat[(ds, v)]
    return f"{bas}-{bit}"


week_days = {}

for ds in PLAN_GUNLER:
    wk = get_week_key(ds)
    week_days.setdefault(wk, []).append(ds)


for a in AGENTS:
    for wk, days in week_days.items():

        pattern_to_vars = {}
        all_week_vars = []

        for ds in days:
            for v in gun_vardiyalari.get(ds, []):
                if (a, ds, v) not in x:
                    continue

                p = get_shift_pattern(ds, v)

                pattern_to_vars.setdefault(p, []).append(x[(a, ds, v)])
                all_week_vars.append(x[(a, ds, v)])

        if not all_week_vars:
            continue

        # Bu agent-week için pattern değişkenleri
        pattern_vars = {}

        for p in pattern_to_vars.keys():
            p_name = p.replace(":", "").replace("-", "_")

            pattern_vars[p] = model.NewBoolVar(
                f"agent_week_pattern_{a}_{wk}_{p_name}"
            )

        # Agent o hafta çalışıyorsa sadece 1 pattern seçsin
        # Haftalık 5 gün kısıtı zaten çalışmayı zorladığı için burada 1 pattern seçiyoruz.
        model.Add(sum(pattern_vars.values()) == 1)
        agent_week_pattern_choice_constraints += 1

        # Seçilmeyen pattern'deki vardiyalar alınamaz
        for p, vars_p in pattern_to_vars.items():
            for var in vars_p:
                model.Add(var <= pattern_vars[p])
                agent_week_same_shift_constraints += 1

print("agent-week pattern seçim kısıtı:", agent_week_pattern_choice_constraints)
print("agent hafta boyunca aynı vardiya hard kısıtı:", agent_week_same_shift_constraints)
