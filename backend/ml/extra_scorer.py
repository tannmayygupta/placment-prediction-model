# backend/ml/extra_scorer.py

import math
from dataclasses import dataclass, field
from typing import List, Dict


# ── Result Structure ──────────────────────────────────────────────────────────
@dataclass
class AdjustmentResult:
    delta_log_odds: float
    p_base: float
    p_final: float
    breakdown: Dict = field(default_factory=dict)


# ── Calibrated Delta Values ───────────────────────────────────────────────────
_DELTAS = {
    "internship_international": 0.50,
    "internship_it_company": 0.25,     # capped at 2
    "internship_eduskills": 0.15,      # capped at 1
    "internship_stipend_10k": 0.20,

    "lor_industry": 0.30,              # capped at 2
    "lor_academic_strong": 0.15,       # capped at 2
    "lor_academic_standard": 0.05,     # capped at 2

    "hackathon_first": 0.35,
    "hackathon_second": 0.20,
    "hackathon_third": 0.10,
    "hackathon_participation": 0.05,   # capped at 3
}

MAX_DELTA = 0.80
MIN_DELTA = -0.30


# ── Helper Functions ──────────────────────────────────────────────────────────
def _sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def _log_odds(p: float) -> float:
    p = max(0.001, min(0.999, p))  # avoid log(0)
    return math.log(p / (1 - p))


# ── Core Function (PURE LOGIC) ────────────────────────────────────────────────
def compute_adjustment(
    p_base: float,
    internship_types: List[str],
    internship_stipend_above_10k: bool,
    lors: List[Dict],
    hackathon_certs: List[Dict],
) -> AdjustmentResult:

    delta = 0.0
    breakdown = {}

    # ── Internship ───────────────────────────────────────────────────────────
    intern_delta = 0.0

    if "international" in internship_types:
        intern_delta += _DELTAS["internship_international"]

    it_count = min(internship_types.count("it_company"), 2)
    intern_delta += it_count * _DELTAS["internship_it_company"]

    edu_count = min(internship_types.count("eduskills"), 1)
    intern_delta += edu_count * _DELTAS["internship_eduskills"]

    if internship_stipend_above_10k:
        intern_delta += _DELTAS["internship_stipend_10k"]

    if intern_delta > 0:
        breakdown["internship"] = round(intern_delta, 3)

    delta += intern_delta

    # ── LOR (FIXED LOGIC) ────────────────────────────────────────────────────
    industry = sum(1 for l in lors if l.get("source_type") == "industry")
    academic_strong = sum(1 for l in lors if l.get("source_type") == "academic_strong")
    academic_standard = sum(1 for l in lors if l.get("source_type") == "academic_standard")

    lor_delta = (
        min(industry, 2) * _DELTAS["lor_industry"] +
        min(academic_strong, 2) * _DELTAS["lor_academic_strong"] +
        min(academic_standard, 2) * _DELTAS["lor_academic_standard"]
    )

    if lor_delta > 0:
        breakdown["lor"] = round(lor_delta, 3)

    delta += lor_delta

    # ── Hackathons ───────────────────────────────────────────────────────────
    hack_delta = 0.0
    participation_count = 0

    for cert in hackathon_certs:
        level = cert.get("prize_level")

        if level == "first":
            hack_delta += _DELTAS["hackathon_first"]
        elif level == "second":
            hack_delta += _DELTAS["hackathon_second"]
        elif level == "third":
            hack_delta += _DELTAS["hackathon_third"]
        elif level == "participation" and participation_count < 3:
            hack_delta += _DELTAS["hackathon_participation"]
            participation_count += 1

    if hack_delta > 0:
        breakdown["hackathon"] = round(hack_delta, 3)

    delta += hack_delta

    # ── Synergy Bonus (ADVANCED FEATURE) ──────────────────────────────────────
    synergy_delta = 0.0

    if intern_delta > 0 and hack_delta > 0:
        synergy_delta += 0.05

    if intern_delta > 0 and lor_delta > 0:
        synergy_delta += 0.04

    if synergy_delta > 0:
        breakdown["synergy"] = round(synergy_delta, 3)

    delta += synergy_delta

    # ── Clamp Final Delta ─────────────────────────────────────────────────────
    delta = max(MIN_DELTA, min(MAX_DELTA, delta))

    # ── Final Probability ─────────────────────────────────────────────────────
    p_final = _sigmoid(_log_odds(p_base) + delta)

    return AdjustmentResult(
        delta_log_odds=round(delta, 3),
        p_base=round(p_base, 4),
        p_final=round(p_final, 4),
        breakdown=breakdown
    )