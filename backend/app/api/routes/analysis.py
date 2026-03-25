import json
import time
import logging
from fastapi import APIRouter, Depends, Form, UploadFile, File, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from app.db.models import StudentProfile, Submission
from app.schemas.profile import (
    ProfileSubmissionRequest,
    AnalysisResponse,
    MatrixBreakdown,
    ShapContribution,
    ActionItem,
)
from app.schemas.user import UserResponse
from app.engine.scorer import MatrixScorer
from app.api.deps import get_db, get_current_user
from typing import Annotated
from ml.extra_scorer import compute_adjustment

router = APIRouter()
logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalize_matrix_breakdown(raw: dict) -> dict:
    """
    Converts MatrixBreakdown.model_dump() into a stable, consistent shape
    that is stored in the DB and reconstructed identically on GET.

    Input keys from MatrixScorer may be:
        academics, internship, projects, coding, hackathons, certifications
    Each value shape: { score: float, maxScore: float }  (MatrixCategoryBreakdown)

    Output: same keys, same { score, maxScore } values — just guaranteed to be
    present and consistently named so the frontend transformer never gets None.
    """
    def _s(d: dict) -> float:
        return float(d.get("score") or d.get("earned") or 0)

    def _m(d: dict) -> float:
        return float(d.get("maxScore") or d.get("max_score") or d.get("max") or 0)

    return {
        "academics":      {"score": _s(raw.get("academics", {})),      "maxScore": _m(raw.get("academics", {}))},
        "coding":         {"score": _s(raw.get("coding", {})),         "maxScore": _m(raw.get("coding", {}))},
        "internship":     {"score": _s(raw.get("internship", {})),     "maxScore": _m(raw.get("internship", {}))},
        "projects":       {"score": _s(raw.get("projects", {})),       "maxScore": _m(raw.get("projects", {}))},
        "certifications": {"score": _s(raw.get("certifications", {})), "maxScore": _m(raw.get("certifications", {}))},
        "hackathons":     {"score": _s(raw.get("hackathons", {})),     "maxScore": _m(raw.get("hackathons", {}))},
    }


# ── POST /analyse ─────────────────────────────────────────────────────────────

@router.post("", response_model=AnalysisResponse)
async def analyse_profile(
    background_tasks: BackgroundTasks,
    profile: Annotated[str, Form(...)],
    resume: UploadFile = File(...),
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Submit a profile + resume for full AI-powered analysis.
    Accepts multipart/form-data: stringified JSON profile + PDF resume.
    """
    start_time = time.time()

    # 1. Parse profile JSON
    try:
        raw_data = json.loads(profile)
        request_data = ProfileSubmissionRequest(**raw_data)
    except Exception as e:
        logger.error(f"Failed to parse profile JSON: {e}")
        raise HTTPException(status_code=422, detail=f"Invalid profile data: {str(e)}")

    # 2. Matrix score
    matrix_score, matrix_breakdown = MatrixScorer.calculate_score(request_data)
    logger.info(f"Matrix score: {matrix_score:.1f}/100")

    # 3. Resume parsing + ATS
    pdf_bytes = await resume.read()
    from app.engine.parser import ResumeParser
    resume_text = ResumeParser.extract_text(pdf_bytes)
    logger.info(f"Extracted {len(resume_text)} chars from resume")

    ats_result = ResumeParser.calculate_ats_score(resume_text)
    if len(ats_result) == 3:
        ats_score, keyword_gaps, resume_skills = ats_result
    else:
        ats_score, keyword_gaps = ats_result
        resume_skills = ResumeParser.extract_skills(resume_text)

    logger.info(f"ATS: {ats_score:.1f}% | {len(resume_skills)} skills | gaps: {keyword_gaps}")

    # 4. ML prediction
    from app.engine.ml import predictor
    result = predictor.predict(
        profile=request_data,
        matrix_score=matrix_score,
        ats_score=ats_score,
        resume_text=resume_text,
        resume_skills=resume_skills,
    )

    if len(result) == 5:
        probability, confidence_band, shap_contributions, actions, platform_summary = result
    else:
        probability, confidence_band, shap_contributions, actions = result
        platform_summary = {}

    logger.info(f"Prediction: {probability}% | band: {confidence_band}")

    # 5. Extra scorer
    exp = request_data.experience
    internship_types = (
        [exp.internshipType] if exp.internshipType != "none" else []
    )
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

    # 6. Persist to DB
    acad = request_data.academic
    code = request_data.coding

    student_profile = StudentProfile(
        user_id=str(current_user.id),
        tenth_pct=acad.tenthPct,
        twelfth_pct=acad.twelfthPct,
        cgpa=acad.cgpa,
        cgpa_scale=acad.cgpaScale,
        branch=acad.branch,
        year=acad.year,
        backlogs=acad.backlogs,
        lc_submissions=code.lcTotalSolved or code.lcSubmissions,
        hr_badges=code.hrBadges,
        hr_med_hard_solved=code.hrMedHardSolved or (code.lcMediumSolved + code.lcHardSolved),
        github_contributions=code.githubYearlyContributions or code.githubContributions,
        github_collaborations=code.githubFollowers or code.githubCollaborations,
        github_monthly_active=code.githubMonthlyActive,
        internship_type=exp.internshipType,
        internship_count=exp.internshipCount,
        internship_stipend_above_10k=exp.internshipStipendAbove10k,
        projects_industry=exp.projectsIndustry,
        projects_domain=exp.projectsDomain,
        certs_global=exp.certsGlobal,
        certs_nptel=exp.certsNptel,
        certs_rbu=exp.certsRbu,
        hackathon_first=exp.hackathonFirst,
        hackathon_second=exp.hackathonSecond,
        hackathon_third=exp.hackathonThird,
        hackathon_participation=exp.hackathonParticipation,
    )
    db.add(student_profile)
    db.flush()

    processing_ms = int((time.time() - start_time) * 1000)

    # Normalize matrix breakdown before storing — consistent shape for GET
    normalized_breakdown = _normalize_matrix_breakdown(matrix_breakdown.model_dump())

    submission = Submission(
        user_id=str(current_user.id),
        profile_id=student_profile.id,
        ats_score=ats_score,
        keyword_gaps=keyword_gaps,
        probability=p_final_pct,
        confidence_lower=confidence_band[0],
        confidence_upper=confidence_band[1],
        matrix_score=matrix_score,
        matrix_breakdown=normalized_breakdown,
        shap_contributions=[s.model_dump() for s in shap_contributions],
        actions=[a.model_dump() for a in actions],
        processing_ms=processing_ms,
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    return AnalysisResponse(
        submissionId=submission.id,
        probability=p_final_pct,
        base_probability=probability,
        adjustment_breakdown=adjustment.breakdown,
        extra_score=adjustment.delta_log_odds,
        confidenceBand=confidence_band,
        matrixScore=matrix_score,
        matrixBreakdown=matrix_breakdown,
        atsScore=ats_score,
        keywordGaps=keyword_gaps,
        resumeSkills=resume_skills,
        shapContributions=shap_contributions,
        actions=actions,
        processingMs=processing_ms,
        platformSummary=platform_summary,
    )


# ── GET /analyse/{submission_id} ──────────────────────────────────────────────

@router.get("/{submission_id}", response_model=AnalysisResponse)
def get_analysis_result(
    submission_id: str,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fetch a previously saved analysis result by submission ID."""
    submission = db.query(Submission).filter(
        Submission.id == submission_id,
        Submission.user_id == str(current_user.id),
    ).first()

    if not submission:
        raise HTTPException(status_code=404, detail="Analysis result not found")

    stored_breakdown = submission.matrix_breakdown or {}

    # Reconstruct MatrixBreakdown from the normalized dict stored in DB.
    # Each value is { score, maxScore } which matches MatrixCategoryBreakdown.
    try:
        matrix_bd = MatrixBreakdown(**{
            k: {"score": v.get("score", 0), "maxScore": v.get("maxScore", 0)}
            for k, v in stored_breakdown.items()
        })
    except Exception as e:
        logger.warning(f"MatrixBreakdown reconstruction failed for {submission_id}: {e}")
        # Provide a safe zero-filled fallback so the response never 500s
        zero = {"score": 0.0, "maxScore": 0.0}
        matrix_bd = MatrixBreakdown(
            academics=zero, coding=zero, internship=zero,
            projects=zero, certifications=zero, hackathons=zero,
        )

    return AnalysisResponse(
        submissionId=submission.id,
        probability=submission.probability,
        confidenceBand=[submission.confidence_lower, submission.confidence_upper],
        matrixScore=submission.matrix_score,
        matrixBreakdown=matrix_bd,
        atsScore=submission.ats_score or 0.0,
        keywordGaps=submission.keyword_gaps or [],
        resumeSkills=[],
        shapContributions=[
            ShapContribution(**s) for s in (submission.shap_contributions or [])
        ],
        actions=[ActionItem(**a) for a in (submission.actions or [])],
        processingMs=submission.processing_ms or 0,
        platformSummary={},
    )
