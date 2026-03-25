import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { PageLayout } from '@/components/layout/PageLayout'
import { FormInput } from '@/components/ui/FormInput'
import { Button } from '@/components/ui/Button'
import { CategoryRow } from '@/components/results/CategoryRow'
import { useAnalysisResult, useWhatIf } from '@/hooks/useAnalysis'
import type { AnalysisResult, WhatIfPayload } from '@/hooks/useAnalysis'
import type { MatrixBreakdown } from '@/components/results/MatrixScoreCard'

// ── Types ─────────────────────────────────────────────────────────────────────

type EditableFields = {
    lcSubmissions:       number
    githubContributions: number
    projectsDomain:      number
    certsGlobal:         number
    hackathonFirst:      number
}

// ── UI helpers ────────────────────────────────────────────────────────────────

function DeltaBadge({ delta }: { delta: number }) {
    if (delta === 0) return <span className="text-xs text-slate-400">—</span>
    const color = delta > 0 ? 'text-emerald-600' : 'text-red-500'
    return (
        <span className={`text-sm font-semibold ${color}`}>
            {delta > 0 ? '↑' : '↓'} {Math.abs(delta).toFixed(1)}
        </span>
    )
}

function ScoreBlock({ label, value, highlighted }: {
    label: string
    value: number
    highlighted?: boolean
}) {
    return (
        <div className={`rounded-2xl border p-5 text-center ${
            highlighted
                ? 'border-indigo-300 ring-2 ring-indigo-200 bg-indigo-50'
                : 'border-slate-100 bg-white'
        }`}>
            <p className="text-xs text-slate-500 mb-1">{label}</p>
            <p className={`text-4xl font-bold ${highlighted ? 'text-indigo-600' : 'text-slate-900'}`}>
                {value.toFixed(1)}%
            </p>
        </div>
    )
}

const MATRIX_KEYS: { key: keyof MatrixBreakdown; label: string }[] = [
    { key: 'coding',         label: 'Coding Platforms' },
    { key: 'projects',       label: 'Projects' },
    { key: 'certifications', label: 'Certifications' },
    { key: 'hackathons',     label: 'Hackathons' },
]

// Extract a numeric value from SHAP contributions by matching feature name
function shapValue(result: AnalysisResult, featureSubstring: string): number {
    return result.shapContributions.find(
        (c) => c.feature.toLowerCase().includes(featureSubstring.toLowerCase())
    )?.value ?? 0
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function WhatIf() {
    const { id } = useParams<{ id: string }>()
    const { data: original, isLoading } = useAnalysisResult(id ?? '')
    const whatIfMutation = useWhatIf()

    const [newResult, setNewResult] = useState<AnalysisResult | null>(null)
    const [noChanges, setNoChanges]   = useState(false)
    const [fields, setFields] = useState<EditableFields>({
        lcSubmissions:       0,
        githubContributions: 0,
        projectsDomain:      0,
        certsGlobal:         0,
        hackathonFirst:      0,
    })

    function handleRecalculate() {
        if (!original) return

        const hasChange = Object.values(fields).some((v) => v !== 0)
        if (!hasChange) { setNoChanges(true); return }
        setNoChanges(false)

        const baseLcSolved       = shapValue(original, 'LeetCode Solved')
        const baseGithubContribs = shapValue(original, 'GitHub Contributions')

        const payload: WhatIfPayload = {
            profile: {
                lc_total_solved:      baseLcSolved       + fields.lcSubmissions,
                lc_submissions:       baseLcSolved       + fields.lcSubmissions,
                github_contributions: baseGithubContribs + fields.githubContributions,
            },
            experience: {
                projects_domain: fields.projectsDomain || undefined,
                certs_global:    fields.certsGlobal    || undefined,
                hackathon_first: fields.hackathonFirst || undefined,
            },
            ats_score: original.atsScore,
            base_profile: {
                academic: {
                    cgpa:       shapValue(original, 'CGPA'),
                    cgpaScale:  10,
                    tenthPct:   0,
                    twelfthPct: 0,
                    branch:     'CSE',
                    year:       3,
                    backlogs:   Math.round(shapValue(original, 'Backlogs')),
                },
                coding: {
                    lcTotalSolved:       baseLcSolved,
                    lcSubmissions:       baseLcSolved,
                    lcHardSolved:        shapValue(original, 'LeetCode Hard'),
                    lcMediumSolved:      shapValue(original, 'LeetCode Med'),
                    lcEasySolved:        0,
                    lcActiveDays:        shapValue(original, 'Active Days'),
                    githubContributions: baseGithubContribs,
                    cfRating:            shapValue(original, 'Codeforces Rating'),
                },
                experience: {
                    internshipType:           'none',
                    internshipCount:          Math.round(shapValue(original, 'Internships')),
                    internshipStipendAbove10k: false,
                    projectsDomain:           0,
                    projectsIndustry:         0,
                    certsGlobal:              0,
                    certsNptel:               0,
                    certsRbu:                 0,
                    hackathonFirst:           0,
                    hackathonSecond:          0,
                    hackathonThird:           0,
                    hackathonParticipation:   0,
                },
            },
        }

        whatIfMutation.mutate(payload, {
            onSuccess: (data) => setNewResult(data),
        })
    }

    // Loading / not found states
    if (isLoading) {
        return (
            <PageLayout>
                <div className="flex items-center justify-center py-32">
                    <p className="text-slate-400 text-sm animate-pulse">Loading original result…</p>
                </div>
            </PageLayout>
        )
    }

    if (!original) {
        return (
            <PageLayout>
                <div className="flex flex-col items-center py-32 gap-4 text-center">
                    <p className="text-slate-500">Original result not found.</p>
                    <Link to="/dashboard" className="text-sm text-indigo-600 hover:underline">
                        ← Back to Dashboard
                    </Link>
                </div>
            </PageLayout>
        )
    }

    const probDelta   = newResult ? newResult.probability - original.probability  : null
    const matrixDelta = newResult ? newResult.matrixScore  - original.matrixScore : null

    return (
        <PageLayout>
            {/* Header */}
            <div className="mb-6">
                <Link to={`/results/${id}`} className="text-sm text-indigo-600 hover:underline">
                    ← Back to Results
                </Link>
                <h1 className="text-2xl font-bold text-slate-900 mt-2">What-If Simulator</h1>
                <p className="text-sm text-slate-500 mt-1">
                    Enter the changes you plan to make and see how they affect your placement probability.
                </p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">

                {/* ── Left: Inputs ─────────────────────────────────────────── */}
                <div className="bg-white rounded-2xl border border-slate-100 p-6 flex flex-col gap-5">
                    <h2 className="font-semibold text-slate-800">Adjust Your Inputs</h2>
                    <div className="bg-slate-50 rounded-xl p-3 text-xs text-slate-500">
                        Enter the <strong>additional amount</strong> you plan to achieve
                        (e.g. +50 LC problems), then click Recalculate.
                    </div>

                    <FormInput
                        label="Additional LeetCode Problems Solved"
                        type="number"
                        min={0}
                        hint={`Current: ${Math.round(shapValue(original, 'LeetCode Solved'))}`}
                        value={fields.lcSubmissions || ''}
                        onChange={(e) =>
                            setFields((f) => ({ ...f, lcSubmissions: Math.max(0, +e.target.value) }))
                        }
                    />
                    <FormInput
                        label="Additional GitHub Contributions"
                        type="number"
                        min={0}
                        hint={`Current: ${Math.round(shapValue(original, 'GitHub Contributions'))}`}
                        value={fields.githubContributions || ''}
                        onChange={(e) =>
                            setFields((f) => ({ ...f, githubContributions: Math.max(0, +e.target.value) }))
                        }
                    />
                    <FormInput
                        label="Additional Domain Projects"
                        type="number"
                        min={0}
                        value={fields.projectsDomain || ''}
                        onChange={(e) =>
                            setFields((f) => ({ ...f, projectsDomain: Math.max(0, +e.target.value) }))
                        }
                    />
                    <FormInput
                        label="Additional Global Certifications"
                        type="number"
                        min={0}
                        value={fields.certsGlobal || ''}
                        onChange={(e) =>
                            setFields((f) => ({ ...f, certsGlobal: Math.max(0, +e.target.value) }))
                        }
                    />
                    <FormInput
                        label="Additional Hackathon 1st Prize Wins"
                        type="number"
                        min={0}
                        value={fields.hackathonFirst || ''}
                        onChange={(e) =>
                            setFields((f) => ({ ...f, hackathonFirst: Math.max(0, +e.target.value) }))
                        }
                    />

                    {noChanges && (
                        <p className="text-xs text-amber-600">
                            No changes detected. Edit at least one field above.
                        </p>
                    )}
                    {whatIfMutation.isError && (
                        <p className="text-xs text-red-500">
                            Recalculation failed. Please try again.
                        </p>
                    )}

                    <Button
                        onClick={handleRecalculate}
                        isLoading={whatIfMutation.isPending}
                        className="w-full"
                    >
                        Recalculate →
                    </Button>
                </div>

                {/* ── Right: Results ───────────────────────────────────────── */}
                <div className="flex flex-col gap-5">

                    {/* Probability */}
                    <div>
                        <p className="text-sm font-medium text-slate-600 mb-3">Placement Probability</p>
                        <div className="grid grid-cols-3 items-center gap-3">
                            <ScoreBlock label="Original" value={original.probability} />
                            <div className="text-center">
                                {probDelta !== null
                                    ? <DeltaBadge delta={probDelta} />
                                    : <span className="text-slate-300 text-lg">→</span>
                                }
                            </div>
                            <ScoreBlock
                                label="Projected"
                                value={newResult?.probability ?? original.probability}
                                highlighted={!!newResult}
                            />
                        </div>
                    </div>

                    {/* Matrix breakdown */}
                    <div className="bg-white rounded-2xl border border-slate-100 p-5">
                        <div className="flex justify-between items-center mb-4">
                            <p className="text-sm font-medium text-slate-600">Matrix Score</p>
                            <div className="flex items-center gap-2">
                                <span className="text-slate-400 text-sm">
                                    {original.matrixScore.toFixed(1)}/100
                                </span>
                                {matrixDelta !== null && (
                                    <>
                                        <span className="text-slate-300">→</span>
                                        <span className="font-semibold text-slate-800">
                                            {newResult!.matrixScore.toFixed(1)}/100
                                        </span>
                                        <DeltaBadge delta={matrixDelta} />
                                    </>
                                )}
                            </div>
                        </div>

                        <div className="flex flex-col gap-3">
                            {MATRIX_KEYS.map(({ key, label }) => {
                                const curr = (newResult ?? original).matrixBreakdown[key]
                                const orig = original.matrixBreakdown[key]
                                const changed = !!newResult && curr.earned !== orig.earned

                                return (
                                    <div
                                        key={key}
                                        className={changed ? 'bg-emerald-50 rounded-lg p-2 -mx-2' : ''}
                                    >
                                        <div className="flex items-center gap-2 mb-1">
                                            <span className="text-xs text-slate-600 w-36">{label}</span>
                                            {changed && (
                                                <span className="text-xs text-emerald-600 font-medium">
                                                    {orig.earned.toFixed(1)} → {curr.earned.toFixed(1)} pts ✅
                                                </span>
                                            )}
                                        </div>
                                        <CategoryRow
                                            label=""
                                            earned={curr.earned}
                                            max={curr.max}
                                        />
                                    </div>
                                )
                            })}
                        </div>
                    </div>

                    {/* Placeholder */}
                    {!newResult && (
                        <div className="flex items-center justify-center bg-slate-50 rounded-2xl border-2 border-dashed border-slate-200 p-8 text-center">
                            <p className="text-sm text-slate-400">
                                Edit a field and click Recalculate to see your projected score
                            </p>
                        </div>
                    )}
                </div>
            </div>
        </PageLayout>
    )
}
