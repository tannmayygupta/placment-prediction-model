import type { ShapContribution } from '@/types'

interface SHAPBarChartProps {
    contributions: ShapContribution[]
}

// ─── Impact descriptions shown in tooltip/legend ─────────────────────────────
const IMPACT_INFO: Record<string, { label: string; icon: string; detail: string }> = {
    'cgpa': { label: 'CGPA', icon: '🎓', detail: 'Academic score — eligibility filter for most companies' },
    'leetcode': { label: 'LeetCode', icon: '🟨', detail: 'DSA problem-solving — primary filter for tech companies' },
    'leetcode solved': { label: 'LeetCode Solved', icon: '🟨', detail: 'Total problems solved — core DSA metric' },
    'leetcode active days': { label: 'LC Active Days', icon: '📅', detail: 'Consistency of practice — shows discipline to recruiters' },
    'leetcode hard': { label: 'LeetCode Hard', icon: '🔴', detail: 'Hard problem count — differentiates tier-1 candidates' },
    'github': { label: 'GitHub Activity', icon: '🐙', detail: 'Code contributions — shows real-world coding output' },
    'github contributions': { label: 'GitHub Contributions', icon: '🐙', detail: 'Yearly contributions — proof of consistent output' },
    'codeforces': { label: 'Codeforces Rating', icon: '🔵', detail: 'Competitive rating — highly valued by product companies' },
    'ats': { label: 'ATS Resume Score', icon: '📄', detail: 'Resume quality — gets you past automated screening bots' },
    'resume': { label: 'Resume Score', icon: '📄', detail: 'Keyword-match score against JD templates' },
    'backlogs': { label: 'Active Backlogs', icon: '⚠️', detail: 'Pending backlogs — hard disqualifier at many companies' },
    'internship': { label: 'Internships', icon: '💼', detail: 'Industry exposure — boosts credibility significantly' },
}

function getFeatureInfo(featureRaw: string): { label: string; icon: string; detail: string } {
    const f = featureRaw.toLowerCase()
    for (const [key, info] of Object.entries(IMPACT_INFO)) {
        if (f.includes(key)) return info
    }
    // Fallback: clean up the raw feature name
    const clean = featureRaw
        .replace(/_/g, ' ')
        .replace(/([A-Z])/g, ' $1')
        .replace(/\s+/g, ' ')
        .trim()
    return { label: clean, icon: '📊', detail: 'Contributes to your placement probability' }
}

export function SHAPBarChart({ contributions }: SHAPBarChartProps) {
    if (!contributions?.length) return null

    // Sort: most impactful (by absolute value) first, max 8 items
    const sorted = [...contributions]
        .sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution))
        .slice(0, 8)

    const maxAbs = Math.max(...sorted.map((c) => Math.abs(c.contribution)), 0.01)

    const positives = sorted.filter((c) => c.contribution > 0)
    const negatives = sorted.filter((c) => c.contribution < 0)
    const neutrals = sorted.filter((c) => c.contribution === 0)
    const displayed = [...positives, ...negatives, ...neutrals]

    return (
        <div className="space-y-3">
            {/* ── Legend ── */}
            <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500 mb-1">
                <span className="flex items-center gap-1.5">
                    <span className="inline-block w-3 h-3 rounded-sm bg-gradient-to-r from-indigo-400 to-indigo-600" />
                    Boosts placement chances
                </span>
                <span className="flex items-center gap-1.5">
                    <span className="inline-block w-3 h-3 rounded-sm bg-gradient-to-r from-red-400 to-red-600" />
                    Hurts placement chances
                </span>
                <span className="flex items-center gap-1.5 ml-auto font-medium text-slate-400">
                    Bar width = strength of impact
                </span>
            </div>

            {/* ── Bars ── */}
            <div className="space-y-2">
                {displayed.map((item, idx) => {
                    const info = getFeatureInfo(item.feature)
                    const pct = (Math.abs(item.contribution) / maxAbs) * 100
                    const isPositive = item.contribution > 0
                    const isNeutral = item.contribution === 0
                    const impactLabel = isNeutral ? 'Neutral' : isPositive ? `+${(item.contribution * 100).toFixed(1)}%` : `${(item.contribution * 100).toFixed(1)}%`

                    const barColor = isNeutral
                        ? 'from-slate-200 to-slate-300'
                        : isPositive
                            ? 'from-indigo-400 to-indigo-600'
                            : 'from-red-400 to-red-600'

                    const badgeBg = isNeutral
                        ? 'bg-slate-100 text-slate-500'
                        : isPositive
                            ? 'bg-indigo-50 text-indigo-700'
                            : 'bg-red-50 text-red-700'

                    return (
                        <div key={idx} className="group">
                            {/* Row header */}
                            <div className="flex items-center justify-between mb-0.5">
                                <div className="flex items-center gap-1.5 min-w-0">
                                    <span className="text-base leading-none">{info.icon}</span>
                                    <span className="text-sm font-semibold text-slate-700 truncate">
                                        {info.label}
                                    </span>
                                    <span className="text-xs text-slate-400 hidden sm:inline truncate max-w-[200px]">
                                        — {info.detail}
                                    </span>
                                </div>
                                <span className={`ml-2 text-xs font-bold px-2 py-0.5 rounded-full ${badgeBg} shrink-0`}>
                                    {impactLabel}
                                </span>
                            </div>

                            {/* Bar track */}
                            <div className="relative h-5 bg-slate-100 rounded-full overflow-hidden">
                                {/* Animated bar */}
                                <div
                                    className={`h-full rounded-full bg-gradient-to-r ${barColor} transition-all duration-700`}
                                    style={{ width: `${Math.max(pct, 2)}%` }}
                                />
                                {/* Value label inside bar */}
                                {pct > 20 && (
                                    <span className="absolute inset-y-0 left-3 flex items-center text-[10px] font-bold text-white/90 pointer-events-none">
                                        {item.value !== undefined ? `Current: ${typeof item.value === 'number' ? item.value.toFixed(item.value % 1 === 0 ? 0 : 1) : item.value}` : ''}
                                    </span>
                                )}
                            </div>

                            {/* Mobile tooltip row */}
                            <p className="text-xs text-slate-400 sm:hidden mt-0.5 pl-1">{info.detail}</p>
                        </div>
                    )
                })}
            </div>

            {/* ── How to read this ── */}
            <div className="mt-4 pt-3 border-t border-slate-100">
                <p className="text-xs text-slate-400 leading-relaxed">
                    <span className="font-semibold text-slate-600">How to read: </span>
                    Each bar shows how much that factor <span className="text-indigo-600 font-medium">increases</span> or{' '}
                    <span className="text-red-500 font-medium">decreases</span> your placement probability.
                    The wider the bar, the stronger the impact. Focus on fixing the{' '}
                    <span className="text-red-500 font-medium">red bars</span> — they're your biggest opportunities.
                </p>
            </div>
        </div>
    )
}
