# %% [KONTROL] - AGENT AYLIK GÜN KIRILIMI KONTROLÜ
# Amaç:
# Her agent için plan ayındaki günlerin tamamı açıklanıyor mu kontrol etmek.
#
# Kontrol mantığı:
# Bir agent için ay içindeki her gün tek bir kategoriye düşmeli:
#
# 1) Çalıştı
# 2) İzinli
# 3) Resmi tatil çalışmadı
# 4) Arife çalışmadı
# 5) Hafta sonu / normal off
#
# Bu kategorilerin toplamı ay gün sayısına eşit olmalı.
#
# Örnek:
# Haziran ayı 30 gün ise:
# calistigi_gun + izinli_gun + resmi_tatil_calisilmayan_gun
# + arife_calisilmayan_gun + hafta_sonu_off_gun + normal_off_gun = 30
#
# Toplam 30 etmeyen agentlar ayrıca violation olarak gösterilir.

agent_month_control_rows = []

# Plan ayındaki toplam gün sayısı
AY_GUN_SAYISI = len(PLAN_GUNLER)

# Tarih setleri
resmi_tatil_set = set(pd.to_datetime(d).date() for d in RESMI_TATIL_GUNLERI)
arife_set = set(pd.to_datetime(d).date() for d in ARIFE_GUNLERI)

for _, row in df_tam.iterrows():
    
    a = str(row["agent_user_code"]).strip()
    
    agent_name = row.get("agent_name", None)
    teamleader_name = row.get("teamleader_name", None)
    working_main_group = row.get("working_main_group", None)
    line_based_main_group = row.get("line_based_main_group", None)
    
    calistigi_gun = 0
    izinli_gun = 0
    resmi_tatil_calisti_gun = 0
    resmi_tatil_calismadi_gun = 0
    arife_calisti_gun = 0
    arife_calismadi_gun = 0
    hafta_sonu_off_gun = 0
    normal_off_gun = 0
    
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
        # Eğer work değişkeni yoksa 0 kabul ediyoruz.
        
        worked = 0
        
        if (a, ds) in work:
            worked = int(solver.Value(work[(a, ds)]))
        
        # --------------------------------------------------
        # Agent o gün izinli mi?
        # --------------------------------------------------
        # izin_map, agent bazlı izin/off günlerini tutuyor.
        
        izinli = ds in izin_map.get(a, set())
        
        # --------------------------------------------------
        # Gün kategorisi
        # --------------------------------------------------
        # Öncelik sırası önemli:
        #
        # 1) Çalıştıysa çalıştı kategorisine gider.
        #    Resmi tatil/arife gününde çalıştıysa ayrıca özel sayaç artar.
        #
        # 2) Çalışmadıysa ve izinliyse izinli kategorisine gider.
        #
        # 3) Çalışmadıysa ve resmi tatilse resmi tatil çalışmadı olur.
        #
        # 4) Çalışmadıysa ve arifeyse arife çalışmadı olur.
        #
        # 5) Çalışmadıysa ve hafta sonuysa hafta sonu off olur.
        #
        # 6) Kalan çalışılmayan günler normal off olur.
        
        if worked == 1:
            calistigi_gun += 1
            
            if is_resmi_tatil:
                resmi_tatil_calisti_gun += 1
            
            if is_arife:
                arife_calisti_gun += 1
        
        else:
            if izinli:
                izinli_gun += 1
            
            elif is_resmi_tatil:
                resmi_tatil_calismadi_gun += 1
            
            elif is_arife:
                arife_calismadi_gun += 1
            
            elif is_weekend:
                hafta_sonu_off_gun += 1
            
            else:
                normal_off_gun += 1
    
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
        
        # Ek bilgi: çalışılan özel günler
        # Bunlar calistigi_gun içinde de vardır.
        # O yüzden toplam hesaba ayrıca eklenmez.
        "resmi_tatil_calisti_gun": resmi_tatil_calisti_gun,
        "arife_calisti_gun": arife_calisti_gun,
        
        # Kontrol
        "toplam_aciklanan_gun": toplam_aciklanan_gun,
        "kontrol_farki": kontrol_farki,
        "kontrol_ok": toplam_aciklanan_gun == AY_GUN_SAYISI
    })

agent_month_control_df = pd.DataFrame(agent_month_control_rows)

print("Agent aylık gün kontrolü oluşturuldu.")
print("Agent sayısı:", len(agent_month_control_df))
print("Ay gün sayısı:", AY_GUN_SAYISI)
print("Kontrol hatalı agent sayısı:", (~agent_month_control_df["kontrol_ok"]).sum())

display(agent_month_control_df.head(20))
