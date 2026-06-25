# %% [HÜCRE 13] - SABAH ÇALIŞANLAR
# sabah_calisir_flg = 1 olan agentlar bitişi 20:00 sonrası olan vardiyalarda çalışamaz.

def dakika(t):
    s = str(t).strip()
    h, m = s.split(":")
    h = int(h)
    m = int(m)
    return h * 60 + m

LIMIT = dakika("20:00")

sabah_agents = set()

for _, row in df_tam.iterrows():
    if pd.to_numeric(row.get("sabah_calisir_flg", 0), errors="coerce") == 1:
        sabah_agents.add(str(row["agent_user_code"]).strip())

n = 0

for a in sabah_agents:
    for ds in PLAN_GUNLER:
        for v in gun_vardiyalari.get(ds, []):
            if (a, ds, v) not in x:
                continue

            bas, bit = saat[(ds, v)]

            # gece dönen vardiyalarda bitiş başlangıçtan küçük olabilir
            bas_dk = dakika(bas)
            bit_dk = dakika(bit)

            # bitiş 00:00 sonrası ise normalize et
            if bit_dk <= bas_dk:
                bit_dk += 24 * 60

            uygun = bit_dk <= LIMIT

            if not uygun:
                model.Add(x[(a, ds, v)] == 0)
                n += 1

print(f"sabah çalışan agent: {len(sabah_agents)} | yasaklanan agent-gün-vardiya: {n}")
