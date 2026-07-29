# %% [KISIT / DEBUG] - AYLIK EKSTRA OFF / TELAFİ DENGESİ

# Bu hücre mevcut aylık telafi kuralını değiştirmez.
# Her agentın telafi eşitliğine bir assumption ekleyerek,
# infeasible durumda hangi agentların eşitliğinin
# çakışmaya katkı verdiğini bulmamızı sağlar.

aylik_telafi_debug_rows = []

telafi_denge_assumption = {}
telafi_assumption_index_to_agent = {}

for a_raw in AGENTS:

    a = str(a_raw).strip()

    agent_extra_off_vars = [
        extra_off_week[(a, wk)]
        for wk in WEEKS
        if (a, wk) in extra_off_week
    ]

    agent_telafi_vars = [
        telafi_week[(a, wk)]
        for wk in WEEKS
        if (a, wk) in telafi_week
    ]

    agent_overtime_vars = [
        overtime_week[(a, wk)]
        for wk in WEEKS
        if (a, wk) in overtime_week
    ]

    # Bu agentın aylık telafi eşitliğini takip eden assumption
    telafi_denge_assumption[a] = model.NewBoolVar(
        f"assumption_telafi_denge_{a}"
    )

    # Aylık toplam ekstra OFF,
    # aylık toplam normal çalışma telafisine eşit olmalı.
    model.Add(
        sum(agent_extra_off_vars)
        ==
        sum(agent_telafi_vars)
    ).OnlyEnforceIf(
        telafi_denge_assumption[a]
    )

    # Assumption aktifken yukarıdaki eşitlik normal hard kısıt gibi çalışır.
    model.AddAssumption(
        telafi_denge_assumption[a]
    )

    telafi_assumption_index_to_agent[
        telafi_denge_assumption[a].Index()
    ] = a

    # Gerçek mesai sınırı telafi sisteminden ayrıdır.
    model.Add(
        sum(agent_overtime_vars)
        <= MAX_OVERTIME_PER_MONTH
    )

    aylik_telafi_debug_rows.append({
        "agent_user_code": a,
        "extra_off_week_var_sayisi": len(
            agent_extra_off_vars
        ),
        "telafi_week_var_sayisi": len(
            agent_telafi_vars
        ),
        "overtime_week_var_sayisi": len(
            agent_overtime_vars
        ),
    })


aylik_telafi_debug_df = pd.DataFrame(
    aylik_telafi_debug_rows
)

print(
    "Assumption eklenen aylık telafi eşitliği:",
    len(telafi_denge_assumption)
)

print(
    "Gerçek mesai aylık üst sınırı:",
    MAX_OVERTIME_PER_MONTH
)


# %% [SOLVE / DEBUG] - INFEASIBLE TELAFİ KISITI TESPİTİ

status = solver.Solve(model)

print(
    "Solver status:",
    solver.StatusName(status)
)

if status == cp_model.INFEASIBLE:

    core_literals = (
        solver.SufficientAssumptionsForInfeasibility()
    )

    core_agentlar = []

    for literal in core_literals:

        # OR-Tools negatif literal kullanırsa
        # bağlı olduğu değişken indeksini bul.
        if literal >= 0:
            variable_index = literal
        else:
            variable_index = -literal - 1

        if variable_index in telafi_assumption_index_to_agent:

            core_agentlar.append(
                telafi_assumption_index_to_agent[
                    variable_index
                ]
            )

    core_agentlar = sorted(
        set(core_agentlar)
    )

    print(
        "Infeasible core assumption sayısı:",
        len(core_literals)
    )

    print(
        "Aylık telafi eşitliği çakışan agent sayısı:",
        len(core_agentlar)
    )

    print(
        "Çakışan agentlar:",
        core_agentlar
    )

    if (
        core_agentlar
        and "haftalik_off_telafi_debug_df" in globals()
        and not haftalik_off_telafi_debug_df.empty
    ):

        df_telafi_core_detay = (
            haftalik_off_telafi_debug_df[
                haftalik_off_telafi_debug_df[
                    "agent_user_code"
                ].astype(str).isin(core_agentlar)
            ]
            .copy()
            .sort_values(
                [
                    "agent_user_code",
                    "week",
                ]
            )
        )

        display(
            df_telafi_core_detay
        )

    elif not core_agentlar:

        print(
            "Aylık telafi eşitliklerinden oluşan bir core bulunamadı."
        )

        print(
            "Sorun haftalık çalışma eşitliğinde veya "
            "önceki başka bir hard kısıtta."
        )

elif status in (
    cp_model.FEASIBLE,
    cp_model.OPTIMAL,
):

    print(
        "Model feasible. Aylık telafi eşitlikleri "
        "tek başına çakışma oluşturmuyor."
    )
