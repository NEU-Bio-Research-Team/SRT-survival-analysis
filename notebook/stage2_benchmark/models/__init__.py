"""Model registry: id -> adapter class (imports are lazy so a D-only run never
loads torch)."""

from __future__ import annotations

import importlib

_REG = {
    "D00": ("discrete", "AgeOnlyHazard"),
    "D01": ("discrete", "Cloglog"),
    "D02": ("discrete", "Logit"),
    "D03": ("discrete", "Probit"),
    "D04": ("discrete", "FlexibleCloglog"),
    "D05": ("boosted", "BoostedHazard"),
    "D06": ("neural", "MLPHazard"),
    "L00": ("survival", "KaplanMeier"),
    "L01": ("survival", "CoxPH"),
    "L02": ("survival", "CoxNet"),
    "L03": ("survival", "WeibullAFT"),
    "L04": ("survival", "LogNormalAFT"),
    "L05": ("survival", "RSF"),
    "L06": ("boosted", "GBCox"),
    "L07": ("neural", "DeepSurv"),
    "L08": ("neural", "CoxTime"),
    "L09": ("neural", "DeepHitSingle"),
    "L10": ("neural", "CBNN"),
}

MODEL_IDS = [k for k in _REG if not k.endswith("00")]
REFERENCE = {"D": "D00", "L": "L00"}


def get_model(mid: str):
    mod, cls = _REG[mid]
    return getattr(importlib.import_module(f"stage2_benchmark.models.{mod}"), cls)()


def task_of(mid: str) -> str:
    return mid[0]
