from typing import Optional, List
from pydantic import BaseModel

# ── Input schemas ──────────────────────────────────────────────────────────────

class AcademicDetails(BaseModel):
    cgpa: float
    cgpaScale: int
    tenthPct: float
    twelfthPct: float
    branch: str
    year: int
    backlogs: int


class CodingDetails(BaseModel):
    # LeetCode
    lcTotalSolved: int = 0
    lcEasySolved: int = 0
    lcMediumSolved: int = 0
    lcHardSolved: int = 0
    lcActiveDays: int = 0
    lcRanking: int = 0

    # GitHub
    githubRepos: int = 0
    githubFollowers: int = 0
    githubStars: int = 0
    githubYearlyContributions: int = 0
    githubRecentCommits: int = 0

    # CodeChef
    ccRating: int = 0
    ccStars: str = "0★"
    ccSolved: int = 0
    ccGlobalRank: int = 0

    # Codeforces
    cfRating: int = 0
    cfMaxRating: int = 0
    cfRank: str = "unrated"
    cfSolved: int = 0

    # Legacy fields (backward compat with scorer.py)
    lcSubmissions: int = 0
    hrBadges: int = 0
    hrMedHardSolved: int = 0
    githubContributions: int = 0
    githubCollaborations: int = 0
    githubMonthlyActive: bool = False

    def model_post_init(self, __context):
        """Auto-populate legacy fields from new fields if not already set."""
        if self.lcSubmissions == 0 and self.lcTotalSolved > 0:
            self.lcSubmissions = self.lcTotalSolved
        if self.hrMedHardSolved == 0:
            self.hrMedHardSolved = self.lcMediumSolved + self.lcHardSolved
        if self.githubContributions == 0:
            if self.githubYearlyContributions > 0:
                self.githubContributions = self.githubYearlyContributions
            elif self.githubRepos > 0:
                self.githubContributions = self.githubRepos * 10
        if self.githubCollaborations == 0:
            self.githubCollaborations = self.githubFollowers
        if not self.githubMonthlyActive:
            self.githubMonthlyActive = (
                self.githubYearlyContributions > 50
                or self.lcActiveDays > 30
            )


class ExperienceDetails(BaseModel):
    internshipType: str = "none"
    internshipCount: int = 0
    internshipStipendAbove10k: bool = False
    projectsIndustry: int = 0
    projectsDomain: int = 0
    certsGlobal: int = 0
    certsNptel: int = 0
    certsRbu: int = 0
    hackathonFirst: int = 0
    hackathonSecond: int = 0
    hackathonThird: int = 0
    hackathonParticipation: int = 0


class ProfileSubmissionRequest(BaseModel):
    """Incoming form payload — matches React WizardFormData shape."""
    academic: AcademicDetails
    coding: CodingDetails
    experience: ExperienceDetails


# ── Output / breakdown schemas ─────────────────────────────────────────────────

class MatrixCategoryBreakdown(BaseModel):
    score: float
    maxScore: float


class MatrixBreakdown(BaseModel):
    academics: MatrixCategoryBreakdown
    internship: MatrixCategoryBreakdown
    projects: MatrixCategoryBreakdown
    coding: MatrixCategoryBreakdown
    hackathons: MatrixCategoryBreakdown
    certifications: MatrixCategoryBreakdown


class ShapContribution(BaseModel):
    feature: str
    value: float
    contribution: float = 0.0


class ActionItem(BaseModel):
    priority: int
    action: str
    rationale: str
    category: str


class ResumeInsights(BaseModel):
    skills: List[str] = []
    experience_summary: str = ""
    project_highlights: List[str] = []
    education: str = ""
    strengths: List[str] = []
    weaknesses: List[str] = []


class AnalysisResponse(BaseModel):
    # Core result
    submissionId: str
    probability: float
    confidenceBand: List[float]          # [lower, upper]
    matrixScore: float
    matrixBreakdown: MatrixBreakdown

    # ATS
    atsScore: float
    keywordGaps: List[str]
    resumeSkills: List[str] = []

    # Explainability
    shapContributions: List[ShapContribution]
    actions: List[ActionItem]

    # Meta
    processingMs: int
    platformSummary: dict = {}

    # Extra scorer fields — Optional so GET and what-if responses work without them
    base_probability: Optional[float] = None
    adjustment_breakdown: Optional[dict] = None
    extra_score: Optional[float] = None
