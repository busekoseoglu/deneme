import unicodedata

def kolon_temizle(c):
    c = str(c).strip().lower()
    c = unicodedata.normalize("NFKD", c)
    c = "".join(ch for ch in c if not unicodedata.combining(ch))
    c = c.replace(" ", "_")
    return c

df_off.columns = [kolon_temizle(c) for c in df_off.columns]
df_izin.columns = [kolon_temizle(c) for c in df_izin.columns]

print("izin_tipi" in df_off.columns)



gun_kolonlari = [
    c
    for c in df_off.columns
    if c.startswith("gun_")
]

df_off_long = df_off.melt(
    id_vars=["agent_user_code", "izin_tipi"],
    value_vars=gun_kolonlari,
    var_name="gun_kolonu",
    value_name="deger"
)
