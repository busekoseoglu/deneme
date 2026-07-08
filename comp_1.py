# %% [ÇIKTI] - AGENT GÜN BAZLI ROSTER LONG FORMAT
# Amaç:
# Her agent'ın her gün hangi vardiyada çalıştığını veya neden çalışmadığını görmek.
#
# Bu tablo kontrol tablolarının temel datasıdır.
#
# Durum önceliği:
# 1) Çalıştıysa: ÇALIŞTI
# 2) Çalışmadıysa ve izin_map içinde ise: İZİN
# 3) Çalışmadıysa ve resmi tatil ise: RESMİ_TATİL_OFF
# 4) Çalışmadıysa ve arife ise: ARİFE_OFF
# 5) Çalışmadıysa ve hafta sonu ise: HAFTA_SONU_OFF
# 6) Diğer çalışmadığı günler: NORMAL_OFF

roster_rows = []

resmi_tatil_set = set(pd.to_datetime(d).date() for d in RESMI_TATIL_GUNLERI)
arife_set = set(pd.to_datetime(d).date() for d in ARIFE_GUNLERI)

for _, row in df_tam.iterrows():
    
    a = str(row["agent_user_code"]).strip()
    
    agent_name = row.get("agent_name", None)
    teamleader_name = row.get("teamleader_name", None)
    working_main_group = row.get("working_main_group", None)
    line_based_main_group = row.get("line_based_main_group", None)
    
    for ds in PLAN_GUNLER:
        
        ds_date = pd.to_datetime(ds).date()
        weekday_no = pd.to_datetime(ds).weekday()
        gun_adi = pd.to_datetime(ds).day_name()
        
        is_weekend = weekday_no in [5, 6]
        is_resmi_tatil = ds_date in resmi_tatil_set
        is_arife = ds_date in arife_set
        izinli = ds in izin_map.get(a, set())
        
        assigned_shift = None
        assigned_start = None
        assigned_end = None
        
        # --------------------------------------------------
        # Agent o gün hangi vardiyaya atanmış?
        # --------------------------------------------------
        # x[(a, ds, v)] = 1 olan vardiyayı buluyoruz.
        
        for v in gun_vardiyalari.get(ds, []):
            if (a, ds, v) in x and solver.Value(x[(a, ds, v)]) == 1:
                assigned_shift = v
                
                if (ds, v) in saat:
                    assigned_start = saat[(ds, v)][0]
                    assigned_end = saat[(ds, v)][1]
                
                break
        
        # --------------------------------------------------
        # Durum etiketi
        # --------------------------------------------------
        
        if assigned_shift is not None:
            durum = "ÇALIŞTI"
            hucre_degeri = assigned_shift
        
        else:
            if izinli:
                durum = "İZİN"
                hucre_degeri = "İZİN"
            
            elif is_resmi_tatil:
                durum = "RESMİ_TATİL_OFF"
                hucre_degeri = "RT_OFF"
            
            elif is_arife:
                durum = "ARİFE_OFF"
                hucre_degeri = "ARİFE_OFF"
            
            elif is_weekend:
                durum = "HAFTA_SONU_OFF"
                hucre_degeri = "HS_OFF"
            
            else:
                durum = "NORMAL_OFF"
                hucre_degeri = "OFF"
        
        roster_rows.append({
            "agent_user_code": a,
            "agent_name": agent_name,
            "teamleader_name": teamleader_name,
            "working_main_group": working_main_group,
            "line_based_main_group": line_based_main_group,
            "date": ds_date,
            "gun": gun_adi,
            "weekday_no": weekday_no,
            "vardiya": assigned_shift,
            "baslangic": assigned_start,
            "bitis": assigned_end,
            "durum": durum,
            "roster_hucre": hucre_degeri,
            "is_weekend": is_weekend,
            "is_resmi_tatil": is_resmi_tatil,
            "is_arife": is_arife,
            "izinli_mi": izinli
        })

df_roster_long = pd.DataFrame(roster_rows)

print("Roster long oluşturuldu.")
print("Satır sayısı:", len(df_roster_long))
print("Agent sayısı:", df_roster_long["agent_user_code"].nunique())
print("Gün sayısı:", df_roster_long["date"].nunique())

display(df_roster_long.head(20))
