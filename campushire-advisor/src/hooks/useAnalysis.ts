import { useMutation, useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import api from '@/lib/api'
import type { WizardFormData } from '@/types'
import type { MatrixBreakdown } from '@/components/results/MatrixScoreCard'

// ── Core result types ─────────────────────────────────────────────────────────

export interface AdjustmentBreakdown {
    internship?: number
    lor?: number
    hackathon?: number
    synergy?: number
}

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

export interface AnalysisResult {
    submissionId: string
    probability: number
    baseProbability: number | null
    extraScore: number | null
    adjustmentBreakdown: AdjustmentBreakdown | null
    confidenceBand: [number, number]
    atsScore: number
    keywordGaps: string[]
    resumeSkills?: string[]
    matrixScore: number
    matrixBreakdown: MatrixBreakdown
    shapContributions: ShapContribution[]
    actions: Action[]
    processingMs: number
}

// ── WhatIf payload types (exported — used by WhatIf.tsx) ─────────────────────

export interface WhatIfBaseProfile {
    academic: {
        cgpa: number
        cgpaScale: number
        tenthPct: number
        twelfthPct: number
        branch: string
        year: number
        backlogs: number
    }
    coding: {
        lcTotalSolved?: number
        lcSubmissions?: number
        lcHardSolved?: number
        lcMediumSolved?: number
        lcEasySolved?: number
        lcActiveDays?: number
        githubContributions?: number
        cfRating?: number
        [key: string]: unknown
    }
    experience: {
        internshipType: string
        internshipCount: number
        internshipStipendAbove10k: boolean
        projectsDomain: number
        projectsIndustry: number
        certsGlobal: number
        certsNptel: number
        certsRbu: number
        hackathonFirst: number
        hackathonSecond: number
        hackathonThird: number
        hackathonParticipation: number
        [key: string]: unknown
    }
}

export interface WhatIfPayload {
    profile: Record<string, unknown>
    experience: Record<string, unknown>
    ats_score?: number
    base_profile?: WhatIfBaseProfile
}

// ── Response transformer ──────────────────────────────────────────────────────
//
// Handles both response shapes without throwing:
//
//   POST /analyse  → camelCase Pydantic serialization
//                    matrixBreakdown keys: academics, coding, internship, …
//                    each { score, maxScore }
//
//   GET /analyse/:id → same shape (normalized before DB save in analysis.py)
//
//   POST /analyse/whatif → same shape as POST /analyse

function transformResult(raw: Record<string, unknown>): AnalysisResult {
    // submissionId — FastAPI serializes as camelCase
    const submissionId = (raw.submissionId ?? raw.submission_id) as string

    // Matrix breakdown — backend always returns { score, maxScore } per category
    const rb = (
        raw.matrixBreakdown ?? raw.matrix_breakdown
    ) as Record<string, {
        score?: number; maxScore?: number; max_score?: number;
        earned?: number; max?: number
    }> ?? {}

    // Unified getters handle all possible backend key variants
    const getEarned = (key: string): number =>
        rb[key]?.score ?? rb[key]?.earned ?? 0

    const getMax = (key: string): number =>
        rb[key]?.maxScore ?? rb[key]?.max_score ?? rb[key]?.max ?? 0

    const matrixBreakdown: MatrixBreakdown = {
        academics:      { earned: getEarned('academics'),      max: getMax('academics') },
        coding:         { earned: getEarned('coding'),         max: getMax('coding') },
        internship:     { earned: getEarned('internship'),     max: getMax('internship') },
        projects:       { earned: getEarned('projects'),       max: getMax('projects') },
        certifications: { earned: getEarned('certifications'), max: getMax('certifications') },
        hackathons:     { earned: getEarned('hackathons'),     max: getMax('hackathons') },
    }

    return {
        submissionId,
        probability:         (raw.probability as number)                                                    ?? 0,
        baseProbability:     ((raw.baseProbability  ?? raw.base_probability)  as number  | null)            ?? null,
        extraScore:          ((raw.extraScore       ?? raw.extra_score)       as number  | null)            ?? null,
        adjustmentBreakdown: ((raw.adjustmentBreakdown ?? raw.adjustment_breakdown) as AdjustmentBreakdown | null) ?? null,
        confidenceBand:      ((raw.confidenceBand   ?? raw.confidence_band)   as [number, number])          ?? [0, 100],
        atsScore:            ((raw.atsScore         ?? raw.ats_score)         as number)                    ?? 0,
        keywordGaps:         ((raw.keywordGaps      ?? raw.keyword_gaps)      as string[])                  ?? [],
        resumeSkills:        ((raw.resumeSkills     ?? raw.resume_skills)     as string[] | undefined),
        matrixScore:         ((raw.matrixScore      ?? raw.matrix_score)      as number)                    ?? 0,
        matrixBreakdown,
        shapContributions:   ((raw.shapContributions ?? raw.shap_contributions) as ShapContribution[])      ?? [],
        actions:             (raw.actions as Action[])                                                      ?? [],
        processingMs:        ((raw.processingMs     ?? raw.processing_ms)     as number)                    ?? 0,
    }
}

// ── useSubmitAnalysis ─────────────────────────────────────────────────────────

export function useSubmitAnalysis() {
    const navigate = useNavigate()

    return useMutation({
        mutationFn: async (formData: WizardFormData) => {
            const fd = new FormData()

            const profilePayload = {
                academic: {
                    cgpa:        formData.academic?.cgpa,
                    cgpaScale:   formData.academic?.cgpaScale,
                    tenthPct:    formData.academic?.tenthPct,
                    twelfthPct:  formData.academic?.twelfthPct,
                    branch:      formData.academic?.branch,
                    year:        formData.academic?.year,
                    backlogs:    formData.academic?.backlogs,
                },
                coding: {
                    lcTotalSolved:             formData.coding?.lcTotalSolved,
                    lcSubmissions:             formData.coding?.lcSubmissions,
                    lcEasySolved:              formData.coding?.lcEasySolved,
                    lcMediumSolved:            formData.coding?.lcMediumSolved,
                    lcHardSolved:              formData.coding?.lcHardSolved,
                    lcActiveDays:              formData.coding?.lcActiveDays,
                    lcRanking:                 formData.coding?.lcRanking,
                    hrBadges:                  formData.coding?.hrBadges,
                    hrMedHardSolved:           formData.coding?.hrMedHardSolved,
                    githubYearlyContributions: formData.coding?.githubContributions,  // map to new field
                    githubContributions:       formData.coding?.githubContributions,  // legacy compat
                    githubCollaborations:      formData.coding?.githubCollaborations,
                    githubMonthlyActive:       formData.coding?.githubMonthlyActive,
                    githubRepos:               formData.coding?.githubRepos,
                    githubFollowers:           formData.coding?.githubFollowers,
                    githubStars:               formData.coding?.githubStars,
                    cfRating:                  formData.coding?.cfRating,
                    cfMaxRating:               formData.coding?.cfMaxRating,
                    cfRank:                    formData.coding?.cfRank,
                    cfSolved:                  formData.coding?.cfSolved,
                    ccRating:                  formData.coding?.ccRating,
                    ccStars:                   formData.coding?.ccStars,
                    ccSolved:                  formData.coding?.ccSolved,
                    ccGlobalRank:              formData.coding?.ccGlobalRank,
                },
                experience: {
                    internshipType:            formData.experience?.internshipType            ?? 'none',
                    internshipCount:           formData.experience?.internshipCount           ?? 0,
                    internshipStipendAbove10k: formData.experience?.internshipStipendAbove10k ?? false,
                    projectsIndustry:          formData.experience?.projectsIndustry          ?? 0,
                    projectsDomain:            formData.experience?.projectsDomain            ?? 0,
                    certsGlobal:               formData.experience?.certsGlobal               ?? 0,
                    certsNptel:                formData.experience?.certsNptel                ?? 0,
                    certsRbu:                  formData.experience?.certsRbu                  ?? 0,
                    hackathonFirst:            formData.experience?.hackathonFirst            ?? 0,
                    hackathonSecond:           formData.experience?.hackathonSecond           ?? 0,
                    hackathonThird:            formData.experience?.hackathonThird            ?? 0,
                    hackathonParticipation:    formData.experience?.hackathonParticipation    ?? 0,
                },
            }

            fd.append('profile', JSON.stringify(profilePayload))
            fd.append('resume', formData.resumeFile as File)

            const response = await api.post('/analyse', fd, {
                headers: { 'Content-Type': 'multipart/form-data' },
            })
            return transformResult(response.data)
        },
        onSuccess: (result) => {
            // submissionId is now guaranteed to be a real UUID — navigate safely
            navigate(`/results/${result.submissionId}`)
        },
    })
}

// ── useAnalysisResult ─────────────────────────────────────────────────────────

export function useAnalysisResult(submissionId: string) {
    return useQuery({
        queryKey: ['analysis', submissionId],
        queryFn: async () => {
            const response = await api.get(`/analyse/${submissionId}`)
            return transformResult(response.data)
        },
        // Guard against 'undefined' string navigated from a failed POST
        enabled: !!submissionId && submissionId !== 'undefined' && submissionId !== 'whatif',
        staleTime: 1000 * 60 * 10,
        retry: 1,
    })
}

// ── useWhatIf ─────────────────────────────────────────────────────────────────

export function useWhatIf() {
    return useMutation({
        mutationFn: async (payload: WhatIfPayload) => {
            const response = await api.post('/analyse/whatif', payload)
            return transformResult(response.data)
        },
    })
}
