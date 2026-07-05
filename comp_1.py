# %% DEBUG - RESMİ TATİLDE HARD X==0 / WORK==0 VAR MI?
# Bu versiyon HasField / WhichOneof kullanmaz.

resmi_tatil_debug_days = set()

if "resmi_tatil_plan_gunleri" in globals():
    resmi_tatil_debug_days = set(resmi_tatil_plan_gunleri)
else:
    if "RESMI_TATIL_GUNLERI" in globals():
        resmi_tatil_key_set = set(RESMI_TATIL_GUNLERI)

        for ds in PLAN_GUNLER:
            ds_key = pd.to_datetime(ds).strftime("%Y-%m-%d")

            if ds_key in resmi_tatil_key_set:
                resmi_tatil_debug_days.add(ds)

print("Resmi tatil debug günleri:", resmi_tatil_debug_days)


x_index_to_key = {
    var.Index(): key
    for key, var in x.items()
}

work_index_to_key = {
    var.Index(): key
    for key, var in work.items()
}


hard_zero_x_rows = []
hard_zero_work_rows = []

proto = model.Proto()

for c_idx, ct in enumerate(proto.constraints):

    # Bazı OR-Tools sürümlerinde ct.linear var ama boş olabilir.
    # Bu yüzden try/except ile gidiyoruz.
    try:
        lin = ct.linear
        vars_list = list(lin.vars)
        coeffs_list = list(lin.coeffs)
        domain_list = list(lin.domain)
    except Exception:
        continue

    # Tek değişkenli x == 0 / work == 0 kısıtlarını arıyoruz.
    if len(vars_list) != 1:
        continue

    if len(coeffs_list) != 1:
        continue

    var_idx = vars_list[0]
    coeff = coeffs_list[0]

    if coeff != 1:
        continue

    if domain_list != [0, 0]:
        continue

    # x == 0
    if var_idx in x_index_to_key:
        a, ds, v = x_index_to_key[var_idx]

        if ds in resmi_tatil_debug_days:
            bas, bit = saat[(ds, v)] if (ds, v) in saat else (None, None)

            hard_zero_x_rows.append({
                "constraint_index": c_idx,
                "agent_user_code": a,
                "date": ds,
                "shift": v,
                "shift_start": bas,
                "shift_end": bit,
            })

    # work == 0
    if var_idx in work_index_to_key:
        a, ds = work_index_to_key[var_idx]

        if ds in resmi_tatil_debug_days:
            hard_zero_work_rows.append({
                "constraint_index": c_idx,
                "agent_user_code": a,
                "date": ds,
            })


hard_zero_x_df = pd.DataFrame(hard_zero_x_rows)
hard_zero_work_df = pd.DataFrame(hard_zero_work_rows)

print("Resmi tatil günü hard x==0 sayısı:", len(hard_zero_x_df))
print("Resmi tatil günü hard work==0 sayısı:", len(hard_zero_work_df))


if len(hard_zero_x_df) > 0:
    agent_info_cols = [
        "agent_user_code",
        "agent_name",
        "takim",
        "teamleader_name",
        "hamile_flg",
        "sut_izni_flg",
        "mesaiye_kalamaz_flg",
        "sabah_calisir_flg"
    ]

    agent_info = df_tam[agent_info_cols].copy()
    agent_info["agent_user_code"] = agent_info["agent_user_code"].astype(str).str.strip()

    hard_zero_x_df = hard_zero_x_df.merge(
        agent_info,
        on="agent_user_code",
        how="left"
    )

    print("Resmi tatilde hard x==0 detay:")
    display(
        hard_zero_x_df
        .sort_values(["shift_start", "shift_end", "takim", "agent_user_code"])
        .head(300)
    )


if len(hard_zero_work_df) > 0:
    agent_info_cols = [
        "agent_user_code",
        "agent_name",
        "takim",
        "teamleader_name",
        "hamile_flg",
        "sut_izni_flg",
        "mesaiye_kalamaz_flg",
        "sabah_calisir_flg"
    ]

    agent_info = df_tam[agent_info_cols].copy()
    agent_info["agent_user_code"] = agent_info["agent_user_code"].astype(str).str.strip()

    hard_zero_work_df = hard_zero_work_df.merge(
        agent_info,
        on="agent_user_code",
        how="left"
    )

    print("Resmi tatilde hard work==0 detay:")
    display(
        hard_zero_work_df
        .sort_values(["date", "takim", "agent_user_code"])
        .head(300)
    )
