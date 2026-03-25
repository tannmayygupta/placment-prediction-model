# app/api/routes/whatif.py
#
# POST /analyse/whatif
#
# Stateless what-if simulation.
# Runs the full Matrix + ML + extra_scorer pipeline — identical to /analyse —
# but accepts a lightweight JSON payload instead of multipart + PDF,
# and writes NOTHING to the database.

import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from app.schemas.profile import (
    ProfileSubmissionRequest,
    AnalysisResponse,
    AcademicDetails,    # correct name from profile.py
    CodingDetails,      # correct name from profile.py
    ExperienceDetails,  # correct name from profile.py
)
from app.schemas.user import UserResponse
from app.engine.scorer import MatrixScorer
from app.api.deps import get_current_user
from ml.extra_scorer import compute_adjustment

router = APIRouter()
logger = logging.getLogger(__name__)


# ── Request schema ────────────────────────────────────────────────────────────

class WhatIfRequest(BaseModel):
    """
    profile      — coding overrides in snake_case (new absolute values)
    experience   — experience overrides in snake_case (new absolute values)
    ats_score    — pass-through from the original submission
    base_profile — original profile dict (camelCase) to fill un-overridden fields
    """
    profile:      dict           = Field(default_factory=dict)
    experience:   dict           = Field(default_factory=dict)
    ats_score:    float          = Field(0.0, ge=0, le=100)
    base_profile: Optional[dict] = Field(None)


# ── Profile builder ───────────────────────────────────────────────────────────

# snake_case keys from WhatIfRequest.profile → camelCase fields of CodingDetails
_CODING_MAP = {
    "lc_submissions":         "lcSubmissions",
    "lc_total_solved":        "lcTotalSolved",
    "lc_easy_solved":         "lcEasySolved",
    "lc_medium_solved":       "lcMediumSolved",
    "lc_hard_solved":         "lcHardSolved",
    "lc_active_days":         "lcActiveDays",
    "lc_ranking":             "lcRanking",
    "github_contributions":   "githubYearlyContributions",  # maps to new field
    "github_repos":           "githubRepos",
    "github_followers":       "githubFollowers",
    "github_collaborations":  "githubCollaborations",
    "github_monthly_active":  "githubMonthlyActive",
    "cf_rating":              "cfRating",
    "cf_max_rating":          "cfMaxRating",
    "cf_rank":                "cfRank",
    "cf_solved":              "cfSolved",
    "cc_rating":              "ccRating",
    "cc_stars":               "ccStars",
    "cc_solved":              "ccSolved",
    "cc_global_rank":         "ccGlobalRank",
    "hr_badges":              "hrBadges",
    "hr_med_hard_solved":     "hrMedHardSolved",
}

_EXPERIENCE_MAP = {
    "internship_type":               "internshipType",
    "internship_count":              "internshipCount",
    "internship_stipend_above_10k":  "internshipStipendAbove10k",
    "projects_industry":             "projectsIndustry",
    "projects_domain":               "projectsDomain",
    "certs_global":                  "certsGlobal",
    "certs_nptel":                   "certsNptel",
    "certs_rbu":                     "certsRbu",
    "hackathon_first":               "hackathonFirst",
    "hackathon_second":              "hackathonSecond",
    "hackathon_third":               "hackathonThird",
    "hackathon_participation":       "hackathonParticipation",
}


def _build_profile(req: WhatIfRequest) -> ProfileSubmissionRequest:
    """
    Merge what-if overrides onto the base profile, apply safe defaults,
    then construct a ProfileSubmissionRequest — same as analysis.py does.
    """
    base = req.base_profile or {}
    acad = dict(base.get("academic",   {}))
    code = dict(base.get("coding",     {}))
    exp  = dict(base.get("experience", {}))

    # Apply coding overrides (snake → camel)
    for snake, camel in _CODING_MAP.items():
        val = req.profile.get(snake)
        if val is not None:
            code[camel] = val

    # Apply experience overrides (snake → camel)
    for snake, camel in _EXPERIENCE_MAP.items():
        val = req.experience.get(snake)
        if val is not None:
            exp[camel] = val

    # Safe defaults — AcademicDetails has no field defaults so all are required
    acad.setdefault("cgpa",       0.0)
    acad.setdefault("cgpaScale",  10)
    acad.setdefault("tenthPct",   0.0)
    acad.setdefault("twelfthPct", 0.0)
    acad.setdefault("branch",     "CSE")
    acad.setdefault("year",       3)
    acad.setdefault("backlogs",   0)

    # ExperienceDetails has defaults but set them anyway for safety
    exp.setdefault("internshipType",            "none")
    exp.setdefault("internshipCount",           0)
    exp.setdefault("internshipStipendAbove10k", False)
    exp.setdefault("projectsIndustry",          0)
    exp.setdefault("projectsDomain",            0)
    exp.setdefault("certsGlobal",               0)
    exp.setdefault("certsNptel",                0)
    exp.setdefault("certsRbu",                  0)
    exp.setdefault("hackathonFirst",            0)
    exp.setdefault("hackathonSecond",           0)
    exp.setdefault("hackathonThird",            0)
    exp.setdefault("hackathonParticipation",    0)

    # CodingDetails has all-zero defaults — no setdefault needed

    return ProfileSubmissionRequest(
        academic=AcademicDetails(**acad),
        coding=CodingDetails(**code),
        experience=ExperienceDetails(**exp),
    )


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/whatif", response_model=AnalysisResponse)
async def what_if_analysis(
    req: WhatIfRequest,
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Stateless what-if simulation.
    Runs full scoring pipeline, returns AnalysisResponse.
    Nothing is written to the database.
    """
    logger.info(f"What-if request from user {current_user.id}")

    # 1. Build profile
    try:
        profile = _build_profile(req)
    except Exception as ex:
        logger.error(f"What-if profile build failed: {ex}")
        raise HTTPException(status_code=422, detail=f"Invalid what-if payload: {ex}")

    # 2. Matrix score
    matrix_score, matrix_breakdown = MatrixScorer.calculate_score(profile)
    logger.info(f"What-if matrix: {matrix_score:.1f}/100")

    # 3. ML prediction (no resume in what-if)
    from app.engine.ml import predictor
    result = predictor.predict(
        profile=profile,
        matrix_score=matrix_score,
        ats_score=req.ats_score,
        resume_text="",
        resume_skills=[],
    )

    if len(result) == 5:
        probability, confidence_band, shap_contributions, actions, platform_summary = result
    else:
        probability, confidence_band, shap_contributions, actions = result
        platform_summary = {}

    logger.info(f"What-if prediction: {probability}% | band: {confidence_band}")

    # 4. Extra scorer
    exp = profile.experience
    internship_types = [exp.internshipType] if exp.internshipType != "none" else []
    certs = []
    certs += [{"prize_level": "first"}]         * (exp.hackathonFirst         or 0)
    certs += [{"prize_level": "second"}]        * (exp.hackathonSecond        or 0)
    certs += [{"prize_level": "third"}]         * (exp.hackathonThird         or 0)
    certs += [{"prize_level": "participation"}] * (exp.hackathonParticipation or 0)

    adjustment = compute_adjustment(
        p_base=probability / 100.0,
        internship_types=internship_types,
        internship_stipend_above_10k=exp.internshipStipendAbove10k or False,
        lors=[],
        hackathon_certs=certs,
    )
    p_final_pct = round(adjustment.p_final * 100, 1)

    # 5. Return — no DB write
    return AnalysisResponse(
        submissionId="whatif",
        probability=p_final_pct,
        base_probability=probability,
        adjustment_breakdown=adjustment.breakdown,
        extra_score=adjustment.delta_log_odds,
        confidenceBand=confidence_band,
        matrixScore=matrix_score,
        matrixBreakdown=matrix_breakdown,
        atsScore=req.ats_score,
        keywordGaps=[],
        resumeSkills=[],
        shapContributions=shap_contributions,
        actions=actions,
        processingMs=0,
        platformSummary=platform_summary,
    )
