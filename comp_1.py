# Her lokasyondaki toplam agent sayısı
lokasyon_agent_sayisi = {
    loc: len({
        str(a).strip()
        for a in AGENTS
        if agent_location_map.get(str(a).strip()) == loc
    })
    for loc in oran_lokasyonlari
}

print("Lokasyon agent sayıları:", lokasyon_agent_sayisi)
