import gurobipy as gp
from gurobipy import GRB
import pandas as pd

def optimise_schedule(df_staff: pd.DataFrame, df_demand: pd.DataFrame) -> pd.DataFrame:
    """
    Build and solve a workforce optimisation model based on user inputs.

    df_staff : DataFrame with columns ['name', 'cost', 'min_days', 'max_days']
    df_demand: DataFrame with columns ['day', 'required']
    Returns  : DataFrame of optimal work schedule (1=work, 0=off)
    """

    # Extract data into dictionaries
    staff = df_staff["Staff Name"].tolist()
    days = df_demand["Day"].tolist()
    cost = dict(zip(df_staff["Staff Name"], df_staff["Staff Cost"]))
    min_days = dict(zip(df_staff["Staff Name"], df_staff["Min Working Days per Week"]))
    max_days = dict(zip(df_staff["Staff Name"], df_staff["Max Working Days per Week"]))
    required = dict(zip(df_demand["Day"], df_demand["Staff Required"]))

    # Initialize model
    model = gp.Model("Workforce Optimisation")

    # Add a variable: x[i,d] = 1 if staff i works on day d, else 0
    x = model.addVars(staff, days, vtype=GRB.BINARY, name="work")

    # Objective function to minimize total labor cost
    model.setObjective(
        gp.quicksum(cost[s] * x[s, d] for s in staff for d in days),
        GRB.MINIMIZE,
    )

    # Constraint: working day limits per employee
    for s in staff:
        model.addConstr(gp.quicksum(x[s, d] for d in days) >= min_days[s], name=f"Staff {s} min days")
        model.addConstr(gp.quicksum(x[s, d] for d in days) <= max_days[s], name=f"Staff {s} max days")

    # Constraint: daily staff needed
    for d in days:
        model.addConstr(gp.quicksum(x[s, d] for s in staff) == required[d], name=f"Day {d} staff needed")

    # Optimisation
    model.optimize()

    # Prepare result DataFrame
    result = pd.DataFrame(0, index=staff, columns=days)
    total_cost = 0

    # Handle infeasibility
    if model.status != GRB.OPTIMAL:
        print(f"Model not solved optimally. Status: {model.status}")

        # Return a message DataFrame instead of crashing
        return pd.DataFrame({
            "Message": ["No feasible solution found. Please check staff limits or daily requirements."]
        })

    else:

        for s in staff:
            for d in days:
                result.loc[s, d] = int(x[s, d].X)
            result.loc[s, "Total Days"] = int(result.loc[s, days].sum())
            result.loc[s, "Cost"] = int(result.loc[s, "Total Days"]) * int(cost[s])
            total_cost += result.loc[s, "Cost"]

        # Add row for daily total staff count
        daily_totals = [int(result[d].sum()) for d in days]
        total_days_sum = sum(daily_totals)  # total staff-days in the week

        # Add summary row with daily totals + total_days_sum + total_cost
        summary_row = pd.DataFrame(
            [daily_totals + [total_days_sum, int(total_cost)]],
            columns=result.columns,
            index=["Total"]
        )

        result = pd.concat([result, summary_row])

    return result
