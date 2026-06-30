# %% [CONFIG] - MODEL PARAMETRELERİ
# Bu hücre modelde kullanılan tüm ayarlanabilir parametreleri tek yerde toplar.
# Parametre değiştirmek istediğimizde kodun farklı yerlerine gitmeden sadece burayı güncelleriz.

CONFIG = {
    # -------------------------------------------------
    # Coverage / talep toleransı
    # -------------------------------------------------

    # Alt tarafta talebin kaç kişi altına kadar tolerans verilecek?
    # Örn: Talep 50, ALT_TOLERANS_KISI = 5 ise alt sınır 45 olur.
    "ALT_TOLERANS_KISI": 5,

    # Üst tarafta talebin yüzde kaç üstüne kadar buffer verilecek?
    # Örn: Talep 50, UST_BUFFER_RATE = 0.05 ise üst sınır ceil(52.5)=53 olur.
    "UST_BUFFER_RATE": 0.05,


    # -------------------------------------------------
    # Mesai kuralları
    # -------------------------------------------------

    # Haftalık normal çalışma günü
    "NORMAL_WORK_DAYS": 5,

    # Bir agent ayda en fazla kaç mesai alabilir?
    "MAX_OVERTIME_PER_MONTH": 2,

    # 2. mesaiyi ekstra cezalandırmak için ağırlık.
    # Amaç: Mesai mümkün olduğunca farklı agentlara dağılsın.
    "IKINCI_MESAI_W": 50000,


    # -------------------------------------------------
    # Gece / akşam vardiyası kuralları
    # -------------------------------------------------

    # Gece/akşam vardiyası olarak kabul edilen vardiyalar.
    # Bunlar için hem max 2 hafta kuralı hem de fazla atama limiti uygulanabilir.
    "GECE_AKSAM_VARDIYA_SET": {
        ("17:00", "01:00"),
        ("18:00", "02:00"),
        ("00:00", "08:00")
    },

    # Bir agent ayda en fazla kaç farklı hafta gece/akşam vardiyası alabilir?
    "MAX_NIGHT_WEEKS_PER_MONTH": 2,


    # -------------------------------------------------
    # Mola / yemek yoğunluk pencereleri
    # -------------------------------------------------

    # Fazla kişi gerekiyorsa, bu saatleri kapsayan vardiyalar daha uygun kabul edilir.
    # Format:
    # (pencere_adi, baslangic, bitis, skor)
    "MOLA_YOGUNLUK_PENCERELERI": [
        ("ogle_yemek", "12:00", "13:30", 2),
        ("ikindi_mola", "15:00", "16:00", 1),
        ("aksam_yemek", "19:00", "20:00", 2),
    ],


    # -------------------------------------------------
    # Fazla atama üst limitleri
    # -------------------------------------------------

    # Genel vardiyalarda talebin üstüne en fazla kaç kişi çıkılabilir?
    "GENEL_MAX_FAZLA_ATAMA": 15,

    # Gece/akşam vardiyalarında talebin üstüne en fazla kaç kişi çıkılabilir?
    "GECE_MAX_FAZLA_ATAMA": 3,


    # -------------------------------------------------
    # Objective ağırlıkları
    # -------------------------------------------------

    # Talep - ALT_TOLERANS_KISI altına düşmek çok pahalı.
    "UNDER_BUFFER_W": 300000,

    # Mesai cezası.
    # Çok düşerse mesai artar, çok yükselirse eksikler kalabilir.
    "OVERTIME_W": 1000,

    # Gece/akşam vardiyasında fazla kişi cezası.
    "EXCESS_GECE_AKSAM_W": 15000,

    # Normal vardiyada fazla kişi cezası.
    "EXCESS_NORMAL_W": 5000,

    # Mola/yemek destek vardiyasında fazla kişi cezası.
    "EXCESS_MOLA_DESTEK_W": 1000,

    # Üst buffer sınırını aşma cezası.
    "OVER_BUFFER_W": 1000,
}


# Kolay erişim için değişkenlere açıyoruz.
ALT_TOLERANS_KISI = CONFIG["ALT_TOLERANS_KISI"]
UST_BUFFER_RATE = CONFIG["UST_BUFFER_RATE"]

NORMAL_WORK_DAYS = CONFIG["NORMAL_WORK_DAYS"]
MAX_OVERTIME_PER_MONTH = CONFIG["MAX_OVERTIME_PER_MONTH"]
IKINCI_MESAI_W = CONFIG["IKINCI_MESAI_W"]

GECE_AKSAM_VARDIYA_SET = CONFIG["GECE_AKSAM_VARDIYA_SET"]
MAX_NIGHT_WEEKS_PER_MONTH = CONFIG["MAX_NIGHT_WEEKS_PER_MONTH"]

MOLA_YOGUNLUK_PENCERELERI = CONFIG["MOLA_YOGUNLUK_PENCERELERI"]

GENEL_MAX_FAZLA_ATAMA = CONFIG["GENEL_MAX_FAZLA_ATAMA"]
GECE_MAX_FAZLA_ATAMA = CONFIG["GECE_MAX_FAZLA_ATAMA"]

UNDER_BUFFER_W = CONFIG["UNDER_BUFFER_W"]
OVERTIME_W = CONFIG["OVERTIME_W"]
EXCESS_GECE_AKSAM_W = CONFIG["EXCESS_GECE_AKSAM_W"]
EXCESS_NORMAL_W = CONFIG["EXCESS_NORMAL_W"]
EXCESS_MOLA_DESTEK_W = CONFIG["EXCESS_MOLA_DESTEK_W"]
OVER_BUFFER_W = CONFIG["OVER_BUFFER_W"]


print("CONFIG yüklendi.")
for k, v in CONFIG.items():
    print(k, "=", v)
