# %% [HÜCRE] - WEEK KEY / WEEK DAYS HELPER
# Amaç:
# PLAN_GUNLER listesindeki her günü ISO hafta bilgisine bağlamak.
#
# Bu hücre:
# - day_week: gün -> hafta eşleşmesi
# - week_days: hafta -> o haftadaki plan günleri
# - WEEKS: plan ayındaki hafta listesi
#
# üretir.
#
# Bu değişkenler daha sonra:
# - weekly target
# - partial week helper
# - max 6 gün üst üste
# - ekip haftalık base vardiya
# gibi haftalık kurallarda kullanılır.

day_week = {}
week_days = {}

for ds in PLAN_GUNLER:
    dt = pd.to_datetime(ds)
    wk = f"{dt.isocalendar().year}-W{dt.isocalendar().week:02d}"

    day_week[ds] = wk

    if wk not in week_days:
        week_days[wk] = []

    week_days[wk].append(ds)

WEEKS = sorted(week_days.keys())

print("Week helper oluşturuldu.")
print("Hafta sayısı:", len(WEEKS))
print("WEEKS:", WEEKS)
