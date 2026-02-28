import json
import time
import logging
from fastapi import APIRouter, Depends, Form, UploadFile, File, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from app.db.models import StudentProfile, Submission
from app.schemas.profile import ProfileSubmissionRequest, AnalysisResponse
from app.schemas.user import UserResponse
from app.engine.scorer import MatrixScorer
from app.api.deps import get_db, get_current_user
from typing import Annotated

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/", response_model=AnalysisResponse)
async def analyse_profile(
    background_tasks: BackgroundTasks,
    profile: Annotated[str, Form(...)],
    resume: UploadFile = File(...),
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submits a profile + resume for full AI-powered analysis.
    Accepts Multipart form data (stringified JSON + PDF).
    """
    start_time = time.time()

    # 1. Parse incoming stringified JSON into Pydantic model
    try:
        raw_data = json.loads(profile)
        request_data = ProfileSubmissionRequest(**raw_data)
    except Exception as e:
        logger.error(f"Failed to parse profile JSON: {e}")
        raise HTTPException(status_code=422, detail=f"Invalid profile data: {str(e)}")

    # 2. Extract deterministic Matrix Score & Breakdown
    matrix_score, matrix_breakdown = MatrixScorer.calculate_score(request_data)
    logger.info(f"Matrix score: {matrix_score:.1f}/100")

    # 3. Resume Extraction via pdfplumber/PyPDF2
    pdf_bytes = await resume.read()
    from app.engine.parser import ResumeParser
    resume_text = ResumeParser.extract_text(pdf_bytes)
    logger.info(f"Extracted {len(resume_text)} characters from resume")

    # Run full ATS analysis with skill extraction (returns score, gaps, skills list)
    ats_result = ResumeParser.calculate_ats_score(resume_text)
    if len(ats_result) == 3:
        ats_score, keyword_gaps, resume_skills = ats_result
    else:
        # Backward compat if only 2 values returned
        ats_score, keyword_gaps = ats_result
        resume_skills = ResumeParser.extract_skills(resume_text)

    logger.info(f"ATS score: {ats_score:.1f}% | {len(resume_skills)} skills found | gaps: {keyword_gaps}")

    # 4. AI / ML Prediction via Gemini (or smart heuristic fallback)
    from app.engine.ml import predictor
    result = predictor.predict(
        profile=request_data,
        matrix_score=matrix_score,
        ats_score=ats_score,
        resume_text=resume_text,
        resume_skills=resume_skills,
    )

    # Handle both old 4-tuple return and new 5-tuple return
    if len(result) == 5:
        probability, confidence_band, shap_contributions, actions, platform_summary = result
    else:
        probability, confidence_band, shap_contributions, actions = result
        platform_summary = {}

    logger.info(f"Prediction: {probability}% | confidence: {confidence_band}")

    # 5. Persist to DB
    acad = request_data.academic
    code = request_data.coding
    exp = request_data.experience

    student_profile = StudentProfile(
        user_id=str(current_user.id),
        tenth_pct=acad.tenthPct,
        twelfth_pct=acad.twelfthPct,
        cgpa=acad.cgpa,
        cgpa_scale=acad.cgpaScale,
        branch=acad.branch,
        year=acad.year,
        backlogs=acad.backlogs,
        # Use the new fields if available, fall back to legacy
        lc_submissions=code.lcTotalSolved or code.lcSubmissions,
        hr_badges=code.hrBadges,
        hr_med_hard_solved=code.hrMedHardSolved or (code.lcMediumSolved + code.lcHardSolved),
        github_contributions=code.githubRepos * 10 if code.githubRepos else code.githubContributions,
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

    submission = Submission(
        user_id=str(current_user.id),
        profile_id=student_profile.id,
        ats_score=ats_score,
        keyword_gaps=keyword_gaps,
        probability=probability,
        confidence_lower=confidence_band[0],
        confidence_upper=confidence_band[1],
        matrix_score=matrix_score,
        matrix_breakdown=matrix_breakdown.model_dump(),
        shap_contributions=[s.model_dump() for s in shap_contributions],
        actions=[a.model_dump() for a in actions],
        processing_ms=processing_ms
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    return AnalysisResponse(
        submissionId=submission.id,
        probability=probability,
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


@router.get("/{submission_id}", response_model=AnalysisResponse)
def get_analysis_result(
    submission_id: str,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Fetch a previously saved analysis result by submission ID."""
    submission = db.query(Submission).filter(
        Submission.id == submission_id,
        Submission.user_id == str(current_user.id)
    ).first()

    if not submission:
        raise HTTPException(status_code=404, detail="Analysis result not found")

    from app.schemas.profile import MatrixBreakdown, ShapContribution, ActionItem

    return AnalysisResponse(
        submissionId=submission.id,
        probability=submission.probability,
        confidenceBand=[submission.confidence_lower, submission.confidence_upper],
        matrixScore=submission.matrix_score,
        matrixBreakdown=MatrixBreakdown(**submission.matrix_breakdown),
        atsScore=submission.ats_score or 0.0,
        keywordGaps=submission.keyword_gaps or [],
        resumeSkills=[],
        shapContributions=[ShapContribution(**s) for s in (submission.shap_contributions or [])],
        actions=[ActionItem(**a) for a in (submission.actions or [])],
        processingMs=submission.processing_ms or 0,
        platformSummary={},
    )
