# %% [KONTROL] - PARTIAL END HAMİLE/SÜT KURALI SONUÇ KONTROLÜ
# Amaç:
# partial_end hafta içi günlerde çalışmaya zorlanan hamile/süt izni agentlar
# gerçekten çalışmış mı ve hangi vardiyaya atanmış görmek.
#
# Beklenen:
# - kontrol_ok = True
# - worked = 1
# - assigned_shift dolu
# - shift_start / shift_end dolu olmalı.
#
# Not:
# shift_start / shift_end None gelirse bu genelde model hatası değil,
# saat dict'indeki date formatı ile kontrol kodundaki date formatı uyuşmadığı içindir.
# Bu kontrol kodu onu daha sağlam yakalar.

# --------------------------------------------------
# 0) Yardımcı fonksiyonlar
# --------------------------------------------------

def _to_date_str(ds):
    return pd.to_datetime(ds).strftime("%Y-%m-%d")


def _find_plan_day_by_str(ds_str):
    for d in PLAN_GUNLER:
        if _to_date_str(d) == ds_str:
            return d
    return None


def _safe_solver_value(var, default=0):
    try:
        return int(solver.Value(var))
    except Exception:
        return default


def get_shift_time_for_control(ds_obj, ds_str, v, agent_user_code=None):
    """
    Vardiya saatini birkaç farklı kaynaktan sağlam şekilde bulur.

    Öncelik:
    1) saat dict
    2) vardiya_talep_df
    3) coverage_simple_df
    4) agent_day_plan_df
    """

    v = str(v).strip() if v is not None else v

    # -------------------------------
    # 1) saat dict üzerinden dene
    # -------------------------------
    if "saat" in globals() and isinstance(saat, dict):

        ds_ts = pd.to_datetime(ds_str)
        ds_date = ds_ts.date()

        possible_ds_keys = [
            ds_obj,
            ds_str,
            ds_date,
            ds_ts,
        ]

        possible_v_keys = [
            v,
            str(v).strip() if v is not None else v,
        ]

        for d_key in possible_ds_keys:
            for v_key in possible_v_keys:
                key = (d_key, v_key)

                if key in saat:
                    val = saat[key]

                    if isinstance(val, (list, tuple)) and len(val) >= 2:
                        return val[0], val[1], "saat_dict"

    # -------------------------------
    # 2) vardiya_talep_df üzerinden dene
    # -------------------------------
    if "vardiya_talep_df" in globals() and isinstance(vardiya_talep_df, pd.DataFrame):
        if {"date", "shift", "shift_start", "shift_end"}.issubset(vardiya_talep_df.columns):

            tmp = vardiya_talep_df[
                (vardiya_talep_df["date"].astype(str) == ds_str) &
                (vardiya_talep_df["shift"].astype(str).str.strip() == str(v).strip())
            ]

            if len(tmp) > 0:
                return (
                    tmp["shift_start"].iloc[0],
                    tmp["shift_end"].iloc[0],
                    "vardiya_talep_df"
                )

    # -------------------------------
    # 3) coverage_simple_df üzerinden dene
    # -------------------------------
    if "coverage_simple_df" in globals() and isinstance(coverage_simple_df, pd.DataFrame):
        if {"date", "shift", "shift_start", "shift_end"}.issubset(coverage_simple_df.columns):

            tmp = coverage_simple_df[
                (coverage_simple_df["date"].astype(str) == ds_str) &
                (coverage_simple_df["shift"].astype(str).str.strip() == str(v).strip())
            ]

            if len(tmp) > 0:
                return (
                    tmp["shift_start"].iloc[0],
                    tmp["shift_end"].iloc[0],
                    "coverage_simple_df"
                )

    # -------------------------------
    # 4) agent_day_plan_df üzerinden dene
    # -------------------------------
    if "agent_day_plan_df" in globals() and isinstance(agent_day_plan_df, pd.DataFrame):
        needed_cols = {
            "agent_user_code",
            "date",
            "assigned_shift",
            "shift_start",
            "shift_end"
        }

        if needed_cols.issubset(agent_day_plan_df.columns) and agent_user_code is not None:

            tmp = agent_day_plan_df[
                (agent_day_plan_df["agent_user_code"].astype(str).str.strip() == str(agent_user_code).strip()) &
                (agent_day_plan_df["date"].astype(str) == ds_str) &
                (agent_day_plan_df["assigned_shift"].astype(str).str.strip() == str(v).strip())
            ]

            if len(tmp) > 0:
                return (
                    tmp["shift_start"].iloc[0],
                    tmp["shift_end"].iloc[0],
                    "agent_day_plan_df"
                )

    return None, None, "bulunamadi"


# --------------------------------------------------
# 1) Debug dataframe var mı kontrol et
# --------------------------------------------------

if (
    "partial_end_hamile_sut_work_debug_df" not in globals()
    or not isinstance(partial_end_hamile_sut_work_debug_df, pd.DataFrame)
    or partial_end_hamile_sut_work_debug_df.empty
):
    raise ValueError(
        "partial_end_hamile_sut_work_debug_df bulunamadı veya boş. "
        "Önce constraint hücresini solve'dan önce çalıştırmalısın."
    )


# --------------------------------------------------
# 2) Sadece constraint_added=True olan satırları kontrol et
# --------------------------------------------------

partial_end_hamile_sut_result_rows = []

forced_rows = partial_end_hamile_sut_work_debug_df[
    partial_end_hamile_sut_work_debug_df["constraint_added"] == True
].copy()

for _, r in forced_rows.iterrows():

    a = str(r["agent_user_code"]).strip()
    ds_str = str(r["date"])
    wk = r["week"]

    ds_obj = _find_plan_day_by_str(ds_str)

    if ds_obj is None:
        partial_end_hamile_sut_result_rows.append({
            "agent_user_code": a,
            "date": ds_str,
            "week": wk,
            "worked": None,
            "assigned_shift": None,
            "shift_start": None,
            "shift_end": None,
            "shift_time_source": None,
            "kontrol_ok": False,
            "saat_ok": False,
            "problem": "PLAN_GUNLER içinde tarih bulunamadı"
        })
        continue

    # --------------------------------------------------
    # 2.1) work sonucu
    # --------------------------------------------------

    worked = 0

    if (a, ds_obj) in work:
        worked = _safe_solver_value(work[(a, ds_obj)])
    else:
        worked = 0

    # --------------------------------------------------
    # 2.2) Atanan vardiyayı bul
    # --------------------------------------------------

    assigned_shift = None
    shift_start = None
    shift_end = None
    shift_time_source = None

    for v in gun_vardiyalari.get(ds_obj, []):

        if (a, ds_obj, v) not in x:
            continue

        if _safe_solver_value(x[(a, ds_obj, v)]) == 1:
            assigned_shift = v

            shift_start, shift_end, shift_time_source = get_shift_time_for_control(
                ds_obj=ds_obj,
                ds_str=ds_str,
                v=v,
                agent_user_code=a
            )

            break

    kontrol_ok = (
        worked == 1
        and assigned_shift is not None
    )

    saat_ok = (
        shift_start is not None
        and shift_end is not None
    )

    if not kontrol_ok:
        problem = "Çalışması zorlandı ama worked=1 veya assigned_shift bulunamadı"
    elif not saat_ok:
        problem = "Atama doğru; sadece vardiya saati bulunamadı"
    else:
        problem = None

    partial_end_hamile_sut_result_rows.append({
        "agent_user_code": a,
        "date": ds_str,
        "week": wk,
        "worked": worked,
        "assigned_shift": assigned_shift,
        "shift_start": shift_start,
        "shift_end": shift_end,
        "shift_time_source": shift_time_source,
        "kontrol_ok": kontrol_ok,
        "saat_ok": saat_ok,
        "problem": problem
    })


partial_end_hamile_sut_result_df = pd.DataFrame(
    partial_end_hamile_sut_result_rows
)


# --------------------------------------------------
# 3) Özet çıktılar
# --------------------------------------------------

print("Partial end hamile/süt kontrol edilen satır sayısı:", len(partial_end_hamile_sut_result_df))

if len(partial_end_hamile_sut_result_df) > 0:

    print(
        "Kural ihlal sayısı:",
        (partial_end_hamile_sut_result_df["kontrol_ok"] == False).sum()
    )

    print(
        "Saat bilgisi eksik satır sayısı:",
        (partial_end_hamile_sut_result_df["saat_ok"] == False).sum()
    )

    print("\nKontrol dağılımı:")
    display(
        partial_end_hamile_sut_result_df[
            ["kontrol_ok", "saat_ok"]
        ]
        .value_counts()
        .reset_index(name="satir_sayisi")
    )

    print("\nDetay:")
    display(
        partial_end_hamile_sut_result_df
        .sort_values(
            ["kontrol_ok", "saat_ok", "date", "agent_user_code"],
            ascending=[True, True, True, True]
        )
    )

else:
    print("Bu ay için partial_end hamile/süt constraint_added=True satırı yok.")
