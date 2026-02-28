import io
import re
import logging
from typing import Tuple, List, Dict

logger = logging.getLogger(__name__)

# Try pdfplumber first (much better text extraction), then fall back to PyPDF2
_PDF_BACKEND = None

def _init_pdf_backend():
    global _PDF_BACKEND
    if _PDF_BACKEND is not None:
        return _PDF_BACKEND
    try:
        import pdfplumber  # type: ignore
        _PDF_BACKEND = 'pdfplumber'
    except ImportError:
        try:
            from PyPDF2 import PdfReader  # type: ignore
            _PDF_BACKEND = 'pypdf2'
        except ImportError:
            _PDF_BACKEND = 'none'
    return _PDF_BACKEND


# ─── Comprehensive ATS Keyword Database ─────────────────────────────────────────
ATS_KEYWORD_DB: Dict[str, List[str]] = {
    "programming_languages": [
        "python", "java", "c++", "c#", "javascript", "typescript", "go", "rust",
        "swift", "kotlin", "scala", "ruby", "r", "matlab", "php", "dart",
    ],
    "web_frontend": [
        "react", "angular", "vue", "next.js", "svelte", "html", "css",
        "tailwind", "bootstrap", "redux", "graphql", "webpack", "vite",
    ],
    "web_backend": [
        "node.js", "express", "django", "flask", "fastapi", "spring", "laravel",
        "asp.net", "rest api", "microservices", "grpc",
    ],
    "databases": [
        "sql", "mysql", "postgresql", "mongodb", "redis", "sqlite", "oracle",
        "dynamodb", "cassandra", "elasticsearch", "firebase",
    ],
    "devops_cloud": [
        "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "ansible",
        "ci/cd", "jenkins", "github actions", "linux", "bash", "shell",
    ],
    "ml_ai": [
        "machine learning", "deep learning", "nlp", "computer vision", "tensorflow",
        "pytorch", "scikit-learn", "pandas", "numpy", "keras", "hugging face",
        "llm", "neural network", "data science",
    ],
    "mobile": [
        "android", "ios", "react native", "flutter", "swift", "kotlin", "xamarin",
    ],
    "tools_practices": [
        "git", "agile", "scrum", "jira", "linux", "unix", "api", "algorithms",
        "data structures", "system design", "oop", "design patterns",
    ],
    "soft_skills_professional": [
        "leadership", "teamwork", "communication", "problem solving", "project management",
        "internship", "research", "publication", "open source", "hackathon",
    ],
}

# Flatten to a priority list for ATS scoring
PRIORITY_KEYWORDS = (
    ATS_KEYWORD_DB["programming_languages"][:8]
    + ATS_KEYWORD_DB["web_frontend"][:6]
    + ATS_KEYWORD_DB["web_backend"][:5]
    + ATS_KEYWORD_DB["databases"][:5]
    + ATS_KEYWORD_DB["devops_cloud"][:6]
    + ATS_KEYWORD_DB["ml_ai"][:6]
    + ATS_KEYWORD_DB["tools_practices"][:6]
)


class ResumeParser:
    """
    Extracts rich text from PDF bytes and performs ATS keyword analysis.
    Uses pdfplumber for best results, falls back to PyPDF2 if unavailable.
    """

    @staticmethod
    def extract_text(pdf_bytes: bytes) -> str:
        """
        Reads a byte-stream PDF and returns clean normalized text.
        Uses pdfplumber first (handles tables and complex layouts better),
        falls back to PyPDF2 if not available.
        """
        backend = _init_pdf_backend()

        # ── pdfplumber (preferred) ──────────────────────────────────────────────
        if backend == 'pdfplumber':
            try:
                import pdfplumber
                text_parts = []
                with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                    for page in pdf.pages:
                        # Extract plain text
                        page_text = page.extract_text(x_tolerance=2, y_tolerance=2)
                        if page_text:
                            text_parts.append(page_text)
                        # Also extract table cells (skills often in tables)
                        tables = page.extract_tables()
                        for table in tables:
                            for row in table:
                                for cell in row:
                                    if cell:
                                        text_parts.append(str(cell))

                full_text = " ".join(text_parts)
                full_text = re.sub(r'\s+', ' ', full_text).strip()
                if full_text:
                    logger.info(f"pdfplumber extracted {len(full_text)} characters")
                    return full_text.lower()
            except Exception as e:
                logger.warning(f"pdfplumber failed: {e}, falling back to PyPDF2")

        # ── PyPDF2 fallback ────────────────────────────────────────────────────
        if backend in ('pypdf2', 'pdfplumber'):  # try pypdf2 as fallback too
            try:
                from PyPDF2 import PdfReader
                reader = PdfReader(io.BytesIO(pdf_bytes))
                text_parts = []
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                full_text = " ".join(text_parts)
                full_text = re.sub(r'\s+', ' ', full_text).strip()
                logger.info(f"PyPDF2 extracted {len(full_text)} characters")
                return full_text.lower()
            except Exception as e:
                logger.error(f"PyPDF2 also failed: {e}")

        logger.error("No PDF backend available — returning empty string")
        return ""

    @staticmethod
    def extract_skills(text: str) -> List[str]:
        """
        Extract all matching skills/keywords from resume text.
        Returns a list of found skills (for display in UI).
        """
        if not text:
            return []

        found = []
        all_keywords = []
        for keywords in ATS_KEYWORD_DB.values():
            all_keywords.extend(keywords)

        for kw in all_keywords:
            # Use word-boundary matching for short keywords to avoid false positives
            pattern = r'\b' + re.escape(kw) + r'\b'
            if re.search(pattern, text):
                found.append(kw)

        # Deduplicate while preserving order
        seen = set()
        unique = []
        for kw in found:
            if kw not in seen:
                seen.add(kw)
                unique.append(kw)

        return unique

    @staticmethod
    def calculate_ats_score(
        text: str,
        domain: str = "software_engineering",
        expected_match_count: int = 15
    ) -> Tuple[float, List[str], List[str]]:
        """
        Calculates an ATS Score out of 100 based on keyword density.
        Returns:
           - score (float): 0–100
           - missing keywords (list[str]): top missing keywords
           - found skills (list[str]): all skills found
        """
        if not text or len(text.strip()) < 50:
            return (0.0, ["Resume text could not be extracted — please upload a standard text-based PDF (not a scanned image)."], [])

        # Find all matching keywords
        found_skills = ResumeParser.extract_skills(text)
        found_set = set(found_skills)

        # Find missing priority keywords
        missing = [kw for kw in PRIORITY_KEYWORDS if kw not in found_set]

        # Score: based on priority keyword coverage (out of 15 expected)
        priority_found = sum(1 for kw in PRIORITY_KEYWORDS if kw in found_set)
        raw_score = (priority_found / expected_match_count) * 100.0
        ats_score = min(100.0, raw_score)

        # Add bonus points for depth of skills (breadth across categories)
        categories_represented = sum(
            1 for cat_keywords in ATS_KEYWORD_DB.values()
            if any(kw in found_set for kw in cat_keywords)
        )
        breadth_bonus = min(10.0, categories_represented * 1.5)
        ats_score = min(100.0, ats_score + breadth_bonus)

        # Top 5 missing keywords as actionable gaps
        top_gaps = missing[:5]

        logger.info(
            f"ATS score: {ats_score:.1f} | "
            f"Found {len(found_skills)} skills | "
            f"Missing top: {top_gaps}"
        )

        return (round(ats_score, 1), top_gaps, found_skills)
