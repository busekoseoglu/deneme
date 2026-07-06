# %% [HÜCRE] - OVERTIME WEEK DEĞİŞKENLERİ

overtime_week = {}

for a in AGENTS:
    a = str(a).strip()

    for wk in WEEKS:
        overtime_week[(a, wk)] = model.NewIntVar(
            0,
            MAX_OVERTIME_PER_WEEK,
            f"overtime_week_{a}_{wk}"
        )

print("Overtime week değişken sayısı:", len(overtime_week))
print("Haftalık max mesai:", MAX_OVERTIME_PER_WEEK)
print("Aylık max mesai:", MAX_OVERTIME_PER_MONTH)

print("Weekly under toplam:", sum(
    solver.Value(v)
    for v in weekly_under.values()
))

print("Weekly over toplam:", sum(
    solver.Value(v)
    for v in weekly_over.values()
))

print("Toplam mesai günü:", sum(
    solver.Value(v)
    for v in overtime_week.values()
))

print("2 mesai yazılan agent-week sayısı:", sum(
    1
    for v in overtime_week.values()
    if solver.Value(v) == 2
))
