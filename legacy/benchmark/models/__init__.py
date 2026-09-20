"""The model universe, and the 2x2 it is designed to fill.

                     |  proportional hazards  |  non-proportional
    -----------------+------------------------+-------------------
    linear           |  CoxPH, CoxNet,        |  -
                     |  Cloglog               |
    nonlinear        |  BoostedCox, DeepSurv, |  RSF, CoxTime,
                     |  Cloglog-theory        |  DeepHit, CBNN

Reading a result off the leaderboard means reading a move within that table, not
a name at the top of it.
"""

from .base import FitContext, SurvivalModel
from .km import KaplanMeier
from .cox import CoxPH
from .coxnet import CoxNet
from .cloglog import DiscreteCloglog
from .rsf import RSF
from .boosted_cox import BoostedCox


def build_registry(cfg: dict) -> dict:
    """Instantiate every model. Deep models are imported lazily so that the
    classical half of the benchmark still runs on a machine without torch."""
    t = cfg["tuning"]
    reg = {
        "KM": KaplanMeier(),
        "CoxPH": CoxPH(),
        "CoxNet": CoxNet(),
        "Cloglog": DiscreteCloglog(),
        "Cloglog-theory": DiscreteCloglog(
            enhanced=True,
            spline_cols=["log_value", "vn_market_share"],
            interactions=[("exp_dest", "n_products_to_c_lag"),
                          ("exp_prod", "n_markets_for_p_lag"),
                          ("exp_prod", "proximity_hs2_lag")]),
        "RSF": RSF(),
        "BoostedCox": BoostedCox(),
    }
    kw = dict(max_epochs=t["deep_max_epochs"], patience=t["deep_patience"],
              batch_size=t["deep_batch_size"])
    try:
        from .deep import DeepSurv, CoxTime, DeepHit
        from .cbnn import CBNN
        reg.update({"DeepSurv": DeepSurv(**kw), "CoxTime": CoxTime(**kw),
                    "DeepHit": DeepHit(**kw), "CBNN": CBNN(**kw)})
    except ImportError as exc:      # pragma: no cover
        print(f"  [warn] deep models unavailable: {exc}")
    return reg


__all__ = ["FitContext", "SurvivalModel", "build_registry"]
