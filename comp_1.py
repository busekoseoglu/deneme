# %% [HÜCRE] - TAKIM GÜNLÜK + HAFTALIK AYNI VARDİYA OBJECTIVE

import re

# Eski objective kalmasın diye sıfırdan başlatıyoruz
objective_terms = []

team_col = "takim"

# Ceza ağırlıkları
# Gün içinde normal ekip bölünmesin diye en yüksek ceza burada
DAY_NORMAL_SPLIT_PENALTY = 10000

# Özel durumlu kişi ayrılırsa daha düşük ceza
DAY_SPECIAL_SPLIT_PENALTY = 300

# Aynı takım hafta içinde ana vardiya değiştirirse ceza
WEEK_SHIFT_CHANGE_PENALTY = 5000

# Bir team-day içinde ekstra vardiya pattern'i kullanılırsa ceza
EXTRA_DAY_PATTERN_PENALTY = 3000

# Eğer normal ekip üyeleri kesinlikle aynı gün aynı vardiyada olsun istersen True yap.
# İlk denemede False bırakmak daha güvenli. Infeasible riskini azaltır.
FORCE_NORMAL_TEAM_SAME_SHIFT_PER_DAY = False


def safe_name(x):
    return re.sub(r"[^A-Za-z0-9_]", "_", str(x))


def get_week_key(ds):
    d = pd.to_datetime(ds)
    iso = d.isocalendar()
    return f"{iso.year}_W{str(iso.week).zfill(2)}"


def get_shift_pattern(ds, v):
    bas, bit = saat[(ds, v)]
    return f"{bas}-{bit}"


def is_special_agent(row):
    return (
        int(row.get("sabah_calisir_flg", 0)) == 1
        or int(row.get("hamile_flg", 0)) == 1
        or int(row.get("sut_izni_flg", 0)) == 1
    )


# Agent bilgileri
df_agent_team = df_tam.copy()
df_agent_team["agent_user_code"] = df_agent_team["agent_user_code"].astype(str).str.strip()

agent_special = {
    str(row["agent_user_code"]).strip(): is_special_agent(row)
    for _, row in df_agent_team.iterrows()
}

team_members = (
    df_agent_team
    .groupby(team_col)["agent_user_code"]
    .apply(lambda x: [str(a).strip() for a in x])
    .to_dict()
)

# Haftalar
week_days = {}
for ds in PLAN_GUNLER:
    wk = get_week_key(ds)
    week_days.setdefault(wk, []).append(ds)


# Yardımcı değişkenler
team_day_main_pattern = {}
team_day_work = {}
team_day_pattern_used = {}

team_week_main_pattern = {}
team_week_work = {}

daily_split_var_count = 0
weekly_change_var_count = 0
team_day_count = 0
team_week_count = 0


# 1) TEAM + GÜN: O gün için ana vardiya seç
for team, members in team_members.items():
    team_name = safe_name(team)

    for ds in PLAN_GUNLER:
        ds_name = safe_name(ds)

        day_vars = [
            x[(a, ds, v)]
            for a in members
            for v in gun_vardiyalari.get(ds, [])
            if (a, ds, v) in x
        ]

        if not day_vars:
            continue

        # Team o gün çalışıyor mu?
        work_day = model.NewBoolVar(f"work_day_{team_name}_{ds_name}")
        team_day_work[(team, ds)] = work_day

        for var in day_vars:
            model.Add(work_day >= var)

        model.Add(work_day <= sum(day_vars))

        patterns = sorted({
            get_shift_pattern(ds, v)
            for v in gun_vardiyalari.get(ds, [])
        })

        main_vars_for_day = []

        for p in patterns:
            p_name = safe_name(p)

            pattern_assignments = [
                x[(a, ds, v)]
                for a in members
                for v in gun_vardiyalari.get(ds, [])
                if (a, ds, v) in x and get_shift_pattern(ds, v) == p
            ]

            pattern_used = model.NewBoolVar(
                f"pattern_used_day_{team_name}_{ds_name}_{p_name}"
            )

            main_pattern = model.NewBoolVar(
                f"main_pattern_day_{team_name}_{ds_name}_{p_name}"
            )

            team_day_pattern_used[(team, ds, p)] = pattern_used
            team_day_main_pattern[(team, ds, p)] = main_pattern
            main_vars_for_day.append(main_pattern)

            if pattern_assignments:
                for var in pattern_assignments:
                    model.Add(pattern_used >= var)

                model.Add(pattern_used <= sum(pattern_assignments))
            else:
                model.Add(pattern_used == 0)

            # Ana vardiya, gerçekten kullanılan vardiyalardan biri olsun
            model.Add(main_pattern <= pattern_used)

            # Ana vardiya dışındaki ekstra pattern kullanımı ceza alsın
            extra_pattern = model.NewBoolVar(
                f"extra_pattern_day_{team_name}_{ds_name}_{p_name}"
            )

            model.Add(extra_pattern <= pattern_used)
            model.Add(extra_pattern <= 1 - main_pattern)
            model.Add(extra_pattern >= pattern_used - main_pattern)

            objective_terms.append(EXTRA_DAY_PATTERN_PENALTY * extra_pattern)

        # Team o gün çalışıyorsa 1 ana vardiya seçsin
        model.Add(sum(main_vars_for_day) == work_day)
        team_day_count += 1

        # Agent ana vardiya dışına çıkarsa ceza yaz
        for a in members:
            penalty = (
                DAY_SPECIAL_SPLIT_PENALTY
                if agent_special.get(a, False)
                else DAY_NORMAL_SPLIT_PENALTY
            )

            for v in gun_vardiyalari.get(ds, []):
                if (a, ds, v) not in x:
                    continue

                p = get_shift_pattern(ds, v)
                p_name = safe_name(p)

                split_var = model.NewBoolVar(
                    f"split_day_{a}_{team_name}_{ds_name}_{p_name}"
                )

                model.Add(split_var <= x[(a, ds, v)])
                model.Add(split_var <= 1 - team_day_main_pattern[(team, ds, p)])
                model.Add(split_var >= x[(a, ds, v)] - team_day_main_pattern[(team, ds, p)])

                # Normal kişiler için istersen hard yapabiliriz
                if FORCE_NORMAL_TEAM_SAME_SHIFT_PER_DAY and not agent_special.get(a, False):
                    model.Add(split_var == 0)

                objective_terms.append(penalty * split_var)
                daily_split_var_count += 1


# 2) TEAM + HAFTA: Haftanın ana vardiyası seçilsin
for team, members in team_members.items():
    team_name = safe_name(team)

    for wk, days in week_days.items():
        wk_name = safe_name(wk)

        week_day_work_vars = [
            team_day_work[(team, ds)]
            for ds in days
            if (team, ds) in team_day_work
        ]

        if not week_day_work_vars:
            continue

        work_week = model.NewBoolVar(f"work_week_{team_name}_{wk_name}")
        team_week_work[(team, wk)] = work_week

        for var in week_day_work_vars:
            model.Add(work_week >= var)

        model.Add(work_week <= sum(week_day_work_vars))

        patterns = sorted({
            get_shift_pattern(ds, v)
            for ds in days
            for v in gun_vardiyalari.get(ds, [])
        })

        week_main_vars = []

        for p in patterns:
            p_name = safe_name(p)

            week_main = model.NewBoolVar(
                f"main_pattern_week_{team_name}_{wk_name}_{p_name}"
            )

            team_week_main_pattern[(team, wk, p)] = week_main
            week_main_vars.append(week_main)

        # Team o hafta çalışıyorsa 1 haftalık ana vardiya seçsin
        model.Add(sum(week_main_vars) == work_week)
        team_week_count += 1

        # Günlük ana vardiya, haftalık ana vardiyadan farklıysa ceza
        for ds in days:
            if (team, ds) not in team_day_work:
                continue

            for p in patterns:
                if (team, ds, p) not in team_day_main_pattern:
                    continue

                change_var = model.NewBoolVar(
                    f"week_change_{team_name}_{wk_name}_{safe_name(ds)}_{safe_name(p)}"
                )

                model.Add(change_var <= team_day_main_pattern[(team, ds, p)])
                model.Add(change_var <= 1 - team_week_main_pattern[(team, wk, p)])
                model.Add(change_var >= team_day_main_pattern[(team, ds, p)] - team_week_main_pattern[(team, wk, p)])

                objective_terms.append(WEEK_SHIFT_CHANGE_PENALTY * change_var)
                weekly_change_var_count += 1


print("team-day sayısı:", team_day_count)
print("team-week sayısı:", team_week_count)
print("daily split değişkeni:", daily_split_var_count)
print("weekly shift change değişkeni:", weekly_change_var_count)
print("toplam objective term:", len(objective_terms))
