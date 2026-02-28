"""
ml.py — AI-Powered Placement Predictor

Uses Google Gemini (gemini-1.5-flash) to intelligently analyse a student's
complete profile (academics, real coding platform stats, resume text) and
generate:
  - A calibrated placement probability (%)
  - Feature-level contributions (SHAP-like)
  - Personalised, specific action items

Falls back to a smart heuristic model only if Gemini is unavailable.
"""

import os
import json
import re
import logging
from typing import Optional

from app.schemas.profile import (
    ProfileSubmissionRequest,
    ShapContribution,
    ActionItem,
)
from app.core.config import settings

logger = logging.getLogger(__name__)


# ─── Gemini Client (lazy-loaded, uses new google-genai SDK) ──────────────────

_gemini_client = None

def _get_gemini_model():
    """Returns a google-genai client if GEMINI_API_KEY is set, else None."""
    global _gemini_client
    if _gemini_client is not None:
        return _gemini_client

    api_key = getattr(settings, 'GEMINI_API_KEY', None) or os.environ.get('GEMINI_API_KEY', '')
    if not api_key or api_key.strip() == '':
        logger.warning("GEMINI_API_KEY not set — falling back to heuristic mode")
        return None

    try:
        from google import genai as google_genai
        _gemini_client = google_genai.Client(api_key=api_key)
        logger.info("Gemini client (google-genai SDK) initialized successfully")
        return _gemini_client
    except Exception as e:
        logger.error(f"Failed to initialize Gemini client: {e}")
        return None


def _build_profile_context(
    profile: ProfileSubmissionRequest,
    matrix_score: float,
    ats_score: float,
    resume_text: str,
    resume_skills: list[str],
) -> str:
    """Builds a rich, structured context string for Gemini."""
    acad = profile.academic
    code = profile.coding
    exp = profile.experience

    cgpa_norm = acad.cgpa * (10.0 / acad.cgpaScale)

    # Determine Codeforces tier label
    cf_tier = "unrated"
    if code.cfRating >= 2400:
        cf_tier = "Grandmaster"
    elif code.cfRating >= 1900:
        cf_tier = "Candidate Master"
    elif code.cfRating >= 1600:
        cf_tier = "Expert"
    elif code.cfRating >= 1400:
        cf_tier = "Specialist"
    elif code.cfRating >= 1200:
        cf_tier = "Pupil"
    elif code.cfRating > 0:
        cf_tier = "Newbie"

    # Determine LeetCode tier
    lc_tier = "Beginner"
    if code.lcTotalSolved >= 500:
        lc_tier = "Expert"
    elif code.lcTotalSolved >= 300:
        lc_tier = "Advanced"
    elif code.lcTotalSolved >= 150:
        lc_tier = "Intermediate"
    elif code.lcTotalSolved >= 50:
        lc_tier = "Beginner-Intermediate"

    context = f"""
STUDENT PROFILE FOR PLACEMENT ANALYSIS:

=== ACADEMICS ===
Branch: {acad.branch} | Year: {acad.year}
CGPA: {cgpa_norm:.2f}/10 (original: {acad.cgpa}/{acad.cgpaScale})
10th Board: {acad.tenthPct}% | 12th Board: {acad.twelfthPct}%
Active Backlogs: {acad.backlogs}

=== CODING PLATFORMS ===
LeetCode:
  - Total Solved: {code.lcTotalSolved} [{lc_tier}]
  - Easy: {code.lcEasySolved} | Medium: {code.lcMediumSolved} | Hard: {code.lcHardSolved}
  - Active Days (past year): {code.lcActiveDays}
  - Global Ranking: {f'#{code.lcRanking:,}' if code.lcRanking > 0 else 'N/A'}

GitHub:
  - Public Repos: {code.githubRepos}
  - Followers: {code.githubFollowers}
  - Total Stars: {code.githubStars}

Codeforces:
  - Rating: {code.cfRating} | Max: {code.cfMaxRating} | Rank: {code.cfRank} [{cf_tier}]
  - Problems Solved: {code.cfSolved}

CodeChef:
  - Rating: {code.ccRating} | Stars: {code.ccStars}
  - Problems Solved: {code.ccSolved}
  - Global Rank: {f'#{code.ccGlobalRank:,}' if code.ccGlobalRank > 0 else 'N/A'}

=== EXPERIENCE & ACHIEVEMENTS ===
Internships: {exp.internshipCount} ({exp.internshipType})
Stipend >10k: {'Yes' if exp.internshipStipendAbove10k else 'No'}
Industry Projects: {exp.projectsIndustry} | Domain Projects: {exp.projectsDomain}
Certifications: Global={exp.certsGlobal}, NPTEL={exp.certsNptel}, RBU={exp.certsRbu}
Hackathons: 1st={exp.hackathonFirst}, 2nd={exp.hackathonSecond}, 3rd={exp.hackathonThird}, Participated={exp.hackathonParticipation}

=== SCORES (pre-computed) ===
Matrix Score (RBU CDPC): {matrix_score:.1f}/100
ATS Resume Score: {ats_score:.1f}/100

=== RESUME SKILLS DETECTED ===
{', '.join(resume_skills) if resume_skills else 'No skills detected (resume may be image-based)'}

=== RESUME TEXT (extracted, first 2000 chars) ===
{resume_text[:2000] if resume_text else 'Resume text unavailable'}
"""
    return context.strip()


def _call_gemini(
    profile: ProfileSubmissionRequest,
    matrix_score: float,
    ats_score: float,
    resume_text: str,
    resume_skills: list[str],
) -> Optional[dict]:
    """
    Calls Gemini 1.5 Flash to generate a structured placement analysis.
    Returns a parsed dict or None if Gemini is unavailable/errors.
    """
    model = _get_gemini_model()
    if model is None:
        return None

    profile_context = _build_profile_context(
        profile, matrix_score, ats_score, resume_text, resume_skills
    )

    prompt = f"""You are an expert placement analyst for engineering students in India.
Analyse this student's profile and generate a realistic, data-driven placement prediction.

{profile_context}

IMPORTANT INSTRUCTIONS:
1. The placement probability should reflect REAL industry standards for Indian campus placements.
2. Base your analysis on the ACTUAL numbers provided — do NOT use placeholders or generic advice.
3. If LeetCode problems solved is 320, acknowledge 320 — don't say "solve 100 more".
4. Each recommendation must be SPECIFIC to this student's data.
5. The probability should be calibrated: 70-85% for strong profiles, 40-65% for average, <40% for weak.

Respond with ONLY valid JSON (no markdown, no code blocks) in exactly this format:
{{
  "probability": <float 0-100>,
  "confidence_lower": <float>,
  "confidence_upper": <float>,
  "reasoning": "<2-3 sentence summary of why this probability>",
  "platform_summary": {{
    "leetcode": "<specific assessment based on actual numbers>",
    "github": "<specific assessment>",
    "codeforces": "<specific assessment>",
    "codechef": "<specific assessment>"
  }},
  "feature_contributions": [
    {{"feature": "CGPA ({profile.academic.cgpa}/{profile.academic.cgpaScale})", "value": <cgpa_normalized>, "contribution": <-0.2 to 0.2>, "impact": "positive|negative|neutral"}},
    {{"feature": "LeetCode ({profile.coding.lcTotalSolved} solved, {profile.coding.lcActiveDays} active days)", "value": {profile.coding.lcTotalSolved}, "contribution": <float>, "impact": "positive|negative|neutral"}},
    {{"feature": "LeetCode Hard Problems ({profile.coding.lcHardSolved})", "value": {profile.coding.lcHardSolved}, "contribution": <float>, "impact": "positive|negative|neutral"}},
    {{"feature": "GitHub ({profile.coding.githubRepos} repos, {profile.coding.githubStars} stars)", "value": {profile.coding.githubRepos}, "contribution": <float>, "impact": "positive|negative|neutral"}},
    {{"feature": "Codeforces Rating ({profile.coding.cfRating})", "value": {profile.coding.cfRating}, "contribution": <float>, "impact": "positive|negative|neutral"}},
    {{"feature": "ATS Resume Score", "value": {ats_score}, "contribution": <float>, "impact": "positive|negative|neutral"}},
    {{"feature": "Backlogs ({profile.academic.backlogs})", "value": {profile.academic.backlogs}, "contribution": <float>, "impact": "positive|negative|neutral"}},
    {{"feature": "Internship", "value": {profile.experience.internshipCount}, "contribution": <float>, "impact": "positive|negative|neutral"}}
  ],
  "action_items": [
    {{
      "priority": 1,
      "action": "<specific, actionable improvement>",
      "rationale": "<WHY this helps, with specific numbers from their profile>",
      "category": "<Academic|Coding|Resume|Experience|Certifications|Hackathons>"
    }}
  ]
}}

Generate 4-6 action_items. They MUST be personalized — reference actual numbers from the profile. 
DO NOT give generic advice like "solve more problems" if they already have 300+ solved.
DO NOT recommend things they've already clearly done well."""

    try:
        from google import genai as google_genai
        response = model.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt,
            config=google_genai.types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=2048,
            ),
        )
        raw = response.text.strip()

        # Strip markdown code fences if present
        raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.MULTILINE)
        raw = re.sub(r'\s*```$', '', raw, flags=re.MULTILINE)
        raw = raw.strip()

        result = json.loads(raw)
        logger.info(f"Gemini returned probability: {result.get('probability')}")
        return result

    except json.JSONDecodeError as e:
        logger.error(f"Gemini returned invalid JSON: {e}\nRaw: {raw[:500]}")
        return None
    except Exception as e:
        logger.error(f"Gemini API call failed: {e}")
        return None


# ─── Smart Heuristic Fallback ─────────────────────────────────────────────────

def _heuristic_predict(
    profile: ProfileSubmissionRequest,
    matrix_score: float,
    ats_score: float,
) -> dict:
    """
    Calibrated, data-driven heuristic when Gemini is unavailable.
    Uses actual platform numbers — NOT hardcoded thresholds.
    """
    code = profile.coding
    acad = profile.academic
    exp = profile.experience

    cgpa_norm = acad.cgpa * (10.0 / acad.cgpaScale)

    # ── Component scores (0–1 scale each) ─────────────────────────────────────
    # LeetCode: realistic scoring — 0 to 1 based on total solved (500+ = max)
    lc_score = min(1.0, code.lcTotalSolved / 500.0)
    # Bonus for hard problems (strong differentiator)
    lc_hard_bonus = min(0.15, code.lcHardSolved / 100.0)
    # Bonus for active days (consistency)
    lc_active_bonus = min(0.1, code.lcActiveDays / 200.0)

    # CGPA: 9+ = max, 6.0 = min
    cgpa_score = max(0.0, min(1.0, (cgpa_norm - 6.0) / 3.5))

    # GitHub: repos + stars
    gh_score = min(1.0, (code.githubRepos / 30.0) + (code.githubStars / 100.0))

    # Codeforces: 0 = unrated, 2400+ = grandmaster (max)
    cf_score = min(1.0, code.cfRating / 2400.0) if code.cfRating > 0 else 0.0

    # CodeChef rating
    cc_score = min(1.0, code.ccRating / 2500.0) if code.ccRating > 0 else 0.0

    # ATS + matrix
    ats_norm = ats_score / 100.0
    matrix_norm = matrix_score / 100.0

    # Internship is a strong signal
    intern_score = min(1.0, exp.internshipCount * 0.3 +
                       (0.15 if exp.internshipType == 'international' else
                        0.1 if exp.internshipType == 'it_company' else 0.0))

    # Backlog penalty
    backlog_penalty = min(0.3, acad.backlogs * 0.1)

    # ── Weighted composite score ───────────────────────────────────────────────
    composite = (
        0.15 * cgpa_score +
        0.20 * (lc_score + lc_hard_bonus + lc_active_bonus) +
        0.10 * gh_score +
        0.08 * cf_score +
        0.04 * cc_score +
        0.15 * matrix_norm +
        0.12 * ats_norm +
        0.10 * intern_score
    ) - backlog_penalty

    prob = max(10.0, min(95.0, composite * 100.0))
    c_low = max(5.0, prob - 10.0)
    c_high = min(98.0, prob + 8.0)

    # ── Feature contributions ──────────────────────────────────────────────────
    features = [
        ShapContribution(
            feature=f"CGPA ({cgpa_norm:.1f}/10)",
            value=round(cgpa_norm, 2),
            contribution=round(0.15 * cgpa_score - 0.075, 3)
        ),
        ShapContribution(
            feature=f"LeetCode ({code.lcTotalSolved} solved, {code.lcActiveDays} active days)",
            value=float(code.lcTotalSolved),
            contribution=round(0.20 * lc_score - 0.10, 3)
        ),
        ShapContribution(
            feature=f"LeetCode Hard ({code.lcHardSolved} hard problems)",
            value=float(code.lcHardSolved),
            contribution=round(lc_hard_bonus - 0.075, 3)
        ),
        ShapContribution(
            feature=f"GitHub ({code.githubRepos} repos, {code.githubStars} stars)",
            value=float(code.githubRepos),
            contribution=round(0.10 * gh_score - 0.05, 3)
        ),
        ShapContribution(
            feature=f"Codeforces Rating ({code.cfRating})",
            value=float(code.cfRating),
            contribution=round(0.08 * cf_score - 0.04, 3)
        ),
        ShapContribution(
            feature=f"ATS Resume Score ({ats_score:.0f}%)",
            value=round(ats_score, 1),
            contribution=round(0.12 * ats_norm - 0.06, 3)
        ),
        ShapContribution(
            feature=f"Matrix Score ({matrix_score:.0f}/100)",
            value=round(matrix_score, 1),
            contribution=round(0.15 * matrix_norm - 0.075, 3)
        ),
        ShapContribution(
            feature=f"Backlogs ({acad.backlogs})",
            value=float(acad.backlogs),
            contribution=round(-backlog_penalty, 3)
        ),
    ]

    # ── Personalised actions ───────────────────────────────────────────────────
    actions = []
    priority = 1

    # Only flag LeetCode if ACTUALLY below threshold
    if code.lcTotalSolved < 100:
        needed = 100 - code.lcTotalSolved
        actions.append(ActionItem(
            priority=priority,
            action=f"Solve {needed} more LeetCode problems (target: 100+ total)",
            rationale=f"You have {code.lcTotalSolved} solved. Most companies filter at 100+ solved. Focus on Easy and Medium problems first.",
            category="Coding"
        ))
        priority += 1
    elif code.lcTotalSolved < 200 and code.lcHardSolved < 10:
        actions.append(ActionItem(
            priority=priority,
            action=f"Increase Hard problem count (currently {code.lcHardSolved}, target 20+)",
            rationale=f"You have {code.lcTotalSolved} solved — good foundation! Solving 20+ Hard problems differentiates you in FAANG/product company rounds.",
            category="Coding"
        ))
        priority += 1
    elif code.lcTotalSolved >= 200 and code.lcActiveDays < 50:
        actions.append(ActionItem(
            priority=priority,
            action=f"Improve consistency: aim for 100+ active LeetCode days (currently {code.lcActiveDays})",
            rationale=f"Strong problem count ({code.lcTotalSolved}) but only {code.lcActiveDays} active days. Consistent daily practice is noticed by interviewers.",
            category="Coding"
        ))
        priority += 1

    # Backlogs
    if acad.backlogs > 0:
        actions.append(ActionItem(
            priority=priority,
            action=f"Clear all {acad.backlogs} active backlog(s) this semester",
            rationale=f"Each backlog deducts 5 pts from your Matrix Score and many companies have a zero-backlog filter. This is your #1 red flag.",
            category="Academic"
        ))
        priority += 1

    # Codeforces
    if code.cfRating == 0:
        actions.append(ActionItem(
            priority=priority,
            action="Create a Codeforces account and participate in Div. 3/4 rounds",
            rationale="Competitive programming on Codeforces is valued by top product companies (Google, Atlassian). Even Pupil-level (1200+ rating) adds significant credibility.",
            category="Coding"
        ))
        priority += 1
    elif code.cfRating < 1400:
        actions.append(ActionItem(
            priority=priority,
            action=f"Improve Codeforces rating from {code.cfRating} to 1400+ (Specialist)",
            rationale="Specialist rank (1400+) on Codeforces is a strong differentiator. Focus on Div. 3 and Div. 4 rounds, practice greedy and implementation problems.",
            category="Coding"
        ))
        priority += 1

    # ATS
    if ats_score < 50:
        actions.append(ActionItem(
            priority=priority,
            action="Rewrite resume with ATS-optimized formatting and technical keywords",
            rationale=f"ATS score {ats_score:.0f}% is below the 50% threshold. Add specific technologies from your projects (e.g., frameworks, cloud platforms, databases used).",
            category="Resume"
        ))
        priority += 1
    elif ats_score < 70:
        actions.append(ActionItem(
            priority=priority,
            action=f"Enhance resume with more project-specific keywords (ATS: {ats_score:.0f}% → 70%+)",
            rationale="Your resume passes basic ATS filters but could be stronger. Add quantified achievements (e.g., 'Reduced API latency by 40%') and specific tech stack versions.",
            category="Resume"
        ))
        priority += 1

    # Internship
    if exp.internshipCount == 0:
        actions.append(ActionItem(
            priority=priority,
            action="Secure at least one industry internship before placement season",
            rationale="Internships contribute up to 20 pts in the Matrix Score and are often a non-negotiable filter at product companies. Apply to Internshala, LinkedIn, and company portals now.",
            category="Experience"
        ))
        priority += 1

    # GitHub
    if code.githubRepos < 5:
        actions.append(ActionItem(
            priority=priority,
            action=f"Build and publish 3-5 project repositories on GitHub (currently {code.githubRepos})",
            rationale="GitHub portfolio is increasingly reviewed by recruiters. Public projects with READMEs and live demos are strong differentiators.",
            category="Experience"
        ))
        priority += 1

    # Hackathons
    if exp.hackathonParticipation == 0 and exp.hackathonFirst == 0:
        actions.append(ActionItem(
            priority=priority,
            action="Participate in 2-3 hackathons (Devfolio, MLH, Smart India Hackathon)",
            rationale="Hackathon experience signals initiative and real-world problem-solving. Even participation adds 2 pts; winning adds up to 15 pts to matrix score.",
            category="Hackathons"
        ))
        priority += 1

    # Congrats if everything looks fine
    if not actions:
        actions.append(ActionItem(
            priority=1,
            action="Focus on interview preparation and mock interviews",
            rationale=f"Strong profile across all dimensions! Probability: {prob:.0f}%. Practice system design for senior roles and mock interviews at interviewing.io or Pramp.",
            category="General"
        ))

    return {
        "probability": round(prob, 1),
        "confidence_lower": round(c_low, 1),
        "confidence_upper": round(c_high, 1),
        "feature_contributions": [f.model_dump() for f in features],
        "action_items": [a.model_dump() for a in actions],
        "platform_summary": {
            "leetcode": f"{code.lcTotalSolved} solved ({code.lcEasySolved}E/{code.lcMediumSolved}M/{code.lcHardSolved}H), {code.lcActiveDays} active days",
            "github": f"{code.githubRepos} repos, {code.githubStars} stars, {code.githubFollowers} followers",
            "codeforces": f"Rating {code.cfRating} ({code.cfRank}), {code.cfSolved} solved" if code.cfRating > 0 else "Not registered",
            "codechef": f"Rating {code.ccRating} {code.ccStars}, {code.ccSolved} solved" if code.ccRating > 0 else "Not provided",
        }
    }


# ─── Main Predictor Class ─────────────────────────────────────────────────────

class MLPredictor:
    """
    AI-powered placement predictor using Google Gemini.
    Falls back to calibrated heuristics if Gemini is unavailable.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MLPredictor, cls).__new__(cls)
        return cls._instance

    def initialize(self, models_dir: str = "models"):
        """Initialize Gemini client. Called on FastAPI boot."""
        model = _get_gemini_model()
        if model:
            logger.info("MLPredictor initialized with Gemini AI backend")
        else:
            logger.info("MLPredictor initialized with heuristic fallback backend")

    def predict(
        self,
        profile: ProfileSubmissionRequest,
        matrix_score: float,
        ats_score: float,
        resume_text: str = "",
        resume_skills: list[str] = None,
    ) -> tuple[float, list[float], list[ShapContribution], list[ActionItem], dict]:
        """
        Runs AI inference via Gemini, falls back to smart heuristic.
        Returns: (probability%, confidenceBand, shap_contributions, actions, platform_summary)
        """
        if resume_skills is None:
            resume_skills = []

        result = None

        # ── Try Gemini AI ──────────────────────────────────────────────────────
        if _get_gemini_model() is not None:
            result = _call_gemini(
                profile=profile,
                matrix_score=matrix_score,
                ats_score=ats_score,
                resume_text=resume_text,
                resume_skills=resume_skills,
            )

        # ── Fallback to heuristic ──────────────────────────────────────────────
        if result is None:
            logger.info("Using heuristic fallback for prediction")
            result = _heuristic_predict(profile, matrix_score, ats_score)

        # ── Parse result ────────────────────────────────────────────────────────
        probability = float(result.get("probability", 50.0))
        c_lower = float(result.get("confidence_lower", max(5.0, probability - 10.0)))
        c_upper = float(result.get("confidence_upper", min(98.0, probability + 8.0)))

        # Build ShapContribution objects
        shap_contributions: list[ShapContribution] = []
        for fc in result.get("feature_contributions", []):
            try:
                shap_contributions.append(ShapContribution(
                    feature=fc.get("feature", "Unknown"),
                    value=float(fc.get("value", 0)),
                    contribution=float(fc.get("contribution", 0)),
                ))
            except (ValueError, KeyError):
                continue

        # Build ActionItem objects
        actions: list[ActionItem] = []
        for ai in result.get("action_items", []):
            try:
                actions.append(ActionItem(
                    priority=int(ai.get("priority", len(actions) + 1)),
                    action=str(ai.get("action", "")),
                    rationale=str(ai.get("rationale", "")),
                    category=str(ai.get("category", "General")),
                ))
            except (ValueError, KeyError):
                continue

        platform_summary = result.get("platform_summary", {})

        probability_pct = round(probability, 1)
        confidence_band = [round(c_lower, 1), round(c_upper, 1)]

        return (probability_pct, confidence_band, shap_contributions, actions, platform_summary)


# Global singleton
predictor = MLPredictor()
