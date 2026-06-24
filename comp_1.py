# %% [HÜCRE] - TAKIM GÜNLÜK + HAFTALIK BASİT OBJECTIVE

objective_terms = []

team_col = "takim"

DAY_NORMAL_SPLIT_PENALTY = 10000
DAY_SPECIAL_SPLIT_PENALTY = 300
WEEK_SHIFT_CHANGE_PENALTY = 3000


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


df_team = df_tam.copy()
df_team["agent_user_code"] = df_team["agent_user_code"].astype(str).str.strip()

agent_special = {
    row["agent_user_code"]: is_special_agent(row)
    for _, row in df_team.iterrows()
}

team_members = (
    df_team
    .groupby(team_col)["agent_user_code"]
    .apply(list)
    .to_dict()
)

# Tüm vardiya saat pattern'leri
all_patterns = sorted({
    get_shift_pattern(ds, v)
    for ds in PLAN_GUNLER
    for v in gun_vardiyalari.get(ds, [])
})

# Günlük ana vardiya değişkenleri
team_day_main = {}

for team, members in team_members.items():
    for ds in PLAN_GUNLER:

        day_work_vars = [
            x[(a, ds, v)]
            for a in members
            for v in gun_vardiyalari.get(ds, [])
            if (a, ds, v) in x
        ]

        if not day_work_vars:
            continue

        # takım o gün çalışıyor mu?
        team_works_day = model.NewBoolVar(f"team_works_{team}_{ds}")

        for var in day_work_vars:
            model.Add(team_works_day >= var)

        model.Add(team_works_day <= sum(day_work_vars))

        # o gün bir ana vardiya seç
        main_vars = []

        for p in all_patterns:
            main = model.NewBoolVar(f"main_{team}_{ds}_{p}")
            team_day_main[(team, ds, p)] = main
            main_vars.append(main)

        model.Add(sum(main_vars) == team_works_day)

        # agent ana vardiya dışında çalışırsa ceza
        for a in members:
            penalty = DAY_SPECIAL_SPLIT_PENALTY if agent_special.get(a, False) else DAY_NORMAL_SPLIT_PENALTY

            for v in gun_vardiyalari.get(ds, []):
                if (a, ds, v) not in x:
                    continue

                p = get_shift_pattern(ds, v)

                split = model.NewBoolVar(f"split_{a}_{ds}_{v}")

                model.Add(split >= x[(a, ds, v)] - team_day_main[(team, ds, p)])
                model.Add(split <= x[(a, ds, v)])
                model.Add(split <= 1 - team_day_main[(team, ds, p)])

                objective_terms.append(penalty * split)
