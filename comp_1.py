# %% [HÜCRE] - VARDİYA TİPİ VE MOLA/YEMEK DESTEK SKORU
# Bu hücrede her gün-vardiya için:
# 1. Gece/akşam vardiyası mı?
# 2. Mola/yemek yoğunluk saatlerini destekliyor mu?
# 3. Fazla atama için üst limit kaç?
# hesaplıyoruz.
#
# Gece/akşam vardiyaları:
# - 17:00-01:00
# - 18:00-02:00
# - 00:00-08:00
#
# Mola/yemek yoğunluk pencereleri:
# - 12:00-13:30
# - 15:00-16:00
# - 19:00-20:00
#
# Ama gece/akşam vardiyası ise, 19:00'u kapsasa bile
# fazla atama açısından yine "gece/akşam" sınıfında kalacak.

def saat_to_dakika(saat_str):
    """
    'HH:MM' veya 'HH:MM:SS' formatındaki saati dakika cinsine çevirir.
    Örn: '12:30' -> 750
    """
    saat_str = str(saat_str).strip()[:5]
    h, m = saat_str.split(":")
    return int(h) * 60 + int(m)


def saat_normalize(saat_str):
    """
    Saat değerini HH:MM formatına getirir.
    Örn: '17:00:00' -> '17:00'
    """
    return str(saat_str).strip()[:5]


def vardiya_araligi_dakika(baslangic, bitis):
    """
    Vardiya başlangıç/bitiş saatini dakika aralığına çevirir.
    Gece dönen vardiyalarda bitişe 24 saat eklenir.

    Örn:
    09:00-18:00 -> 540, 1080
    17:00-01:00 -> 1020, 1500
    00:00-08:00 -> 0, 480
    """
    bas_dk = saat_to_dakika(baslangic)
    bit_dk = saat_to_dakika(bitis)

    if bit_dk <= bas_dk:
        bit_dk += 24 * 60

    return bas_dk, bit_dk


def aralik_kesisiyor_mu(vardiya_bas, vardiya_bit, pencere_bas, pencere_bit):
    """
    Vardiya aralığı ile mola/yemek yoğunluk penceresi kesişiyor mu?
    """
    return max(vardiya_bas, pencere_bas) < min(vardiya_bit, pencere_bit)


# Parametreler
GECE_AKSAM_VARDIYA_SET = {
    ("17:00", "01:00"),
    ("18:00", "02:00"),
    ("00:00", "08:00")
}

# Mola/yemek yoğunluk pencereleri
MOLA_YOGUNLUK_PENCERELERI = [
    ("ogle_yemek", "12:00", "13:30", 2),
    ("ikindi_mola", "15:00", "16:00", 1),
    ("aksam_yemek", "19:00", "20:00", 2),
]

# Fazla atama üst limitleri
GENEL_MAX_FAZLA_ATAMA = 15
GECE_MAX_FAZLA_ATAMA = 3

# Her gün-vardiya için hesaplanacak sözlükler
gece_aksam_vardiyasi_mi = {}
mola_destek_skoru = {}
mola_destek_vardiyasi_mi = {}
fazla_atama_ust_limit = {}

for ds in PLAN_GUNLER:
    for v in gun_vardiyalari.get(ds, []):

        baslangic = saat_normalize(saat[(ds, v)][0])
        bitis = saat_normalize(saat[(ds, v)][1])

        # Gece/akşam vardiyası mı?
        gece_mi = (baslangic, bitis) in GECE_AKSAM_VARDIYA_SET
        gece_aksam_vardiyasi_mi[(ds, v)] = gece_mi

        # Vardiya dakika aralığı
        vardiya_bas, vardiya_bit = vardiya_araligi_dakika(baslangic, bitis)

        # Mola/yemek destek skoru
        skor = 0

        for pencere_adi, pencere_bas_saat, pencere_bit_saat, pencere_puan in MOLA_YOGUNLUK_PENCERELERI:
            pencere_bas = saat_to_dakika(pencere_bas_saat)
            pencere_bit = saat_to_dakika(pencere_bit_saat)

            # Gece dönen vardiyalarda 19:00 gibi pencereler zaten aynı gün içinde kalır.
            if aralik_kesisiyor_mu(vardiya_bas, vardiya_bit, pencere_bas, pencere_bit):
                skor += pencere_puan

        mola_destek_skoru[(ds, v)] = skor

        # Gece vardiyası ise, mola desteklese bile fazla atama açısından gece sınıfında kalacak.
        mola_destek_vardiyasi_mi[(ds, v)] = (skor > 0) and (not gece_mi)

        # Fazla atama hard cap
        if gece_mi:
            fazla_atama_ust_limit[(ds, v)] = GECE_MAX_FAZLA_ATAMA
        else:
            fazla_atama_ust_limit[(ds, v)] = GENEL_MAX_FAZLA_ATAMA


vardiya_tip_ozet = []

for ds in PLAN_GUNLER:
    for v in gun_vardiyalari.get(ds, []):
        vardiya_tip_ozet.append({
            "tarih": str(ds),
            "hafta": day_week[ds],
            "vardiya": v,
            "baslangic": saat[(ds, v)][0],
            "bitis": saat[(ds, v)][1],
            "gece_aksam_vardiyasi_mi": gece_aksam_vardiyasi_mi[(ds, v)],
            "mola_destek_skoru": mola_destek_skoru[(ds, v)],
            "mola_destek_vardiyasi_mi": mola_destek_vardiyasi_mi[(ds, v)],
            "fazla_atama_ust_limit": fazla_atama_ust_limit[(ds, v)]
        })

vardiya_tip_ozet_df = pd.DataFrame(vardiya_tip_ozet)

print("Gece/akşam gün-vardiya sayısı:", vardiya_tip_ozet_df["gece_aksam_vardiyasi_mi"].sum())
print("Mola destek gün-vardiya sayısı:", vardiya_tip_ozet_df["mola_destek_vardiyasi_mi"].sum())

display(
    vardiya_tip_ozet_df
    .drop_duplicates(["vardiya", "baslangic", "bitis"])
    .sort_values(["gece_aksam_vardiyasi_mi", "mola_destek_skoru", "baslangic"], ascending=[False, False, True])
)

# %% [HÜCRE] - FAZLA ATAMA ÜST LİMİTİ
# Bu hücrede her vardiyada talebin üstüne çıkabilecek maksimum kişi sayısını sınırlıyoruz.
#
# Genel kural:
# assigned <= required + 15
#
# Gece/akşam vardiyası ise:
# assigned <= required + 3
#
# Amaç:
# Talep 50 iken 72 atama gibi aşırı over durumlarını engellemek.
# Gece/akşam vardiyalarına fazla kişi yığılmasını engellemek.

fazla_atama_cap_constraints = 0

for ds in PLAN_GUNLER:
    for v in gun_vardiyalari.get(ds, []):

        required = int(talep[(ds, v)])

        assigned = sum(
            x[(a, ds, v)]
            for a in AGENTS
            if (a, ds, v) in x
        )

        max_fazla = fazla_atama_ust_limit[(ds, v)]

        model.Add(
            assigned <= required + max_fazla
        )

        fazla_atama_cap_constraints += 1

print("Fazla atama üst limit kısıtı:", fazla_atama_cap_constraints)
print("Genel max fazla atama:", GENEL_MAX_FAZLA_ATAMA)
print("Gece/akşam max fazla atama:", GECE_MAX_FAZLA_ATAMA)

# %% [HÜCRE] - OBJECTIVE
# Bu objective, under/missing sorununu çözerken fazla kişiyi daha mantıklı vardiyalara yönlendirir.
#
# Öncelik:
# 1. Buffer altına düşme çok pahalı
# 2. Talebe göre eksik kalma pahalı
# 3. Mesai daha ucuz; eksik kapatabiliyorsa kullanılabilir
# 4. Fazla atama vardiya tipine göre cezalandırılır:
#    - Gece/akşam vardiyası: çok pahalı
#    - Mola/yemek destek vardiyası: daha ucuz
#    - Normal vardiya: orta seviye
# 5. Buffer üstüne çıkma ayrıca cezalı

objective_terms = []

# Eksik tarafı ağırlıkları
UNDER_BUFFER_W = 300000
MISSING_TO_REQUIRED_W = 50000

# Mesai ağırlığı
OVERTIME_W = 1000

# Fazla tarafı ağırlıkları
EXCESS_GECE_AKSAM_W = 15000
EXCESS_NORMAL_W = 5000
EXCESS_MOLA_DESTEK_W = 1000

# Buffer üst sınırını aşma ağırlığı
OVER_BUFFER_W = 1000

for ds in PLAN_GUNLER:
    for v in gun_vardiyalari.get(ds, []):

        # %5 buffer altına düşmek en kötü durumlardan biri
        objective_terms.append(
            UNDER_BUFFER_W * under_buffer[(ds, v)]
        )

        # Buffer içinde kalsa bile talebin altında kalmak ciddi cezalı
        objective_terms.append(
            MISSING_TO_REQUIRED_W * missing_to_required[(ds, v)]
        )

        # Fazla atama cezası vardiya tipine göre değişir.
        # Gece/akşam vardiyalarında fazla kişi çok pahalı.
        # Mola/yemek destek vardiyalarında fazla kişi daha kabul edilebilir.
        if gece_aksam_vardiyasi_mi[(ds, v)]:
            excess_weight = EXCESS_GECE_AKSAM_W

        elif mola_destek_vardiyasi_mi[(ds, v)]:
            excess_weight = EXCESS_MOLA_DESTEK_W

        else:
            excess_weight = EXCESS_NORMAL_W

        objective_terms.append(
            excess_weight * excess_to_required[(ds, v)]
        )

        # %5 buffer üst sınırının da üstüne çıkarsa ayrıca ceza
        objective_terms.append(
            OVER_BUFFER_W * over_buffer[(ds, v)]
        )

# Mesai cezası
for a in AGENTS:
    for wk in WEEKS:
        objective_terms.append(
            OVERTIME_W * overtime_week[(a, wk)]
        )

model.Minimize(sum(objective_terms))

print("Objective term sayısı:", len(objective_terms))
print("UNDER_BUFFER_W:", UNDER_BUFFER_W)
print("MISSING_TO_REQUIRED_W:", MISSING_TO_REQUIRED_W)
print("OVERTIME_W:", OVERTIME_W)
print("EXCESS_GECE_AKSAM_W:", EXCESS_GECE_AKSAM_W)
print("EXCESS_NORMAL_W:", EXCESS_NORMAL_W)
print("EXCESS_MOLA_DESTEK_W:", EXCESS_MOLA_DESTEK_W)
print("OVER_BUFFER_W:", OVER_BUFFER_W)


# %% KONTROL - FAZLA ATAMA DAĞILIMI VE MOLA DESTEK ETKİSİ

fazla_atama_kontrol_rows = []

for ds in PLAN_GUNLER:
    for v in gun_vardiyalari.get(ds, []):

        assigned = sum(
            solver.Value(x[(a, ds, v)])
            for a in AGENTS
            if (a, ds, v) in x
        )

        required = int(talep[(ds, v)])
        excess = max(0, assigned - required)

        fazla_atama_kontrol_rows.append({
            "tarih": str(ds),
            "gun": DAY_TR[pd.to_datetime(ds).weekday()],
            "hafta": day_week[ds],
            "vardiya": v,
            "baslangic": saat[(ds, v)][0],
            "bitis": saat[(ds, v)][1],
            "talep": required,
            "atanan": assigned,
            "gap_to_required": assigned - required,
            "excess_to_required": solver.Value(excess_to_required[(ds, v)]),
            "manual_excess": excess,
            "under_buffer": solver.Value(under_buffer[(ds, v)]),
            "over_buffer": solver.Value(over_buffer[(ds, v)]),
            "missing_to_required": solver.Value(missing_to_required[(ds, v)]),
            "gece_aksam_vardiyasi_mi": gece_aksam_vardiyasi_mi[(ds, v)],
            "mola_destek_skoru": mola_destek_skoru[(ds, v)],
            "mola_destek_vardiyasi_mi": mola_destek_vardiyasi_mi[(ds, v)],
            "fazla_atama_ust_limit": fazla_atama_ust_limit[(ds, v)],
            "fazla_atama_limit_ihlali": excess > fazla_atama_ust_limit[(ds, v)]
        })

fazla_atama_kontrol = pd.DataFrame(fazla_atama_kontrol_rows)

print("Toplam under_buffer:", fazla_atama_kontrol["under_buffer"].sum())
print("Toplam missing_to_required:", fazla_atama_kontrol["missing_to_required"].sum())
print("Toplam excess_to_required:", fazla_atama_kontrol["excess_to_required"].sum())
print("Toplam over_buffer:", fazla_atama_kontrol["over_buffer"].sum())

print("Max excess:", fazla_atama_kontrol["manual_excess"].max())
print("Fazla atama limit ihlali:", fazla_atama_kontrol["fazla_atama_limit_ihlali"].sum())

print("\nGece/akşam vardiyalarında max excess:")
display(
    fazla_atama_kontrol[fazla_atama_kontrol["gece_aksam_vardiyasi_mi"] == True]
    .groupby(["vardiya", "baslangic", "bitis"], as_index=False)
    .agg(
        max_excess=("manual_excess", "max"),
        toplam_excess=("manual_excess", "sum"),
        satir_sayisi=("manual_excess", "count")
    )
    .sort_values("max_excess", ascending=False)
)

print("\nMola destek / normal / gece sınıfına göre fazla atama özeti:")
fazla_atama_kontrol["vardiya_sinifi"] = np.select(
    [
        fazla_atama_kontrol["gece_aksam_vardiyasi_mi"] == True,
        fazla_atama_kontrol["mola_destek_vardiyasi_mi"] == True
    ],
    [
        "gece_aksam",
        "mola_destek"
    ],
    default="normal"
)

display(
    fazla_atama_kontrol
    .groupby("vardiya_sinifi", as_index=False)
    .agg(
        toplam_talep=("talep", "sum"),
        toplam_atanan=("atanan", "sum"),
        toplam_excess=("manual_excess", "sum"),
        max_excess=("manual_excess", "max"),
        toplam_missing=("missing_to_required", "sum"),
        toplam_under=("under_buffer", "sum"),
        satir_sayisi=("vardiya", "count")
    )
)

print("\nEn yüksek excess olan vardiyalar:")
display(
    fazla_atama_kontrol
    .sort_values(["manual_excess", "tarih", "baslangic"], ascending=[False, True, True])
    .head(50)
)
