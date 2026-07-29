# %% [DEBUG] - PRESOLVE'DA PATLAYAN KISITIN DEĞİŞKENLERİNİ BUL

# Solver logunda görünen constraint numarası
SORUNLU_CONSTRAINT_INDEX = 54275

model_proto = model.Proto()

if SORUNLU_CONSTRAINT_INDEX >= len(model_proto.constraints):
    raise IndexError(
        f"Modelde yalnızca {len(model_proto.constraints)} kısıt var. "
        f"{SORUNLU_CONSTRAINT_INDEX} numaralı kısıt bulunamadı."
    )

sorunlu_constraint = model_proto.constraints[
    SORUNLU_CONSTRAINT_INDEX
]

constraint_type = sorunlu_constraint.WhichOneof(
    "constraint"
)

print(
    "Sorunlu constraint index:",
    SORUNLU_CONSTRAINT_INDEX
)

print(
    "Constraint tipi:",
    constraint_type
)

print(
    "Constraint adı:",
    sorunlu_constraint.name
)


sorunlu_var_rows = []

if constraint_type == "linear":

    var_indices = list(
        sorunlu_constraint.linear.vars
    )

    coeffs = list(
        sorunlu_constraint.linear.coeffs
    )

    constraint_domain = list(
        sorunlu_constraint.linear.domain
    )

    print(
        "Constraint domain:",
        constraint_domain
    )

    for var_index, coeff in zip(
        var_indices,
        coeffs
    ):

        var_proto = model_proto.variables[
            var_index
        ]

        sorunlu_var_rows.append({
            "var_index": var_index,
            "var_name": var_proto.name,
            "coefficient": coeff,
            "original_domain": list(
                var_proto.domain
            ),
        })

else:

    print(
        sorunlu_constraint
    )


sorunlu_constraint_vars_df = pd.DataFrame(
    sorunlu_var_rows
)

display(
    sorunlu_constraint_vars_df
)
