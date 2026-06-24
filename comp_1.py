# %% [HÜCRE 16] - TEAM HAFTALIK AYNI VARDİYA OBJECTIVE
# Her team + hafta için bir ana vardiya pattern'i seçilir.
# Ekip üyeleri o hafta çalıştıkları günlerde mümkün olduğunca bu pattern'de tutulur.

objective_terms = []

NORMAL_SPLIT_PENALTY = 500
SPECIAL_SPLIT_PENALTY = 50
EXTRA_TEAM_PATTERN_PENALTY = 200


def get_week_key(ds):
    d = pd.to_datetime(ds)
    iso = d.isocalendar()
    return f"{iso.year}-W{str(iso.week).zfill(2)}"


def get_shift_pattern(ds, v):
    bas, bit = saat[(ds, v)]
    return f"{bas}-{bit}"


def is_special_agent(row):
    return (
        int(row.get("sabah_calisir_flg", 0)) == 1
        or int(row.get("hamile_flg", 0)) == 1
        or int(row.get("sut_izni_flg", 0)) == 1
    )


# agent -> team
agent_team = {
    str(row["agent_user_code"]).strip(): row["team"]
    for _, row in df_tam.iterrows()
}

# agent -> özel durum flag
agent_special = {
    str(row["agent_user_code"]).strip(): is_special_agent(row)
    for _, row in df_tam.iterrows()
}

# team -> agent listesi
team_members = (
    df_tam
    .assign(agent_user_code=df_tam["agent_user_code"].astype(str).str.strip())
    .groupby("team")["agent_user_code"]
    .apply(list)
    .to_dict()
)

# week -> günler
week_days = {}

for ds in PLAN_GUNLER:
    wk = get_week_key(ds)
    week_days.setdefault(wk, []).append(ds)


team_week_main_pattern_constraints = 0
team_week_split_penalties = 0
team_week_extra_pattern_penalties = 0

for team, members in team_members.items():
    team_name = str(team).replace(" ", "_").replace("|", "_")

    for wk, days in week_days.items():
        wk_name = wk.replace("-", "_")

        # Bu team bu hafta çalışabilecek mi?
        team_week_vars = [
            x[a, ds, v]
            for a in members
            for ds in days
            for v in gun_vardiyalari.get(ds, [])
            if (a, ds, v) in x
        ]

        if not team_week_vars:
            continue

        # Bu hafta var olan vardiya pattern'leri
        patterns = sorted({
            get_shift_pattern(ds, v)
            for ds in days
            for v in gun_vardiyalari.get(ds, [])
        })

        # Team bu hafta çalışıyor mu?
        team_work_week = model.NewBoolVar(
            f"team_work_week_{team_name}_{wk_name}"
        )

        for var in team_week_vars:
            model.Add(team_work_week >= var)

        model.Add(team_work_week <= sum(team_week_vars))

        main_pattern_vars = {}
        pattern_used_vars = {}

        for p in patterns:
            p_name = p.replace(":", "").replace("-", "_")

            # Bu pattern bu team tarafından bu hafta kullanıldı mı?
            pattern_assignments = [
                x[a, ds, v]
                for a in members
                for ds in days
                for v in gun_vardiyalari.get(ds, [])
                if (a, ds, v) in x and get_shift_pattern(ds, v) == p
            ]

            pattern_used = model.NewBoolVar(
                f"pattern_used_{team_name}_{wk_name}_{p_name}"
            )

            main_pattern = model.NewBoolVar(
                f"main_pattern_{team_name}_{wk_name}_{p_name}"
            )

            pattern_used_vars[p] = pattern_used
            main_pattern_vars[p] = main_pattern

            if pattern_assignments:
                for var in pattern_assignments:
                    model.Add(pattern_used >= var)

                model.Add(pattern_used <= sum(pattern_assignments))
            else:
                model.Add(pattern_used == 0)

            # Ana pattern sadece kullanılmış pattern olabilir
            model.Add(main_pattern <= pattern_used)

        # Team o hafta çalışıyorsa 1 ana pattern seçilsin
        model.Add(sum(main_pattern_vars.values()) == team_work_week)
        team_week_main_pattern_constraints += 1

        # Ana pattern dışındaki pattern kullanımları ceza alsın
        for p in patterns:
            extra_pattern = model.NewBoolVar(
                f"extra_pattern_{team_name}_{wk_name}_{p.replace(':','').replace('-','_')}"
            )

            model.Add(extra_pattern <= pattern_used_vars[p])
            model.Add(extra_pattern <= 1 - main_pattern_vars[p])
            model.Add(extra_pattern >= pattern_used_vars[p] - main_pattern_vars[p])

            objective_terms.append(EXTRA_TEAM_PATTERN_PENALTY * extra_pattern)
            team_week_extra_pattern_penalties += 1

        # Agent ana pattern dışına çıkarsa ceza alsın
        for a in members:
            penalty = SPECIAL_SPLIT_PENALTY if agent_special.get(a, False) else NORMAL_SPLIT_PENALTY

            for ds in days:
                for v in gun_vardiyalari.get(ds, []):
                    if (a, ds, v) not in x:
                        continue

                    p = get_shift_pattern(ds, v)

                    split_var = model.NewBoolVar(
                        f"split_{a}_{team_name}_{wk_name}_{p.replace(':','').replace('-','_')}_{ds}_{v}"
                    )

                    model.Add(split_var <= x[a, ds, v])
                    model.Add(split_var <= 1 - main_pattern_vars[p])
                    model.Add(split_var >= x[a, ds, v] - main_pattern_vars[p])

                    objective_terms.append(penalty * split_var)
                    team_week_split_penalties += 1


print(f"team-week ana pattern kısıtı: {team_week_main_pattern_constraints}")
print(f"team-week split penalty değişkeni: {team_week_split_penalties}")
print(f"team-week extra pattern penalty değişkeni: {team_week_extra_pattern_penalties}")
print(f"toplam objective term: {len(objective_terms)}")
