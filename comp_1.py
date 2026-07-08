# %% [KONTROL] - AGENT AYLIK GÜN KIRILIMI KONTROLÜ
# Amaç:
# Her agent için plan ayındaki bütün günlerin tek bir ana kategoriye düşüp düşmediğini kontrol etmek.
#
# Ana kategori mantığı:
# Bir agent için her gün sadece 1 ana kategoriye yazılır:
#
# 1) Çalıştı
# 2) İzinli
# 3) Resmi tatil çalışmadı
# 4) Arife çalışmadı
# 5) Hafta sonu off
# 6) Normal off
#
# Bu ana kategorilerin toplamı AY_GUN_SAYISI etmeli.
#
# Ek bilgi:
# Resmi tatilde çalıştıysa "çalıştı" ana kategorisine girer.
# Ayrıca resmi_tatil_calisti_gun sayacı artar.
#
# Arifede çalıştıysa "çalıştı" ana kategorisine girer.
# Ayrıca arife_calisti_gun sayacı artar.
#
# Yani resmi_tatil_calisti_gun ve arife_calisti_gun toplam hesaba ayrıca eklenmez.
# Bunlar bilgi kolonudur.

agent_month_control_rows = []

# --------------------------------------------------
# 1) Plan ayındaki gün sayısı
# --------------------------------------------------
# Date aralığı üretmiyoruz.
# Model hangi günleri planladıysa onu kullanıyoruz.

AY_GUN_SAYISI = len(PLAN_GUNLER)

# --------------------------------------------------
# 2) Resmi tatil ve arife gün setleri
# --------------------------------------------------
# CONFIG içindeki tarihleri date formatına çeviriyoruz.
# PLAN_GUNLER zaten modelin planladığı günleri temsil ediyor.

resmi_tatil_set = set()
arife_set = set()

if "RESMI_TATIL_GUNLERI" in globals():
    resmi_tatil_set = set(
        pd.to_datetime(d).date()
        for d in RESMI_TATIL_GUNLERI
    )

if "ARIFE_GUNLERI" in globals():
    arife_set = set(
        pd.to_datetime(d).date()
        for d in ARIFE_GUNLERI
    )

# --------------------------------------------------
# 3) Agent bazlı gün kırılımı
# --------------------------------------------------

for _, row in df_tam.iterrows():

    a = str(row["agent_user_code"]).strip()

    agent_name = row.get("agent_name", None)
    teamleader_name = row.get("teamleader_name", None)
    working_main_group = row.get("working_main_group", None)
    line_based_main_group = row.get("line_based_main_group", None)

    # Ana gün kategorileri
    calistigi_gun = 0
    izinli_gun = 0
    resmi_tatil_calismadi_gun = 0
    arife_calismadi_gun = 0
    hafta_sonu_off_gun = 0
    normal_off_gun = 0

    # Ek bilgi kolonları
    resmi_tatil_calisti_gun = 0
    arife_calisti_gun = 0

    # Debug için hangi gün hangi kategoriye düştü görmek istersek
    gun_detaylari = []

    for ds in PLAN_GUNLER:

        ds_date = pd.to_datetime(ds).date()
        weekday = pd.to_datetime(ds).weekday()

        is_weekend = weekday in [5, 6]
        is_resmi_tatil = ds_date in resmi_tatil_set
        is_arife = ds_date in arife_set

        # --------------------------------------------------
        # Agent o gün çalıştı mı?
        # --------------------------------------------------
        # work[(a, ds)] varsa solver sonucundan bakıyoruz.
        # Yoksa 0 kabul ediyoruz.

        worked = 0

        if (a, ds) in work:
            worked = int(solver.Value(work[(a, ds)]))

        # --------------------------------------------------
        # Agent o gün izinli mi?
        # --------------------------------------------------
        # Öncelik agent_izinli_mi helper'ında.
        # Çünkü bu helper hem izin_map format farklarını hem de set/list/string
        # gibi durumları daha sağlam yönetiyor.
        #
        # Eğer helper yoksa direkt izin_map üzerinden kontrol ediyoruz.

        if "agent_izinli_mi" in globals():
            izinli = bool(agent_izinli_mi(a, ds))
        else:
            izinli = ds in izin_map.get(a, set())

        # --------------------------------------------------
        # Gün kategorisi
        # --------------------------------------------------
        # Öncelik sırası önemli:
        #
        # 1) Çalıştıysa ana kategori "çalıştı"
        # 2) Çalışmadıysa ve izinliyse "izinli"
        # 3) Çalışmadıysa ve resmi tatilse "resmi tatil çalışmadı"
        # 4) Çalışmadıysa ve arifeyse "arife çalışmadı"
        # 5) Çalışmadıysa ve hafta sonuysa "hafta sonu off"
        # 6) Kalan çalışılmayan günler "normal off"

        if worked == 1:

            calistigi_gun += 1
            ana_kategori = "calisti"

            if is_resmi_tatil:
                resmi_tatil_calisti_gun += 1

            if is_arife:
                arife_calisti_gun += 1

        else:

            if izinli:
                izinli_gun += 1
                ana_kategori = "izinli"

            elif is_resmi_tatil:
                resmi_tatil_calismadi_gun += 1
                ana_kategori = "resmi_tatil_calismadi"

            elif is_arife:
                arife_calismadi_gun += 1
                ana_kategori = "arife_calismadi"

            elif is_weekend:
                hafta_sonu_off_gun += 1
                ana_kategori = "hafta_sonu_off"

            else:
                normal_off_gun += 1
                ana_kategori = "normal_off"

        gun_detaylari.append({
            "agent_user_code": a,
            "date": ds,
            "weekday": weekday,
            "worked": worked,
            "izinli": izinli,
            "is_resmi_tatil": is_resmi_tatil,
            "is_arife": is_arife,
            "is_weekend": is_weekend,
            "ana_kategori": ana_kategori
        })

    # --------------------------------------------------
    # 4) Toplam kontrol
    # --------------------------------------------------
    # Ek bilgi kolonları toplam hesaba eklenmez.
    # Çünkü resmi tatilde/arifede çalıştıysa zaten calistigi_gun içinde sayıldı.

    toplam_aciklanan_gun = (
        calistigi_gun
        + izinli_gun
        + resmi_tatil_calismadi_gun
        + arife_calismadi_gun
        + hafta_sonu_off_gun
        + normal_off_gun
    )

    kontrol_farki = AY_GUN_SAYISI - toplam_aciklanan_gun

    agent_month_control_rows.append({
        "agent_user_code": a,
        "agent_name": agent_name,
        "teamleader_name": teamleader_name,
        "working_main_group": working_main_group,
        "line_based_main_group": line_based_main_group,

        "ay_gun_sayisi": AY_GUN_SAYISI,

        # Ana gün kırılımı
        "calistigi_gun": calistigi_gun,
        "izinli_gun": izinli_gun,
        "resmi_tatil_calismadi_gun": resmi_tatil_calismadi_gun,
        "arife_calismadi_gun": arife_calismadi_gun,
        "hafta_sonu_off_gun": hafta_sonu_off_gun,
        "normal_off_gun": normal_off_gun,

        # Ek bilgi
        "resmi_tatil_calisti_gun": resmi_tatil_calisti_gun,
        "arife_calisti_gun": arife_calisti_gun,

        # Kontrol
        "toplam_aciklanan_gun": toplam_aciklanan_gun,
        "kontrol_farki": kontrol_farki,
        "kontrol_ok": toplam_aciklanan_gun == AY_GUN_SAYISI
    })

agent_month_control_df = pd.DataFrame(agent_month_control_rows)

print("Agent aylık gün kontrolü oluşturuldu.")
print("Ay gün sayısı:", AY_GUN_SAYISI)
print("Agent sayısı:", len(agent_month_control_df))
print("Kontrol hatalı agent sayısı:", (~agent_month_control_df["kontrol_ok"]).sum())

display(
    agent_month_control_df
    .sort_values(["kontrol_ok", "agent_user_code"])
    .head(20)
)

# --------------------------------------------------
# 5) Hatalı agentlar
# --------------------------------------------------

agent_month_control_error_df = (
    agent_month_control_df[
        agent_month_control_df["kontrol_ok"] == False
    ]
    .sort_values(["kontrol_farki", "agent_user_code"])
)

display(agent_month_control_error_df)
