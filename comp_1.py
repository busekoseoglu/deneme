# ------------------------------------------------------------
# 8) ÇİFT OFF SONUÇLARI
# ------------------------------------------------------------

cift_off_rows = []
cift_off_sayisi_agent = defaultdict(int)

pair_off_dict = globals().get("pair_off", None)
weekend_pairs_list = globals().get("weekend_pairs", [])

# pair_off gerçekten sözlükse solver değişkeninden oku
pair_off_solverdan_okunabilir = (
    isinstance(pair_off_dict, dict)
    and isinstance(weekend_pairs_list, (list, tuple))
)

for a_raw in AGENTS:
    a = norm_agent(a_raw)

    for pair_index, (sat_ds, sun_ds) in enumerate(weekend_pairs_list):

        sat_date = pd.to_datetime(sat_ds).date()
        sun_date = pd.to_datetime(sun_ds).date()

        if pair_off_solverdan_okunabilir:
            var = pair_off_dict.get((a, pair_index))

            if var is not None:
                pair_value = int(solver.Value(var))
            else:
                pair_value = 0

        else:
            # pair_off sözlüğü yoksa final takvim sonucundan hesapla.
            # İzin gerçek OFF sayılmaz.
            sat_tip = tip_getir(a, sat_date)
            sun_tip = tip_getir(a, sun_date)

            sat_gercek_off = (
                sat_tip in {"off_t", "off_t2"}
                or (
                    sat_tip != "izin"
                    and work_map.get((a, sat_date), 0) == 0
                )
            )

            sun_gercek_off = (
                sun_tip in {"off_t", "off_t2"}
                or (
                    sun_tip != "izin"
                    and work_map.get((a, sun_date), 0) == 0
                )
            )

            pair_value = int(
                sat_gercek_off and sun_gercek_off
            )

        if pair_value == 1:
            cift_off_sayisi_agent[a] += 1

        cift_off_rows.append({
            "agent_user_code": a,
            "pair_index": pair_index,
            "cumartesi": sat_date.isoformat(),
            "pazar": sun_date.isoformat(),
            "cumartesi_durum": calendar_status[
                (a, sat_date)
            ]["durum"],
            "pazar_durum": calendar_status[
                (a, sun_date)
            ]["durum"],
            "cift_off_mi": pair_value,
            "hesaplama_kaynagi": (
                "solver_pair_off"
                if pair_off_solverdan_okunabilir
                else "final_takvimden_hesaplandi"
            ),
        })

print(
    "Çift OFF okuma kaynağı:",
    (
        "Solver pair_off değişkenleri"
        if pair_off_solverdan_okunabilir
        else "Final takvim sonucu"
    )
)
