# %% [OBJECTIVE HAZIRLIK] - SOFT OFF TALEBİ CEZA TERİMLERİ
#
# Mantık:
# - off_t2 her zaman HARD olduğu için burada yer almaz.
# - off_t HARD açıksa burada yer almaz.
# - Sadece SOFT çalışan off_t talepleri için:
#       work[a, ds] = 0  -> talep karşılandı, ceza 0
#       work[a, ds] = 1  -> talep karşılanmadı, ceza oluşur
#
# Bu hücre mevcut objective_terms listesine doğrudan dokunmaz.
# Objective hücresinde kullanılacak listeyi hazırlar.

OFF_TALEP_CEZA_W = globals().get("OFF_TALEP_CEZA_W", 100_000)

soft_off_objective_terms = []
soft_off_objective_debug_rows = []

# Fonksiyonlardan üretilmiş ceza değişkenlerinin varlığını zorunlu kontrol et
if "off_talep_ceza_terms" not in globals():
    raise NameError(
        "off_talep_ceza_terms oluşturulmamış. "
        "Önce haftalık çalışma + OFF talebi modüllerini çalıştır."
    )

if off_talep_ceza_terms is None:
    raise ValueError("off_talep_ceza_terms None geldi.")

# off_talep_ceza_terms içinde:
# 1 - off_talep_karsilandi[a, ds]
# ifadeleri bulunuyor.
for ceza_var in off_talep_ceza_terms:
    soft_off_objective_terms.append(
        OFF_TALEP_CEZA_W * ceza_var
    )

print("Soft OFF ceza terimi sayısı:", len(soft_off_objective_terms))
print("Soft OFF ceza ağırlığı:", OFF_TALEP_CEZA_W)
