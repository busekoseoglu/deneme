# -------------------------------------------------
# PM DEĞERLERİNİ CAP'LE
# -------------------------------------------------
# Amaç:
# Geçen ay çok yüksek mesai/gece/hafta sonu sayısı olan agentlarda
# objective cezası aşırı büyümesin.
#
# Örn:
# pm_hafta_sonu = 8 olsa bile cap 4 ise model bunu 4 gibi görür.
# Böylece geçmiş ay etkisi olur ama coverage'ı bozacak kadar baskın olmaz.

PM_MESAI_CAP = 2
PM_GECE_CAP = 4
PM_HAFTA_SONU_CAP = 4

pm_mesai_map = {
    a: min(v, PM_MESAI_CAP)
    for a, v in pm_mesai_map.items()
}

pm_gece_map = {
    a: min(v, PM_GECE_CAP)
    for a, v in pm_gece_map.items()
}

pm_hafta_sonu_map = {
    a: min(v, PM_HAFTA_SONU_CAP)
    for a, v in pm_hafta_sonu_map.items()
}

print("Cap sonrası PM mesai max:", max(pm_mesai_map.values()) if pm_mesai_map else 0)
print("Cap sonrası PM gece max:", max(pm_gece_map.values()) if pm_gece_map else 0)
print("Cap sonrası PM hafta sonu max:", max(pm_hafta_sonu_map.values()) if pm_hafta_sonu_map else 0)