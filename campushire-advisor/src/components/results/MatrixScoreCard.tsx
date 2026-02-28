import type { MatrixBreakdown } from '@/types'
import { CategoryRow } from './CategoryRow'

const CATEGORY_LABELS: { key: keyof MatrixBreakdown; label: string }[] = [
    { key: 'academics', label: 'Academics (CGPA / Board %)' },
    { key: 'internship', label: 'Internship' },
    { key: 'projects', label: 'Projects' },
    { key: 'coding', label: 'Coding Profile' },
    { key: 'hackathons', label: 'Hackathons' },
    { key: 'certifications', label: 'Certifications' },
]

interface MatrixScoreCardProps {
    matrixScore: number
    matrixBreakdown: MatrixBreakdown
}

export function MatrixScoreCard({ matrixScore, matrixBreakdown }: MatrixScoreCardProps) {
    return (
        <div className="bg-white rounded-2xl border border-slate-100 p-6">
            <div className="flex justify-between items-baseline mb-5">
                <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide">
                    RBU Placement Matrix
                </h2>
                <span className="text-2xl font-bold text-slate-900">
                    {matrixScore.toFixed(1)}
                    <span className="text-sm font-normal text-slate-400">/100</span>
                </span>
            </div>

            <div className="flex flex-col gap-3">
                {CATEGORY_LABELS.map(({ key, label }) => (
                    <CategoryRow
                        key={key}
                        label={label}
                        earned={matrixBreakdown[key].score}
                        max={matrixBreakdown[key].maxScore}
                    />
                ))}
            </div>
        </div>
    )
}
