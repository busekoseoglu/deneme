# %% [KARAR DEĞİŞKENİ] - GÜNLÜK VARDİYA ATAMALARI

x = {}

for a_raw in AGENTS:

    a = str(a_raw).strip()

    for ds in PLAN_GUNLER:

        for v in gun_vardiyalari.get(ds, []):

            x[(a, ds, v)] = model.NewBoolVar(
                f"x_{a}_{pd.to_datetime(ds).strftime('%Y%m%d')}_{v}"
            )


print("x karar değişkeni sayısı:", len(x))



# %% [KISIT / DEBUG] - HARD OFF GÜNLERİ

# izin:
#     her zaman hard
#
# off_t2:
#     her zaman hard
#
# off_t:
#     ENABLE_OFF_T_HARD=True ise hard
#
# Her hard OFF gününde work=0 zorunludur.

hard_off_assumption = {}
hard_off_assumption_index_map = {}
hard_off_debug_rows = []

for a_raw in AGENTS:

    a = str(a_raw).strip()

    izin_dates = {
        pd.to_datetime(d).date()
        for d in izin_map.get(a, set())
    }

    off_t2_dates = {
        pd.to_datetime(d).date()
        for d in off_t2_map.get(a, set())
    }

    off_t_dates = {
        pd.to_datetime(d).date()
        for d in off_t_map.get(a, set())
    }

    agent_hard_off_dates = {
        pd.to_datetime(d).date()
        for d in hard_off_map.get(a, set())
    }

    for ds in PLAN_GUNLER:

        ds_date = pd.to_datetime(ds).date()

        if ds_date not in agent_hard_off_dates:
            continue

        assumption_var = model.NewBoolVar(
            f"assumption_hard_off_{a}_{ds_date.strftime('%Y%m%d')}"
        )

        # Hard OFF günü kişi kesinlikle çalışamaz
        model.Add(
            work[(a, ds)] == 0
        ).OnlyEnforceIf(
            assumption_var
        )

        model.AddAssumption(
            assumption_var
        )

        hard_off_assumption[(a, ds)] = assumption_var

        hard_off_assumption_index_map[
            assumption_var.Index()
        ] = {
            "agent_user_code": a,
            "date": ds_date,
        }

        if ds_date in izin_dates:
            off_type = "izin"
        elif ds_date in off_t2_dates:
            off_type = "off_t2"
        elif ds_date in off_t_dates:
            off_type = "off_t"
        else:
            off_type = "diger_hard_off"

        hard_off_debug_rows.append({
            "agent_user_code": a,
            "date": ds_date,
            "week": day_week.get(ds),
            "weekday": pd.to_datetime(ds).weekday(),
            "off_type": off_type,
        })


hard_off_debug_df = pd.DataFrame(
    hard_off_debug_rows
)

print(
    "Hard OFF assumption sayısı:",
    len(hard_off_assumption)
)

print(
    hard_off_debug_df["off_type"].value_counts(
        dropna=False
    )
)



# %% [SOLVE / DEBUG] - HARD OFF ÇAKIŞMA TESPİTİ

status = solver.Solve(model)

print(
    "Solver status:",
    solver.StatusName(status)
)

if status == cp_model.INFEASIBLE:

    core_literals = (
        solver.SufficientAssumptionsForInfeasibility()
    )

    hard_off_core_rows = []
    haftalik_core_rows = []
    eslesmeyen_literal_sayisi = 0

    for literal_raw in core_literals:

        literal = int(literal_raw)

        if literal >= 0:
            variable_index = literal
        else:
            variable_index = -literal - 1

        # Hard OFF assumption
        if variable_index in hard_off_assumption_index_map:

            hard_off_core_rows.append(
                hard_off_assumption_index_map[
                    variable_index
                ]
            )

        # Önceki haftalık debug assumption'ları hâlâ varsa
        elif (
            "haftalik_assumption_index_map" in globals()
            and variable_index
            in haftalik_assumption_index_map
        ):

            haftalik_core_rows.append(
                haftalik_assumption_index_map[
                    variable_index
                ]
            )

        else:
            eslesmeyen_literal_sayisi += 1


    hard_off_infeasible_core_df = pd.DataFrame(
        hard_off_core_rows
    )

    if not hard_off_infeasible_core_df.empty:

        hard_off_infeasible_core_df = (
            hard_off_infeasible_core_df
            .drop_duplicates()
            .merge(
                hard_off_debug_df,
                on=[
                    "agent_user_code",
                    "date",
                ],
                how="left",
            )
            .sort_values(
                [
                    "agent_user_code",
                    "date",
                ]
            )
            .reset_index(drop=True)
        )


    haftalik_infeasible_core_df = pd.DataFrame(
        haftalik_core_rows
    )

    if not haftalik_infeasible_core_df.empty:

        haftalik_infeasible_core_df = (
            haftalik_infeasible_core_df
            .drop_duplicates()
            .sort_values(
                [
                    "agent_user_code",
                    "week",
                    "grup",
                ]
            )
            .reset_index(drop=True)
        )


    print(
        "Toplam infeasible core literal:",
        len(core_literals)
    )

    print(
        "Çakışan hard OFF günü:",
        len(hard_off_infeasible_core_df)
    )

    print(
        "Çakışan haftalık debug kaydı:",
        len(haftalik_infeasible_core_df)
    )

    print(
        "Eşleşmeyen assumption literal:",
        eslesmeyen_literal_sayisi
    )


    print("\nHARD OFF ÇAKIŞMALARI")

    display(
        hard_off_infeasible_core_df
    )


    if not haftalik_infeasible_core_df.empty:

        print("\nHAFTALIK BLOK ÇAKIŞMALARI")

        display(
            haftalik_infeasible_core_df
        )


    if hard_off_infeasible_core_df.empty:

        print(
            "Infeasible core içinde hard OFF günü bulunmadı."
        )

        print(
            "Bu durumda sorun hard OFF taleplerinden bağımsız "
            "başka bir hard kısıtta."
        )

elif status in (
    cp_model.FEASIBLE,
    cp_model.OPTIMAL,
):

    print(
        "Model feasible."
    )
