# %% [HÜCRE 15] - İKİ VARDİYA ARASI MİNİMUM 11 SAAT DİNLENME

MIN_REST_HOURS = 11
MIN_REST_MINUTES = MIN_REST_HOURS * 60

def make_shift_datetime(ds, baslangic, bitis):
    """
    ds: tarih stringi
    baslangic: 08:00
    bitis: 17:00 veya gece dönen 02:00
    """
    start_dt = pd.to_datetime(f"{ds} {baslangic}")
    end_dt = pd.to_datetime(f"{ds} {bitis}")

    if end_dt <= start_dt:
        end_dt = end_dt + pd.Timedelta(days=1)

    return start_dt, end_dt


# shift datetime map
shift_dt_map = {}

for ds in PLAN_GUNLER:
    for v in gun_vardiyalari.get(ds, []):
        baslangic, bitis = saat[(ds, v)]
        start_dt, end_dt = make_shift_datetime(ds, baslangic, bitis)

        shift_dt_map[(ds, v)] = {
            "start_dt": start_dt,
            "end_dt": end_dt
        }


min_rest_constraints = 0

for a in AGENTS:
    agent_shift_options = []

    for ds in PLAN_GUNLER:
        for v in gun_vardiyalari.get(ds, []):
            if (a, ds, v) not in x:
                continue

            agent_shift_options.append({
                "ds": ds,
                "v": v,
                "start_dt": shift_dt_map[(ds, v)]["start_dt"],
                "end_dt": shift_dt_map[(ds, v)]["end_dt"]
            })

    agent_shift_options = sorted(agent_shift_options, key=lambda r: r["start_dt"])

    for i in range(len(agent_shift_options)):
        sh1 = agent_shift_options[i]

        for j in range(i + 1, len(agent_shift_options)):
            sh2 = agent_shift_options[j]

            # Aynı gün zaten max 1 vardiya kısıtıyla engelleniyor.
            # Burada sadece sonraki gün/sonraki vardiya çakışmalarına bakıyoruz.
            if sh2["start_dt"] <= sh1["end_dt"]:
                rest_minutes = -1
            else:
                rest_minutes = int(
                    (sh2["start_dt"] - sh1["end_dt"]).total_seconds() / 60
                )

            if rest_minutes < MIN_REST_MINUTES:
                model.Add(
                    x[(a, sh1["ds"], sh1["v"])] + x[(a, sh2["ds"], sh2["v"])] <= 1
                )
                min_rest_constraints += 1
            else:
                # start zamanına göre sıralı olduğu için bundan sonrakiler daha uzak
                break

print(f"minimum 11 saat dinlenme kısıtı: {min_rest_constraints} adet")
