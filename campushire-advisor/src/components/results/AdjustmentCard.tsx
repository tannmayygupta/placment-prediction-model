// src/components/results/AdjustmentCard.tsx

interface AdjustmentBreakdown {
    internship?: number
    lor?: number
    hackathon?: number
}

interface Props {
    baseProbability: number
    finalProbability: number
    adjustmentBreakdown: AdjustmentBreakdown
}

const LABELS: Record<string, string> = {
    internship: 'Internship experience',
    lor:        'Letters of recommendation',
    hackathon:  'Hackathon results',
}

export function AdjustmentCard({ baseProbability, finalProbability, adjustmentBreakdown }: Props) {
    // Don't render the card at all if there was no boost
    if (!adjustmentBreakdown || Object.keys(adjustmentBreakdown).length === 0) return null

    const totalBoost = (finalProbability - baseProbability).toFixed(1)

    // Convert each category's log-odds delta to an approximate % boost for display
    // We do this by computing what the probability would be with ONLY that delta applied
    const logOddsBase = Math.log(baseProbability / (100 - baseProbability))

    function deltaToBoostPct(deltaLogOdds: number): string {
        const pWithDelta = (1 / (1 + Math.exp(-(logOddsBase + deltaLogOdds)))) * 100
        return (pWithDelta - baseProbability).toFixed(1)
    }

    return (
        <div className="bg-white rounded-2xl p-6 border border-slate-100">
            <h2 className="text-base font-semibold text-slate-800 mb-1">
                Profile boost factors
            </h2>
            <p className="text-sm text-slate-400 mb-4">
                Extra signals that boosted your score beyond the base model prediction
            </p>

            {/* Base → Final row */}
            <div className="flex items-center gap-4 mb-5 p-4 bg-indigo-50 rounded-xl border border-indigo-100">
                <div className="text-center">
                    <div className="text-2xl font-semibold text-slate-500">{baseProbability}%</div>
                    <div className="text-xs text-slate-400 mt-0.5">Base score</div>
                </div>
                <div className="text-slate-300 text-xl flex-1 text-center">→</div>
                <div className="text-center">
                    <div className="text-2xl font-semibold text-indigo-600">{finalProbability}%</div>
                    <div className="text-xs text-slate-400 mt-0.5">Final score</div>
                </div>
                <div className="ml-auto">
                    <span className="text-sm font-semibold text-emerald-600 bg-emerald-50 border border-emerald-200 rounded-full px-3 py-1">
                        +{totalBoost}% total boost
                    </span>
                </div>
            </div>

            {/* Per-category rows */}
            <div className="space-y-2">
                {Object.entries(adjustmentBreakdown).map(([key, deltaLogOdds]) => (
                    <div
                        key={key}
                        className="flex items-center justify-between py-2 border-b border-slate-50 last:border-0"
                    >
                        <span className="text-sm text-slate-600">{LABELS[key] ?? key}</span>
                        <span className="text-sm font-semibold text-emerald-600">
                            +{deltaToBoostPct(deltaLogOdds)}%
                        </span>
                    </div>
                ))}
            </div>
        </div>
    )
}