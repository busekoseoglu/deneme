# --------------------------------------------------
# PARTIAL WEEK FAZLA ATAMA PARAMETRELERİ
# --------------------------------------------------
# Amaç:
# Ay başı / ay sonu yarım haftalarda model fazla kişileri bu günlere yığmasın.
#
# Örn:
# Haziran 2026'da 2026-W27 sadece 29-30 Haziran olarak görünüyor.
# Bu hafta aslında Temmuz ile devam ettiği için Haziran modelinde
# bu iki güne fazla kişi yığılmamalı.
#
# 0 seçersek:
# partial week günlerinde assigned <= required olur.
#
# Eğer model infeasible olursa 1 veya 2 denenebilir.
"PARTIAL_WEEK_MAX_FAZLA_ATAMA": 0,


PARTIAL_WEEK_MAX_FAZLA_ATAMA = CONFIG["PARTIAL_WEEK_MAX_FAZLA_ATAMA"]


# %% [HÜCRE] - PARTIAL WEEK HELPER
# Amaç:
# Ay başı veya ay sonunda modelin sadece bir kısmını gördüğü haftaları bulmak.
#
# Örnek:
# Haziran 2026:
# 2026-W27 haftası sadece 29-30 Haziran olarak modelde var.
# Bu yüzden partial week kabul edilir.
#
# Bu haftalarda:
# - Haftalık hedef skip edilir.
# - Fazla atama üst limiti sıkılaştırılır.
# - Coverage yine çalışır.

partial_weeks = set()
week_normal_weekday_count = {}

for wk in WEEKS:
    
    week_days_list = week_days[wk]
    
    normal_weekdays_this_week = [
        ds
        for ds in week_days_list
        if pd.to_datetime(ds).weekday() in [0, 1, 2, 3, 4]
    ]
    
    week_normal_weekday_count[wk] = len(normal_weekdays_this_week)
    
    if len(normal_weekdays_this_week) < FULL_WEEKDAY_COUNT:
        partial_weeks.add(wk)

print("Partial week sayısı:", len(partial_weeks))
print("Partial weeks:", sorted(partial_weeks))

partial_week_debug_df = pd.DataFrame([
    {
        "week": wk,
        "normal_weekday_count": week_normal_weekday_count[wk],
        "is_partial_week": wk in partial_weeks
    }
    for wk in WEEKS
])

display(partial_week_debug_df)



# %% [HÜCRE] - FAZLA ATAMA ÜST LİMİTİ
# Amaç:
# Her gün-vardiya için talebin üstüne en fazla kaç kişi çıkılabilir?
#
# Yeni ek:
# Partial week günlerinde fazla atama limiti sıkılaştırılır.
# Böylece model ay sonundaki yarım haftaya fazla kişileri yığamaz.

fazla_atama_cap_constraints = 0
arife_cap_relax_rows = []

for ds in PLAN_GUNLER:
    for v in gun_vardiyalari.get(ds, []):
        
        required = int(talep[(ds, v)])
        
        assigned = sum(
            x[(a, ds, v)]
            for a in AGENTS
            if (a, ds, v) in x
        )
        
        # --------------------------------------------------
        # Normal / partial week fazla atama limiti
        # --------------------------------------------------
        # Normal haftada mevcut fazla_atama_ust_limit kullanılır.
        # Partial week'te ise limit daha sıkıdır.
        
        wk = day_week[ds]
        
        if wk in partial_weeks:
            max_fazla = PARTIAL_WEEK_MAX_FAZLA_ATAMA
        else:
            max_fazla = fazla_atama_ust_limit.get((ds, v), GENEL_MAX_FAZLA_ATAMA)
        
        # --------------------------------------------------
        # ARİFE ÖZEL 09-13 VARDİYASI
        # --------------------------------------------------
        # Arife özel vardiyasında kısıtlı agentlar zorunlu atanabildiği için
        # max_fazla gerektiğinde esnetilir.
        
        if (ds, v) in arife_ozel_vardiyalar:
            
            forced_count = 0
            
            for a in tatil_kisitli_agents:
                a = str(a).strip()
                
                if ds in izin_map.get(a, set()):
                    continue
                
                if (a, ds, v) in x:
                    forced_count += 1
            
            min_needed_extra = max(0, forced_count - required)
            
            if min_needed_extra > max_fazla:
                arife_cap_relax_rows.append({
                    "date": ds,
                    "shift": v,
                    "required": required,
                    "old_max_fazla": max_fazla,
                    "forced_count": forced_count,
                    "new_max_fazla": min_needed_extra
                })
                
                max_fazla = min_needed_extra
        
        # --------------------------------------------------
        # Fazla atama üst limit constraint
        # --------------------------------------------------
        # assigned <= required + max_fazla
        #
        # Partial week için max_fazla genelde 0 olduğu için:
        # assigned <= required olur.
        
        model.Add(
            assigned <= required + max_fazla
        )
        
        fazla_atama_cap_constraints += 1

print("Fazla atama üst limit kısıtı:", fazla_atama_cap_constraints)
print("Genel max fazla atama:", GENEL_MAX_FAZLA_ATAMA)
print("Gece/akşam max fazla atama:", GECE_MAX_FAZLA_ATAMA)
print("Partial week max fazla atama:", PARTIAL_WEEK_MAX_FAZLA_ATAMA)

if arife_cap_relax_rows:
    arife_cap_relax_df = pd.DataFrame(arife_cap_relax_rows)
    print("Arife özel 09-13 cap esnetilen satır sayısı:", len(arife_cap_relax_df))
    display(arife_cap_relax_df)
