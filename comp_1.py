# %% [CONFIG] - MODEL PARAMETRELERİ
# Bu hücre modelde kullanılan tüm ayarlanabilir parametreleri tek yerde toplar.
# Parametre değiştirmek istediğimizde kodun farklı yerlerine gitmeden sadece burayı güncelleriz.

CONFIG = {
    # -------------------------------------------------
    # COVERAGE / BUFFER PARAMETRESİ
    # -------------------------------------------------

    # Coverage alt/üst buffer oranı.
    # Örn:
    # Talep = 100, BUFFER_RATE = 0.05 ise
    # alt sınır = floor(100 * 0.95) = 95
    # üst sınır = ceil(100 * 1.05) = 105
    "BUFFER_RATE": 0.05,


    # -------------------------------------------------
    # HAFTALIK ÇALIŞMA / MESAİ PARAMETRELERİ
    # -------------------------------------------------

    # Normal haftalık çalışma günü.
    # İzin varsa hedef: NORMAL_WORK_DAYS - izin_günü
    "NORMAL_WORK_DAYS": 5,

    # Bir agent ay içinde maksimum kaç mesai alabilir?
    "MAX_OVERTIME_PER_MONTH": 2,

    # 2. mesaiyi ekstra cezalandırma ağırlığı.
    # Amaç: Mesai mümkün olduğunca farklı agentlara dağılsın.
    "IKINCI_MESAI_W": 50000,


    # -------------------------------------------------
    # GECE / AKŞAM VARDİYA PARAMETRELERİ
    # -------------------------------------------------

    # Gece/akşam vardiyası olarak kabul edilen vardiyalar.
    # Bu set:
    # - Agent ay içinde max kaç hafta gece/akşam vardiyası alabilir kuralında
    # - Fazla atama limitinde
    # - Excess cezasında
    # kullanılır.
    "GECE_AKSAM_VARDIYA_SET": {
        ("17:00", "01:00"),
        ("18:00", "02:00"),
        ("00:00", "08:00")
    },

    # Bir agent ay içinde en fazla kaç farklı haftada gece/akşam vardiyası alabilir?
    "MAX_NIGHT_WEEKS_PER_MONTH": 2,


    # -------------------------------------------------
    # MOLA / YEMEK YOĞUNLUK PENCERELERİ
    # -------------------------------------------------

    # Fazla kişi gerekiyorsa, bu saatleri kapsayan vardiyalar daha uygun kabul edilir.
    # Format:
    # (pencere_adi, baslangic, bitis, skor)
    #
    # Skor şu an objective'te direkt katsayı olarak kullanılmıyor;
    # skor > 0 ise vardiya "mola destek vardiyası" kabul ediliyor.
    "MOLA_YOGUNLUK_PENCERELERI": [
        ("ogle_yemek", "12:00", "13:30", 2),
        ("ikindi_mola", "15:00", "16:00", 1),
        ("aksam_yemek", "19:00", "20:00", 2),
    ],


    # -------------------------------------------------
    # FAZLA ATAMA ÜST LİMİTLERİ
    # -------------------------------------------------

    # Genel vardiyalarda talebin üstüne en fazla kaç kişi çıkılabilir?
    # Örn:
    # Talep = 50, GENEL_MAX_FAZLA_ATAMA = 15 ise
    # max atama = 65
    "GENEL_MAX_FAZLA_ATAMA": 15,

    # Gece/akşam vardiyalarında talebin üstüne en fazla kaç kişi çıkılabilir?
    # Örn:
    # Talep = 50, GECE_MAX_FAZLA_ATAMA = 3 ise
    # max atama = 53
    "GECE_MAX_FAZLA_ATAMA": 3,


    # -------------------------------------------------
    # OBJECTIVE AĞIRLIKLARI
    # -------------------------------------------------

    # Buffer alt sınırının altına düşme cezası.
    # En kritik cezalardan biri.
    "UNDER_BUFFER_W": 300000,

    # Buffer içinde kalsa bile talebin altında kalma cezası.
    # Bu değer eksikleri mesaiyle kapatma davranışını artırır.
    "MISSING_TO_REQUIRED_W": 50000,

    # Mesai cezası.
    # Düşük olursa model daha çok mesai kullanır.
    # Yüksek olursa mesai azalır ama eksik/under artabilir.
    "OVERTIME_W": 1000,

    # Gece/akşam vardiyasında fazla kişi cezası.
    # Geceye fazla kişi yığılmasını engellemek için yüksek tutulur.
    "EXCESS_GECE_AKSAM_W": 15000,

    # Normal vardiyada fazla kişi cezası.
    "EXCESS_NORMAL_W": 5000,

    # Mola/yemek destek vardiyasında fazla kişi cezası.
    # Fazla kişi gerekiyorsa buralara kayması için düşük tutulur.
    "EXCESS_MOLA_DESTEK_W": 1000,

    # Buffer üst sınırını aşma cezası.
    "OVER_BUFFER_W": 1000,
}


# -------------------------------------------------
# CONFIG DEĞERLERİNİ KOLAY ERİŞİM İÇİN DEĞİŞKENLERE AÇ
# -------------------------------------------------

BUFFER_RATE = CONFIG["BUFFER_RATE"]

NORMAL_WORK_DAYS = CONFIG["NORMAL_WORK_DAYS"]
MAX_OVERTIME_PER_MONTH = CONFIG["MAX_OVERTIME_PER_MONTH"]
IKINCI_MESAI_W = CONFIG["IKINCI_MESAI_W"]

GECE_AKSAM_VARDIYA_SET = CONFIG["GECE_AKSAM_VARDIYA_SET"]
MAX_NIGHT_WEEKS_PER_MONTH = CONFIG["MAX_NIGHT_WEEKS_PER_MONTH"]

MOLA_YOGUNLUK_PENCERELERI = CONFIG["MOLA_YOGUNLUK_PENCERELERI"]

GENEL_MAX_FAZLA_ATAMA = CONFIG["GENEL_MAX_FAZLA_ATAMA"]
GECE_MAX_FAZLA_ATAMA = CONFIG["GECE_MAX_FAZLA_ATAMA"]

UNDER_BUFFER_W = CONFIG["UNDER_BUFFER_W"]
MISSING_TO_REQUIRED_W = CONFIG["MISSING_TO_REQUIRED_W"]
OVERTIME_W = CONFIG["OVERTIME_W"]

EXCESS_GECE_AKSAM_W = CONFIG["EXCESS_GECE_AKSAM_W"]
EXCESS_NORMAL_W = CONFIG["EXCESS_NORMAL_W"]
EXCESS_MOLA_DESTEK_W = CONFIG["EXCESS_MOLA_DESTEK_W"]

OVER_BUFFER_W = CONFIG["OVER_BUFFER_W"]


print("CONFIG yüklendi.")

for key, value in CONFIG.items():
    print(f"{key}: {value}")
