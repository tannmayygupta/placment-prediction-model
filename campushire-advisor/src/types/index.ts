// ─── Auth ────────────────────────────────────────────────────────────────────
export interface User {
    id: string
    email: string
    name: string
}

export interface AuthState {
    user: User | null
    isAuthenticated: boolean
}

// ─── Profile / Wizard ────────────────────────────────────────────────────────
export interface AcademicProfile {
    cgpa: number
    cgpaScale: 10 | 4
    tenthPct: number
    twelfthPct: number
    branch: string
    year: number
    backlogs: number
}

export interface CodingActivity {
    // LeetCode
    lcTotalSolved: number
    lcEasySolved: number
    lcMediumSolved: number
    lcHardSolved: number
    lcActiveDays: number
    lcRanking: number

    // GitHub
    githubRepos: number
    githubFollowers: number
    githubStars: number

    // CodeChef
    ccRating: number
    ccStars: string
    ccSolved: number
    ccGlobalRank: number

    // Codeforces
    cfRating: number
    cfMaxRating: number
    cfRank: string
    cfSolved: number

    // Legacy fields for backward compat with scorer
    lcSubmissions: number          // = lcTotalSolved
    hrBadges: number
    hrMedHardSolved: number        // = lcMediumSolved + lcHardSolved
    githubContributions: number    // = githubRepos * 10 (proxy)
    githubCollaborations: number   // = githubFollowers
    githubMonthlyActive: boolean
}

export type InternshipType = 'international' | 'it_company' | 'eduskills' | 'none'

export interface ExperienceAchievements {
    internshipType: InternshipType
    internshipCount: number
    internshipStipendAbove10k: boolean
    projectsIndustry: number
    projectsDomain: number
    certsGlobal: number
    certsNptel: number
    certsRbu: number
    hackathonFirst: number
    hackathonSecond: number
    hackathonThird: number
    hackathonParticipation: number
}

export interface WizardFormData {
    academic: AcademicProfile
    coding: CodingActivity
    experience: ExperienceAchievements
    resumeFile: File | null
}

// ─── Platform raw data stored in wizard state ─────────────────────────────────
export interface PlatformRawData {
    leetcode: {
        username: string
        totalSolved: number
        easySolved: number
        mediumSolved: number
        hardSolved: number
        activeDays: number
        ranking: number
    } | null
    github: {
        username: string
        repos: number
        followers: number
        stars: number
    } | null
    codeforces: {
        handle: string
        rating: number
        maxRating: number
        rank: string
        solved: number
    } | null
    codechef: {
        username: string
        rating: number
        stars: string
        solved: number
        globalRank: number
    } | null
}

// ─── Analysis Results ─────────────────────────────────────────────────────────
export interface ShapContribution {
    feature: string
    value: number
    contribution: number
}

export interface Action {
    priority: number
    action: string
    rationale: string
    category: string
}

export interface CategoryScore {
    score: number
    maxScore: number
}

export interface MatrixBreakdown {
    academics: CategoryScore
    internship: CategoryScore
    projects: CategoryScore
    coding: CategoryScore
    hackathons: CategoryScore
    certifications: CategoryScore
}

export interface AnalysisResult {
    submissionId: string
    probability: number
    confidenceBand: [number, number]
    atsScore: number
    keywordGaps: string[]
    resumeSkills: string[]
    matrixScore: number
    matrixBreakdown: MatrixBreakdown
    shapContributions: ShapContribution[]
    actions: Action[]
    processingMs: number
    platformSummary?: PlatformSummary
}

export interface PlatformSummary {
    leetcode: string
    github: string
    codeforces: string
    codechef: string
}

// ─── API Responses ────────────────────────────────────────────────────────────
export interface ApiError {
    detail: string
    status: number
}
