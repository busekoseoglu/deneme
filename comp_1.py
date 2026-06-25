# %% SOLVE - DAHA UZUN SÜRE

solver = cp_model.CpSolver()

solver.parameters.max_time_in_seconds = 1200
solver.parameters.num_search_workers = 8
solver.parameters.log_search_progress = True

status = solver.Solve(model)

status_map = {
    cp_model.OPTIMAL: "OPTIMAL",
    cp_model.FEASIBLE: "FEASIBLE",
    cp_model.INFEASIBLE: "INFEASIBLE",
    cp_model.MODEL_INVALID: "MODEL_INVALID",
    cp_model.UNKNOWN: "UNKNOWN"
}

print("status:", status_map.get(status, status))

if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
    print("objective:", solver.ObjectiveValue())
    print("best bound:", solver.BestObjectiveBound())
    print("gap:", solver.ObjectiveValue() - solver.BestObjectiveBound())
    print("wall time:", solver.WallTime())
