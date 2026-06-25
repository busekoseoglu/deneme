# %% [HÜCRE 10] - COVERAGE KISITI - %10 BUFFERLI
# Talebin %10 altı ve %10 üstü cezasız kabul edilir.
# Buffer dışına çıkılırsa under_buffer / over_buffer açılır.
#
# Örnek:
# Talep 50 ise lower=45, upper=55
# Atanan 46 ise ceza yok
# Atanan 55 ise ceza yok
# Atanan 43 ise under_buffer=2
# Atanan 58 ise over_buffer=3

import math

BUFFER_RATE = 0.10

coverage_lower = {}
coverage_upper = {}

coverage_constraints = 0

for ds in PLAN_GUNLER:
    for v in gun_vardiyalari.get(ds, []):

        required = int(talep[(ds, v)])

        lower_req = math.floor(required * (1 - BUFFER_RATE))
        upper_req = math.ceil(required * (1 + BUFFER_RATE))

        coverage_lower[(ds, v)] = lower_req
        coverage_upper[(ds, v)] = upper_req

        assigned = sum(
            x[(a, ds, v)]
            for a in AGENTS
            if (a, ds, v) in x
        )

        model.Add(
            assigned + under_buffer[(ds, v)] >= lower_req
        )

        model.Add(
            assigned - over_buffer[(ds, v)] <= upper_req
        )

        coverage_constraints += 2

print(f"coverage buffer constraint sayısı: {coverage_constraints}")
print(f"buffer oranı: %{int(BUFFER_RATE * 100)}")
