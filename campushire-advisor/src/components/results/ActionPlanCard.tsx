import type { Action } from '@/types'
import { ActionItem } from './ActionItem'
import { SHAPBarChart } from '@/components/charts/SHAPBarChart'
import type { ShapContribution } from '@/types'

interface ActionPlanCardProps {
    actions: Action[]
    shapContributions: ShapContribution[]
}

export function ActionPlanCard({ actions, shapContributions }: ActionPlanCardProps) {
    return (
        <div className="flex flex-col gap-4">
            {/* ── SHAP Feature Impact Chart ── */}
            <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
                <div className="flex items-start justify-between mb-5">
                    <div>
                        <h2 className="text-base font-bold text-slate-800">
                            📊 What's Driving Your Score
                        </h2>
                        <p className="text-xs text-slate-500 mt-0.5">
                            Each factor below either boosts or hurts your placement probability.
                            Longer bar = stronger impact on your result.
                        </p>
                    </div>
                </div>
                <SHAPBarChart contributions={shapContributions} />
            </div>

            {/* ── Action Plan ── */}
            <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
                <div className="mb-4">
                    <h2 className="text-base font-bold text-slate-800">🎯 Your Personalised Action Plan</h2>
                    <p className="text-xs text-slate-500 mt-0.5">
                        Based on your specific profile — sorted by what will help the most. Fix these to improve your score.
                    </p>
                </div>
                <div className="flex flex-col gap-3">
                    {actions.map((action) => (
                        <ActionItem key={action.priority} action={action} />
                    ))}
                </div>
            </div>
        </div>
    )
}
