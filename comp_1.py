# %% [HÜCRE] - GECE / AKŞAM VARDİYA HAFTASI DEĞİŞKENİ
# Kural:
# Agent ay içinde en fazla 2 hafta gece/akşam vardiyasında çalışabilir.
# Gece/akşam vardiyaları:
# 17:00-01:00, 18:00-02:00, 00:00-08:00

def normalize_time_str(t):
    """
    Saat değerini HH:MM formatına çevirir.
    Örn: '17:00:00' -> '17:00'
    """
    if pd.isna(t):
        return None

    t = str(t).strip()

    if len(t) >= 5:
        return t[:5]

    return t


NIGHT_SHIFT_WINDOWS = {
    ("17:00", "01:00"),
    ("18:00", "02:00"),
    ("00:00", "08:00")
}

night_shift_map = {}

for ds in PLAN_GUNLER:
    for v in gun_vardiyalari.get(ds, []):
        bas = normalize_time_str(saat[(ds, v)][0])
        bit = normalize_time_str(saat[(ds, v)][1])

        night_shift_map[(ds, v)] = (bas, bit) in NIGHT_SHIFT_WINDOWS


print("Gece/akşam vardiyası olan gün-vardiya sayısı:", sum(night_shift_map.values()))

# night_week[(a, wk)] = 1 ise agent o hafta en az 1 gece/akşam vardiyası almış demektir.
night_week = {}

for a in AGENTS:
    for wk in WEEKS:
        night_week[(a, wk)] = model.NewBoolVar(f"night_week_{a}_{wk}")



# %% [HÜCRE] - AYDA MAX 2 HAFTA GECE / AKŞAM VARDİYASI

MAX_NIGHT_WEEKS_PER_MONTH = 2

night_week_link_constraints = 0
night_week_limit_constraints = 0

for a in AGENTS:
    for wk in WEEKS:
        days_in_week = week_days[wk]

        night_vars_this_week = []

        for ds in days_in_week:
            for v in gun_vardiyalari.get(ds, []):

                if not night_shift_map.get((ds, v), False):
                    continue

                if (a, ds, v) in x:
                    night_vars_this_week.append(x[(a, ds, v)])

        if night_vars_this_week:
            # Eğer agent bu hafta herhangi bir gece/akşam vardiyası alırsa night_week = 1 olur
            for var in night_vars_this_week:
                model.Add(var <= night_week[(a, wk)])
                night_week_link_constraints += 1

            # Eğer hiç gece/akşam vardiyası almıyorsa night_week = 0 kalır
            model.Add(night_week[(a, wk)] <= sum(night_vars_this_week))
            night_week_link_constraints += 1

        else:
            model.Add(night_week[(a, wk)] == 0)
            night_week_link_constraints += 1

    # Ay içinde en fazla 2 hafta gece/akşam vardiyası
    model.Add(
        sum(night_week[(a, wk)] for wk in WEEKS)
        <= MAX_NIGHT_WEEKS_PER_MONTH
    )
    night_week_limit_constraints += 1


print("Gece/akşam hafta bağlantı kısıtı:", night_week_link_constraints)
print("Agent bazlı max 2 gece/akşam hafta kısıtı:", night_week_limit_constraints)



# %% KONTROL - AGENT BAZLI GECE / AKŞAM HAFTASI

night_week_rows = []

for a in AGENTS:
    for wk in WEEKS:
        night_week_rows.append({
            "agent_user_code": a,
            "hafta": wk,
            "night_week": solver.Value(night_week[(a, wk)])
        })

night_week_check = pd.DataFrame(night_week_rows)

night_week_summary = (
    night_week_check
    .groupby("agent_user_code", as_index=False)
    .agg(
        toplam_gece_aksam_haftasi=("night_week", "sum")
    )
)

night_week_summary["max_2_gece_aksam_haftasi_ok"] = (
    night_week_summary["toplam_gece_aksam_haftasi"] <= 2
)

viol_night_week = night_week_summary[
    night_week_summary["max_2_gece_aksam_haftasi_ok"] == False
]

print("2 haftadan fazla gece/akşam vardiyası alan agent sayısı:", len(viol_night_week))

display(
    night_week_summary
    .sort_values("toplam_gece_aksam_haftasi", ascending=False)
    .head(30)
)
