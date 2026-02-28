import { useParams, useNavigate } from 'react-router-dom'
import { PageLayout } from '@/components/layout/PageLayout'
import { ProbabilityCard } from '@/components/results/ProbabilityCard'
import { MatrixScoreCard } from '@/components/results/MatrixScoreCard'
import { ATSScoreCard } from '@/components/results/ATSScoreCard'
import { ActionPlanCard } from '@/components/results/ActionPlanCard'
import { Button } from '@/components/ui/Button'
import { ResultsSkeleton } from '@/components/ui/SkeletonCard'
import { useAnalysisResult } from '@/hooks/useAnalysis'

export default function Results() {
    const { id } = useParams<{ id: string }>()
    const navigate = useNavigate()
    const { data, isLoading, isError } = useAnalysisResult(id ?? '')

    if (isLoading) {
        return (
            <PageLayout>
                <ResultsSkeleton />
            </PageLayout>
        )
    }

    if (isError || !data) {
        return (
            <PageLayout>
                <div className="flex flex-col items-center justify-center py-32 gap-4 text-center">
                    <span className="text-4xl">😕</span>
                    <h1 className="text-xl font-semibold text-slate-800">Result not found</h1>
                    <p className="text-sm text-slate-500">We couldn't find this analysis. It may have expired.</p>
                    <Button onClick={() => navigate('/profile')}>Start Over</Button>
                </div>
            </PageLayout>
        )
    }

    const lowConfidence = data.confidenceBand[1] - data.confidenceBand[0] > 20

    return (
        <PageLayout>
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
                <div>
                    <h1 className="text-2xl font-bold text-slate-900">Your Placement Analysis</h1>
                    <p className="text-sm text-slate-500 mt-1">
                        Processed in {(data.processingMs / 1000).toFixed(1)}s
                    </p>
                </div>
                <div className="flex gap-3">
                    <Button variant="outline" onClick={() => navigate(`/whatif/${data.submissionId}`)}>
                        Run What-If Simulation →
                    </Button>
                    <Button variant="ghost" onClick={() => navigate('/profile')}>
                        Start Over
                    </Button>
                </div>
            </div>

            {/* Low-confidence banner */}
            {lowConfidence && (
                <div className="mb-6 bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 text-sm text-amber-700">
                    ⚠️ This profile is unusual — treat this estimate as approximate. The confidence range is wide.
                </div>
            )}

            {/* Results grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Left column */}
                <div className="flex flex-col gap-6">
                    <ProbabilityCard
                        probability={data.probability}
                        confidenceBand={data.confidenceBand}
                    />
                    <MatrixScoreCard
                        matrixScore={data.matrixScore}
                        matrixBreakdown={data.matrixBreakdown}
                    />
                </div>

                {/* Right column */}
                <div className="flex flex-col gap-6">
                    <ATSScoreCard atsScore={data.atsScore} keywordGaps={data.keywordGaps} resumeSkills={data.resumeSkills} />
                    <ActionPlanCard
                        actions={data.actions}
                        shapContributions={data.shapContributions}
                    />
                </div>
            </div>
        </PageLayout>
    )
}
