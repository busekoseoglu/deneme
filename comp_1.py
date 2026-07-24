# %% [KISIT] - AYDA EN AZ 1 CUMARTESİ-PAZAR GERÇEK ÇİFT OFF
#
# Çift OFF sayılması için:
# - Cumartesi gerçek OFF olmalı
# - Pazar gerçek OFF olmalı
#
# İZİN günü çalışılmasa bile OFF sayılmaz.

weekend_pairs = []

plan_dates = sorted([
    pd.to_datetime(ds).date()
    for ds in PLAN_GUNLER
])

date_to_ds = {
    pd.to_datetime(ds).date(): ds
    for ds in PLAN_GUNLER
}

for d in plan_dates:

    # Cumartesi = 5
    if d.weekday() == 5:

        sunday = d + pd.Timedelta(days=1)

        if sunday in date_to_ds:

            sat_ds = date_to_ds[d]
            sun_ds = date_to_ds[sunday]

            weekend_pairs.append(
                (sat_ds, sun_ds)
            )


print("Cumartesi-Pazar çiftleri:")

for pair in weekend_pairs:
    print(pair)


# --------------------------------------------------
# GERÇEK OFF DEĞİŞKENLERİ
# --------------------------------------------------

gercek_off = {}

for a in AGENTS:

    for ds in PLAN_GUNLER:

        gercek_off[(a, ds)] = model.NewBoolVar(
            f"gercek_off_{a}_{ds}"
        )

        izinli_mi = int(
            izin_map.get((a, ds), 0)
        )

        if izinli_mi == 1:

            # İzin günü OFF sayılamaz
            model.Add(
                gercek_off[(a, ds)] == 0
            )

        else:

            # İzinli değilse:
            # çalışmıyorsa gerçek OFF,
            # çalışıyorsa OFF değil.
            model.Add(
                gercek_off[(a, ds)]
                + work[(a, ds)]
                == 1
            )


# --------------------------------------------------
# ÇİFT OFF DEĞİŞKENLERİ
# --------------------------------------------------

pair_off = {}

weekend_pair_constraints = 0

for a in AGENTS:

    pair_vars = []

    for i, (sat_ds, sun_ds) in enumerate(
        weekend_pairs
    ):

        pair_off[(a, i)] = model.NewBoolVar(
            f"pair_off_{a}_{i}"
        )

        # pair_off = 1 ise iki gün de gerçek OFF
        model.Add(
            pair_off[(a, i)]
            <= gercek_off[(a, sat_ds)]
        )

        model.Add(
            pair_off[(a, i)]
            <= gercek_off[(a, sun_ds)]
        )

        # İki gün de gerçek OFF ise pair_off = 1
        model.Add(
            pair_off[(a, i)]
            >=
            gercek_off[(a, sat_ds)]
            +
            gercek_off[(a, sun_ds)]
            - 1
        )

        pair_vars.append(
            pair_off[(a, i)]
        )

        weekend_pair_constraints += 3

    # Her agent için ayda en az 1 gerçek Cmt-Paz çift OFF
    if pair_vars:

        model.Add(
            sum(pair_vars) >= 1
        )

        weekend_pair_constraints += 1


print("Gerçek OFF değişken sayısı:", len(gercek_off))
print("Pair OFF değişken sayısı:", len(pair_off))
print(
    "Cumartesi-Pazar gerçek çift OFF kısıtı:",
    weekend_pair_constraints
)


# %% [KONTROL] - AYDA EN AZ 1 GERÇEK CUMARTESİ-PAZAR ÇİFT OFF

# --------------------------------------------------
# 1. SOLVE SONUCU KONTROLÜ
# --------------------------------------------------

if status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
    raise RuntimeError(
        f"Model sonucu FEASIBLE/OPTIMAL değil. Status: {status}"
    )


# Tarihi okunabilir göstermek için
def tarih_str(ds):
    return pd.to_datetime(ds).strftime("%Y-%m-%d")


# --------------------------------------------------
# 2. ÇİFT OFF DETAYLARI
# --------------------------------------------------

cift_off_kontrol_rows = []
cift_off_ihlalleri = []

for a in AGENTS:

    agent_pair_off_sayisi = 0
    agent_pair_detaylari = []

    for i, (sat_ds, sun_ds) in enumerate(weekend_pairs):

        pair_key = (a, i)

        if pair_key not in pair_off:
            continue

        pair_val = int(
            solver.Value(pair_off[pair_key])
        )

        cumartesi_work = int(
            solver.Value(work[(a, sat_ds)])
        )

        pazar_work = int(
            solver.Value(work[(a, sun_ds)])
        )

        cumartesi_gercek_off = int(
            solver.Value(gercek_off[(a, sat_ds)])
        )

        pazar_gercek_off = int(
            solver.Value(gercek_off[(a, sun_ds)])
        )

        # Gerçek sonuç:
        # İki gün de gerçek OFF ise 1, aksi hâlde 0
        beklenen_pair_val = int(
            cumartesi_gercek_off == 1
            and pazar_gercek_off == 1
        )

        pair_tutarlı_mı = (
            pair_val == beklenen_pair_val
        )

        if pair_val == 1:
            agent_pair_off_sayisi += 1

        detay = (
            f"{tarih_str(sat_ds)}-{tarih_str(sun_ds)}"
            f" | Cmt work={cumartesi_work}"
            f", gerçek_off={cumartesi_gercek_off}"
            f" | Paz work={pazar_work}"
            f", gerçek_off={pazar_gercek_off}"
            f" | pair_off={pair_val}"
        )

        agent_pair_detaylari.append(detay)

        # pair_off değişkeni gerçek OFF durumuyla uyuşmuyor
        if not pair_tutarlı_mı:

            cift_off_ihlalleri.append({
                "agent_user_code": a,
                "cumartesi": tarih_str(sat_ds),
                "pazar": tarih_str(sun_ds),
                "cumartesi_work": cumartesi_work,
                "pazar_work": pazar_work,
                "cumartesi_gercek_off": cumartesi_gercek_off,
                "pazar_gercek_off": pazar_gercek_off,
                "pair_off": pair_val,
                "beklenen_pair_off": beklenen_pair_val,
                "ihlal_tipi": "pair_off bağlantı ihlali"
            })

    # Her agentın ayda en az 1 çift OFF'u olmalı
    aylik_kural_saglandi_mi = (
        agent_pair_off_sayisi >= 1
    )

    if not aylik_kural_saglandi_mi:

        cift_off_ihlalleri.append({
            "agent_user_code": a,
            "cumartesi": None,
            "pazar": None,
            "cumartesi_work": None,
            "pazar_work": None,
            "cumartesi_gercek_off": None,
            "pazar_gercek_off": None,
            "pair_off": agent_pair_off_sayisi,
            "beklenen_pair_off": "en az 1",
            "ihlal_tipi": "Ayda hiç gerçek çift OFF yok"
        })

    cift_off_kontrol_rows.append({
        "agent_user_code": a,
        "gercek_cift_off_sayisi": agent_pair_off_sayisi,
        "kural_saglandi_mi": aylik_kural_saglandi_mi,
        "weekend_pair_details": " || ".join(
            agent_pair_detaylari
        )
    })


cift_off_kontrol_df = pd.DataFrame(
    cift_off_kontrol_rows
)

cift_off_violation_df = pd.DataFrame(
    cift_off_ihlalleri
)


# --------------------------------------------------
# 3. SONUÇ
# --------------------------------------------------

print("=" * 90)
print("AYDA EN AZ 1 GERÇEK CUMARTESİ-PAZAR ÇİFT OFF KONTROLÜ")
print("=" * 90)

print("Kontrol edilen agent sayısı:", len(cift_off_kontrol_df))
print(
    "Kuralı sağlamayan agent sayısı:",
    int((~cift_off_kontrol_df["kural_saglandi_mi"]).sum())
)
print(
    "Toplam tespit edilen ihlal:",
    len(cift_off_violation_df)
)

if cift_off_violation_df.empty:

    print("SONUÇ: İHLAL YOK")

else:

    print("SONUÇ: İHLAL VAR")

    display(
        cift_off_violation_df
        .sort_values(
            ["ihlal_tipi", "agent_user_code"]
        )
        .reset_index(drop=True)
    )


display(
    cift_off_kontrol_df
    .sort_values(
        [
            "kural_saglandi_mi",
            "gercek_cift_off_sayisi",
            "agent_user_code"
        ],
        ascending=[True, True, True]
    )
    .reset_index(drop=True)
)
