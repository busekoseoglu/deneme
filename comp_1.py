# %% [HÜCRE 9] - CP-SAT MODEL + KARAR DEĞİŞKENLERİ
# Yeni mantık:
# x[agent, gün, vardiya] = 1 ise agent o gün o vardiyada çalışır
# work[agent, gün] = 1 ise agent o gün çalışır
# team_week_base[takım, hafta, vardiya] = takımın o hafta ana vardiyası
# exception[agent, gün] = agent o gün takımının haftalık base vardiyası dışında çalıştı mı
# shortage[gün, vardiya] = eksik kişi
# excess[gün, vardiya] = fazla kişi

from ortools.sat.python import cp_model
import pandas as pd
import numpy as np
from collections import defaultdict

model = cp_model.CpModel()

# -----------------------------
# Yardımcı setler
# -----------------------------

PLAN_GUNLER = sorted(PLAN_GUNLER)

ALL_VARDIYALAR = sorted(
    set(v for ds in PLAN_GUNLER for v in gun_vardiyalari.get(ds, []))
)

TAKIMLAR = sorted(df_tam["takim"].dropna().astype(str).unique().tolist())

agent_team = dict(
    zip(
        df_tam["agent_user_code"].astype(str).str.strip(),
        df_tam["takim"].astype(str).str.strip()
    )
)

def week_key(ds):
    d = pd.to_datetime(ds)
    iso = d.isocalendar()
    return f"{int(iso.year)}-W{int(iso.week):02d}"

day_week = {ds: week_key(ds) for ds in PLAN_GUNLER}
WEEKS = sorted(set(day_week.values()))

# takımın o hafta çalışabileceği vardiyalar
week_vardiyalari = defaultdict(set)
for ds in PLAN_GUNLER:
    wk = day_week[ds]
    for v in gun_vardiyalari.get(ds, []):
        week_vardiyalari[wk].add(v)

week_vardiyalari = {
    wk: sorted(list(vs))
    for wk, vs in week_vardiyalari.items()
}

print(f"agent sayısı: {len(AGENTS)}")
print(f"takım sayısı: {len(TAKIMLAR)}")
print(f"plan gün sayısı: {len(PLAN_GUNLER)}")
print(f"hafta sayısı: {len(WEEKS)} -> {WEEKS}")
print(f"vardiya sayısı: {len(ALL_VARDIYALAR)}")


# -----------------------------
# x değişkeni
# izinli günlerde x açılmayacak
# -----------------------------

x = {}

for a in AGENTS:
    izinli = izin_map.get(a, set())

    for ds in PLAN_GUNLER:
        d_date = pd.to_datetime(ds).date()

        if d_date in izinli:
            continue

        for v in gun_vardiyalari.get(ds, []):
            x[(a, ds, v)] = model.NewBoolVar(f"x_{a}_{ds}_{v}")


# -----------------------------
# work değişkeni
# -----------------------------

work = {}

for a in AGENTS:
    for ds in PLAN_GUNLER:
        work[(a, ds)] = model.NewBoolVar(f"work_{a}_{ds}")


# -----------------------------
# takım-hafta base vardiya değişkeni
# -----------------------------

team_week_base = {}

for t in TAKIMLAR:
    for wk in WEEKS:
        for v in week_vardiyalari[wk]:
            team_week_base[(t, wk, v)] = model.NewBoolVar(
                f"team_week_base_{t}_{wk}_{v}"
            )


# -----------------------------
# exception değişkeni
# -----------------------------

exception = {}

for a in AGENTS:
    for ds in PLAN_GUNLER:
        exception[(a, ds)] = model.NewBoolVar(f"exception_{a}_{ds}")


# -----------------------------
# shortage / excess değişkenleri
# -----------------------------

shortage = {}
excess = {}

MAX_AGENT = len(AGENTS)

for ds in PLAN_GUNLER:
    for v in gun_vardiyalari.get(ds, []):
        shortage[(ds, v)] = model.NewIntVar(0, MAX_AGENT, f"shortage_{ds}_{v}")
        excess[(ds, v)] = model.NewIntVar(0, MAX_AGENT, f"excess_{ds}_{v}")


print(f"x karar değişkeni: {len(x)}")
print(f"work değişkeni: {len(work)}")
print(f"team_week_base değişkeni: {len(team_week_base)}")
print(f"exception değişkeni: {len(exception)}")
print(f"shortage/excess kovası: {len(shortage)}")
