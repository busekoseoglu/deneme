# %% [HÜCRE 12] - HAFTADA MAX 5 ÇALIŞMA GÜNÜ
# Agent bir haftada en fazla 5 gün çalışsın.
# İzin günleri zaten work=0 olduğu için ayrıca düşmeye gerek yok.

weekly_work_constraints = 0
MAX_WORK_DAYS_PER_WEEK = 5

week_days = defaultdict(list)

for ds in PLAN_GUNLER:
    week_days[day_week[ds]].append(ds)

for a in AGENTS:
    for wk, days_in_week in week_days.items():
        model.Add(
            sum(work[(a, ds)] for ds in days_in_week) <= MAX_WORK_DAYS_PER_WEEK
        )
        weekly_work_constraints += 1

print(f"haftada max {MAX_WORK_DAYS_PER_WEEK} gün çalışma kısıtı: {weekly_work_constraints}")
