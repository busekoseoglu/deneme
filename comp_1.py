# %% [HÜCRE] - AGENT HAFTADA 5 GÜN TEK VARDİYA PATTERN'İNDE ÇALIŞSIN

from collections import defaultdict
import re

WEEKLY_WORK_DAYS = 5

def safe_name(x):
    return re.sub(r"[^A-Za-z0-9_]", "_", str(x))


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


agent_week_pattern = {}
agent_week_pattern_constraints = 0
agent_week_assignment_constraints = 0

for a in AGENTS:
    a = str(a).strip()

    for wk, days in week_days.items():

        pattern_to_day_vars = defaultdict(list)
        all_week_vars = []

        for ds in days:
            for v in gun_vardiyalari.get(ds, []):

                if (a, ds, v) not in x:
                    continue

                p = get_shift_pattern(ds, v)

                pattern_to_day_vars[p].append(x[(a, ds, v)])
                all_week_vars.append(x[(a, ds, v)])

        if not all_week_vars:
            continue

        required_work_days = min(WEEKLY_WORK_DAYS, len(days))

        pattern_vars = {}

        for p in pattern_to_day_vars.keys():
            pv = model.NewBoolVar(
                f"agent_week_pattern_{safe_name(a)}_{safe_name(wk)}_{safe_name(p)}"
            )

            pattern_vars[p] = pv
            agent_week_pattern[(a, wk, p)] = pv

        # Agent o hafta sadece 1 ana vardiya pattern'i seçsin
        model.Add(sum(pattern_vars.values()) == 1)
        agent_week_pattern_constraints += 1

        # Agent o hafta 5 gün çalışsın
        model.Add(sum(all_week_vars) == required_work_days)

        # Seçilmeyen pattern'de çalışamaz
        for p, vars_p in pattern_to_day_vars.items():
            for var in vars_p:
                model.Add(var <= pattern_vars[p])
                agent_week_assignment_constraints += 1

print("agent-week pattern seçim:", agent_week_pattern_constraints)
print("agent-week pattern assignment kısıtı:", agent_week_assignment_constraints)
