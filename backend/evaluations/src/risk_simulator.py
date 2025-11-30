# src/risk_simulator.py
import numpy as np
from typing import Dict, Any

def run_monte_carlo(
    base_cost: float,
    cost_cv: float = 0.2,
    base_duration_days: float = 365,
    duration_cv: float = 0.25,
    n_sims: int = 5000,
    random_seed: int = 42
) -> Dict[str, Any]:
    """
    Monte Carlo simulation for cost and schedule risk.

    - base_cost: nominal total cost (INR lakhs / crores as per your unit)
    - cost_cv: coefficient of variation for cost (std / mean)
    - base_duration_days: planned duration in days
    - duration_cv: coefficient of variation for duration
    - n_sims: number of simulation runs

    Returns summary statistics and percentile estimates.
    """
    rng = np.random.default_rng(random_seed)

    # Use log-normal model to keep values positive and model multiplicative shocks
    # derive mu, sigma for lognormal from mean=m and cv
    def lognorm_params(mean, cv):
        sigma = np.sqrt(np.log(1 + cv**2))
        mu = np.log(mean) - 0.5 * sigma**2
        return mu, sigma

    mu_c, sigma_c = lognorm_params(base_cost, cost_cv)
    mu_d, sigma_d = lognorm_params(base_duration_days, duration_cv)

    costs = rng.lognormal(mean=mu_c, sigma=sigma_c, size=n_sims)
    durations = rng.lognormal(mean=mu_d, sigma=sigma_d, size=n_sims)

    # compute overruns
    cost_overrun_pct = (costs - base_cost) / base_cost * 100.0
    duration_overrun_pct = (durations - base_duration_days) / base_duration_days * 100.0

    def pctile(arr, p):
        return float(np.percentile(arr, p))

    summary = {
        "n_sims": n_sims,
        "cost": {
            "mean": float(np.mean(costs)),
            "std": float(np.std(costs)),
            "p10": pctile(costs, 10),
            "p50": pctile(costs, 50),
            "p90": pctile(costs, 90),
            "overrun_pct_mean": float(np.mean(cost_overrun_pct)),
            "overrun_pct_p90": pctile(cost_overrun_pct, 90)
        },
        "duration": {
            "mean_days": float(np.mean(durations)),
            "std_days": float(np.std(durations)),
            "p10_days": pctile(durations, 10),
            "p50_days": pctile(durations, 50),
            "p90_days": pctile(durations, 90),
            "overrun_pct_mean": float(np.mean(duration_overrun_pct)),
            "overrun_pct_p90": pctile(duration_overrun_pct, 90)
        },
        "cost_overrun_distribution_pct": {
            "p10": pctile(cost_overrun_pct, 10),
            "p50": pctile(cost_overrun_pct, 50),
            "p90": pctile(cost_overrun_pct, 90)
        },
        "duration_overrun_distribution_pct": {
            "p10": pctile(duration_overrun_pct, 10),
            "p50": pctile(duration_overrun_pct, 50),
            "p90": pctile(duration_overrun_pct, 90)
        }
    }
    return summary
