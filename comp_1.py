# %% [DEBUG] - PRESOLVE'DA PATLAYAN LINEAR KISITI BUL

# Solver logunda yazan constraint numarası:
SORUNLU_CONSTRAINT_INDEX = 54275

model_proto = model.Proto()

toplam_kisit_sayisi = len(
    model_proto.constraints
)

print(
    "Modeldeki toplam kısıt sayısı:",
    toplam_kisit_sayisi
)

if (
    SORUNLU_CONSTRAINT_INDEX < 0
    or SORUNLU_CONSTRAINT_INDEX >= toplam_kisit_sayisi
):
    raise IndexError(
        f"{SORUNLU_CONSTRAINT_INDEX} numaralı kısıt bulunamadı. "
        f"Modelde 0 ile {toplam_kisit_sayisi - 1} arasında "
        f"kısıt indeksleri var."
    )


sorunlu_constraint = (
    model_proto.constraints[
        SORUNLU_CONSTRAINT_INDEX
    ]
)

print(
    "Sorunlu constraint index:",
    SORUNLU_CONSTRAINT_INDEX
)

print(
    "Constraint adı:",
    sorunlu_constraint.name
)


# OR-Tools 9.15'te WhichOneof kullanılmıyor.
# Solver logundaki kısıt linear olduğu için has_linear kontrolü yapıyoruz.

if not sorunlu_constraint.has_linear():

    print(
        "Bu constraint linear değil."
    )

    print(
        sorunlu_constraint
    )

else:

    linear_constraint = (
        sorunlu_constraint.linear
    )

    var_indices = list(
        linear_constraint.vars
    )

    coeffs = list(
        linear_constraint.coeffs
    )

    constraint_domain = list(
        linear_constraint.domain
    )

    print(
        "Constraint domain:",
        constraint_domain
    )

    print(
        "Constraint içindeki değişken sayısı:",
        len(var_indices)
    )


    sorunlu_var_rows = []

    for var_index, coefficient in zip(
        var_indices,
        coeffs
    ):

        var_proto = (
            model_proto.variables[
                var_index
            ]
        )

        sorunlu_var_rows.append({
            "constraint_index": (
                SORUNLU_CONSTRAINT_INDEX
            ),
            "var_index": var_index,
            "var_name": var_proto.name,
            "coefficient": coefficient,
            "original_domain": list(
                var_proto.domain
            ),
        })


    sorunlu_constraint_vars_df = (
        pd.DataFrame(
            sorunlu_var_rows
        )
    )

    display(
        sorunlu_constraint_vars_df
    )
