# %% [HÜCRE] - TAKIM HAFTA BOYUNCA AYNI VARDİYADA KALSIN OBJECTIVE

# Bu hücre, günlük takım bölünmesin objective'inden SONRA çalışmalı.
# objective_terms sıfırlanmıyor, üstüne ekleniyor.

import re

WEEK_SHIFT_CHANGE_PENALTY = 5000

team_col = "takim"

def safe_name(x):
    return re.sub(r"[^A-Za-z0-9_]", "_", str(x))


def get_week_key(ds):
    d = pd.to_datetime(ds)
    iso = d.isocalendar()
    return f"{iso.year}-W{str(iso.week).zfill(2)}"


def get_shift_pattern(ds, v):
    bas, bit = saat[(ds, v)]
    return f"{bas}-{bit}"


# Haftalık gün listesi
week_days = {}

for ds in PLAN_GUNLER:
    wk = get_week_key(ds)
    week_days.setdefault(wk, []).append(ds)


weekly_objective_terms = []

team_week_main = {}
weekly_change_var_count = 0
team_week_count = 0


for team, members in team_members.items():
    team_name = safe_name(team)

    for wk, days in week_days.items():
        wk_name = safe_name(wk)

        # Bu team-week için günlük main pattern var mı?
        active_day_patterns = [
            (ds, p)
            for ds in days
            for p in all_patterns
            if (team, ds, p) in team_day_main
        ]

        if not active_day_patterns:
            continue

        # Haftalık ana vardiya seç
        week_main_vars = []

        for p in all_patterns:
            p_name = safe_name(p)

            week_main = model.NewBoolVar(
                f"week_main_{team_name}_{wk_name}_{p_name}"
            )

            team_week_main[(team, wk, p)] = week_main
            week_main_vars.append(week_main)

        # Her team-week için 1 haftalık ana vardiya seçilsin
        model.Add(sum(week_main_vars) == 1)
        team_week_count += 1

        # O haftadaki günlük ana vardiya haftalık ana vardiyadan farklıysa ceza
        for ds in days:
            ds_name = safe_name(ds)

            for p in all_patterns:
                if (team, ds, p) not in team_day_main:
                    continue

                p_name = safe_name(p)

                week_change = model.NewBoolVar(
                    f"week_change_{team_name}_{wk_name}_{ds_name}_{p_name}"
                )

                # week_change = 1 olması için:
                # günlük main vardiya p seçilmiş ama haftalık main p değil
                model.Add(week_change >= team_day_main[(team, ds, p)] - team_week_main[(team, wk, p)])
                model.Add(week_change <= team_day_main[(team, ds, p)])
                model.Add(week_change <= 1 - team_week_main[(team, wk, p)])

                weekly_objective_terms.append(WEEK_SHIFT_CHANGE_PENALTY * week_change)
                weekly_change_var_count += 1


objective_terms.extend(weekly_objective_terms)

print("team-week sayısı:", team_week_count)
print("weekly change değişkeni:", weekly_change_var_count)
print("weekly objective term:", len(weekly_objective_terms))
print("toplam objective term:", len(objective_terms))
