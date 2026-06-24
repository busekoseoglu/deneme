# %% [HÜCRE] - İKİ VARDİYA ARASI MİNİMUM 11 SAAT DİNLENME

MIN_REST_HOURS = 11
MIN_REST_MINUTES = MIN_REST_HOURS * 60

def make_shift_datetime(tarih, baslangic, bitis):
    start_dt = pd.to_datetime(f"{tarih} {baslangic}")
    end_dt = pd.to_datetime(f"{tarih} {bitis}")

    # Geceye dönen vardiya: 18:00-02:00 gibi
    if end_dt <= start_dt:
        end_dt = end_dt + pd.Timedelta(days=1)

    return start_dt, end_dt


# Tüm vardiya zamanlarını hazırla
shift_time_map = {}

for ds in PLAN_GUNLER:
    for v in gun_vardiyalari.get(ds, []):
        bas, bit = saat[(ds, v)]
        start_dt, end_dt = make_shift_datetime(ds, bas, bit)

        shift_time_map[(ds, v)] = {
            "start_dt": start_dt,
            "end_dt": end_dt,
            "vardiya": f"{bas}-{bit}"
        }


min_rest_constraints = 0

for a in AGENTS:
    agent_options = []

    for ds in PLAN_GUNLER:
        for v in gun_vardiyalari.get(ds, []):
            if (a, ds, v) in x:
                agent_options.append({
                    "ds": ds,
                    "v": v,
                    "start_dt": shift_time_map[(ds, v)]["start_dt"],
                    "end_dt": shift_time_map[(ds, v)]["end_dt"],
                    "vardiya": shift_time_map[(ds, v)]["vardiya"]
                })

    agent_options = sorted(agent_options, key=lambda r: r["start_dt"])

    for i in range(len(agent_options)):
        sh1 = agent_options[i]

        for j in range(i + 1, len(agent_options)):
            sh2 = agent_options[j]

            rest_minutes = (
                sh2["start_dt"] - sh1["end_dt"]
            ).total_seconds() / 60

            # Eğer vardiyalar çakışıyorsa veya dinlenme 11 saatten azsa birlikte seçilemez
            if rest_minutes < MIN_REST_MINUTES:
                model.Add(
                    x[(a, sh1["ds"], sh1["v"])] +
                    x[(a, sh2["ds"], sh2["v"])]
                    <= 1
                )
                min_rest_constraints += 1

            # sh2 artık yeterince uzaksa sonraki vardiyalar daha da uzak olacak
            if rest_minutes >= MIN_REST_MINUTES:
                break

print("minimum 11 saat dinlenme kısıtı:", min_rest_constraints)
