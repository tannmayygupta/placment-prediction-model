interface ATSScoreCardProps {
    atsScore: number
    keywordGaps: string[]
    resumeSkills?: string[]
}

function getScoreColor(score: number) {
    if (score >= 75) return 'text-emerald-600'
    if (score >= 50) return 'text-amber-600'
    return 'text-red-500'
}

function getScoreBg(score: number) {
    if (score >= 75) return 'bg-emerald-50 border-emerald-200'
    if (score >= 50) return 'bg-amber-50 border-amber-200'
    return 'bg-red-50 border-red-200'
}

function getScoreLabel(score: number) {
    if (score >= 80) return '🟢 Excellent ATS Match'
    if (score >= 65) return '🟡 Good ATS Match'
    if (score >= 45) return '🟠 Average ATS Match'
    return '🔴 Below ATS Threshold'
}

export function ATSScoreCard({ atsScore, keywordGaps, resumeSkills = [] }: ATSScoreCardProps) {
    // Show at most 20 skills to avoid clutter
    const displaySkills = resumeSkills.slice(0, 24)

    return (
        <div className="bg-white rounded-2xl border border-slate-100 p-6">
            <div className="flex justify-between items-baseline mb-3">
                <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide">
                    Resume ATS Score
                </h2>
                <span className={`text-2xl font-bold ${getScoreColor(atsScore)}`}>
                    {atsScore.toFixed(0)}
                    <span className="text-sm font-normal text-slate-400">/100</span>
                </span>
            </div>

            {/* Score label badge */}
            <div className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-medium border mb-4 ${getScoreBg(atsScore)}`}>
                {getScoreLabel(atsScore)}
            </div>

            {/* Found skills */}
            {displaySkills.length > 0 && (
                <div className="mb-4">
                    <p className="text-xs font-medium text-slate-500 mb-2">
                        ✅ Skills detected in your resume ({resumeSkills.length} total)
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                        {displaySkills.map((kw) => (
                            <span
                                key={kw}
                                className="bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full px-2.5 py-0.5 text-xs font-medium"
                            >
                                {kw}
                            </span>
                        ))}
                        {resumeSkills.length > 24 && (
                            <span className="text-xs text-slate-400 self-center">
                                +{resumeSkills.length - 24} more
                            </span>
                        )}
                    </div>
                </div>
            )}

            {/* Missing keywords */}
            {keywordGaps.length > 0 && (
                <div>
                    <p className="text-xs font-medium text-slate-500 mb-2">
                        ⚠️ Missing high-priority keywords
                    </p>
                    <div className="flex flex-wrap gap-2">
                        {keywordGaps.map((kw) => (
                            <span
                                key={kw}
                                className="bg-red-50 text-red-600 border border-red-200 rounded-full px-3 py-1 text-xs font-medium"
                            >
                                {kw}
                            </span>
                        ))}
                    </div>
                    <p className="text-xs text-slate-400 mt-2">
                        Add these keywords to your resume to improve ATS compatibility.
                    </p>
                </div>
            )}

            {keywordGaps.length === 0 && resumeSkills.length > 0 && (
                <p className="text-xs text-emerald-600">✓ No major keyword gaps detected — excellent keyword coverage!</p>
            )}

            {resumeSkills.length === 0 && atsScore === 0 && (
                <p className="text-xs text-red-500">
                    ⚠️ Resume text could not be extracted. Please re-upload a text-based PDF (not a scanned image).
                </p>
            )}
        </div>
    )
}
