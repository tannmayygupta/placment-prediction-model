import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { PageLayout } from '@/components/layout/PageLayout'
import { ProgressBar } from '@/components/wizard/ProgressBar'
import { StepIndicator } from '@/components/wizard/StepIndicator'
import { FileDropzone } from '@/components/wizard/FileDropzone'
import { FormInput } from '@/components/ui/FormInput'
import { Button } from '@/components/ui/Button'
import { LoadingOverlay } from '@/components/ui/LoadingOverlay'
import { profileSchema, type ProfileFormValues } from '@/lib/validators'
import { useSubmitAnalysis } from '@/hooks/useAnalysis'
import type { WizardFormData } from '@/types'
import type { InternshipType } from '@/types'
import {
    fetchLeetCodeStats,
    fetchGithubStats,
    fetchCodeforcesStats,
    fetchCodeChefStats,
    type CodeChefStats,
} from '@/lib/api-fetchers'

// ── FIX 1: Type declarations must be OUTSIDE the component function ──────────
type LOREntry = {
    source_type: 'industry' | 'academic_strong' | 'academic_standard'
    institution: string
}

type CertEntry = {
    event_name: string
    prize_level: 'first' | 'second' | 'third' | 'participation'
}
// ────────────────────────────────────────────────────────────────────────────

const STEP_LABELS = ['Profile & Usernames', 'Experience & Extras', 'Resume']
const BRANCHES = ['CSE', 'IT', 'ECE', 'ENTC', 'Mechanical', 'Civil', 'Chemical', 'Other']

function SectionHeader({ children }: { children: React.ReactNode }) {
    return <h2 className="text-lg font-semibold text-slate-800 mb-4">{children}</h2>
}

interface PlatformCard {
    name: string
    icon: string
    color: string
    items: [string, string | number][]
    status: 'ok' | 'failed' | 'skipped'
}

function PlatformCards({ cards }: { cards: PlatformCard[] }) {
    return (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {cards.map((card) => (
                <div
                    key={card.name}
                    className={`rounded-xl border p-4 ${card.status === 'failed' ? 'bg-red-50 border-red-200' :
                        card.status === 'skipped' ? 'bg-slate-50 border-slate-200 opacity-60' :
                            card.color
                        }`}
                >
                    <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                            <span className="text-xl">{card.icon}</span>
                            <span className="font-semibold text-sm text-slate-700">{card.name}</span>
                        </div>
                        {card.status === 'ok' && <span className="text-xs bg-emerald-100 text-emerald-700 rounded-full px-2 py-0.5">✓ Fetched</span>}
                        {card.status === 'failed' && <span className="text-xs bg-red-100 text-red-700 rounded-full px-2 py-0.5">✗ Failed</span>}
                        {card.status === 'skipped' && <span className="text-xs bg-slate-200 text-slate-500 rounded-full px-2 py-0.5">Skipped</span>}
                    </div>
                    {card.status === 'ok' && (
                        <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
                            {card.items.map(([label, val]) => (
                                <div key={label}>
                                    <div className="text-xs text-slate-400">{label}</div>
                                    <div className="text-sm font-bold text-slate-800">{val}</div>
                                </div>
                            ))}
                        </div>
                    )}
                    {card.status === 'skipped' && (
                        <p className="text-xs text-slate-400">API unavailable — won't affect prediction</p>
                    )}
                </div>
            ))}
        </div>
    )
}

export default function ProfileWizard() {
    const [step, setStep] = useState(1)
    const [resumeFile, setResumeFile] = useState<File | null>(null)
    const [formData, setFormData] = useState<Partial<WizardFormData>>({})
    const [isVerifying, setIsVerifying] = useState(false)
    const [verifyStatus, setVerifyStatus] = useState('')
    const [verifyError, setVerifyError] = useState('')
    const [platformCards, setPlatformCards] = useState<PlatformCard[]>([])

    // ── Step 2 state ──────────────────────────────────────────────────────────
    
    const [internshipType, setInternshipType] = useState<InternshipType>('none')
    const [internshipCount, setInternshipCount] = useState<number>(0)
    const [stipendAbove10k, setStipendAbove10k] = useState<boolean>(false)
    const [projectsIndustry, setProjectsIndustry] = useState<number>(0)
    const [projectsDomain, setProjectsDomain] = useState<number>(0)
    const [certsGlobal, setCertsGlobal] = useState<number>(0)
    const [certsNptel, setCertsNptel] = useState<number>(0)
    const [certsRbu, setCertsRbu] = useState<number>(0)
    const [hackathonFirst, setHackathonFirst] = useState<number>(0)
    const [hackathonSecond, setHackathonSecond] = useState<number>(0)
    const [hackathonThird, setHackathonThird] = useState<number>(0)
    const [hackathonParticipation, setHackathonParticipation] = useState<number>(0)
    // ── FIX 2: useState uses the module-level types, NOT inline type declarations
    const [lors, setLors] = useState<LOREntry[]>([])
    const [hackathonCerts, setHackathonCerts] = useState<CertEntry[]>([])
    // ─────────────────────────────────────────────────────────────────────────

    const submitAnalysis = useSubmitAnalysis()

    const form = useForm<ProfileFormValues>({
        resolver: zodResolver(profileSchema),
        defaultValues: { cgpaScale: 10, year: 3, backlogs: 0, codechefUsername: '' }
    })

    async function handleVerifyAndProceed(data: ProfileFormValues) {
        setIsVerifying(true)
        setVerifyError('')
        setPlatformCards([])

        setVerifyStatus('🔍 Fetching LeetCode stats...')
        const lcData = await fetchLeetCodeStats(data.leetcodeUsername)

        if (!lcData) {
            setVerifyError(`❌ Could not fetch LeetCode profile for "${data.leetcodeUsername}". Check your username at leetcode.com and try again.`)
            setIsVerifying(false)
            setVerifyStatus('')
            return
        }

        setVerifyStatus('🔍 Fetching GitHub stats...')
        const ghData = await fetchGithubStats(data.githubUsername)

        if (!ghData) {
            setVerifyError(`❌ Could not fetch GitHub profile for "${data.githubUsername}". Check your username at github.com and try again.`)
            setIsVerifying(false)
            setVerifyStatus('')
            return
        }

        setVerifyStatus('🔍 Fetching Codeforces stats...')
        const cfData = await fetchCodeforcesStats(data.codeforcesHandle)

        if (!cfData) {
            setVerifyError(`❌ Could not fetch Codeforces profile for "${data.codeforcesHandle}". Check your handle at codeforces.com and try again.`)
            setIsVerifying(false)
            setVerifyStatus('')
            return
        }

        setVerifyStatus('🔍 Fetching CodeChef stats (optional)...')
        const ccData: CodeChefStats = data.codechefUsername
            ? await fetchCodeChefStats(data.codechefUsername)
            : { username: '', currentRating: 0, stars: '0★', fullySolved: 0, globalRank: 0, skipped: true, reason: 'Not provided' }

        const cards: PlatformCard[] = [
            {
                name: 'LeetCode',
                icon: '🟨',
                color: 'bg-yellow-50 border-yellow-200',
                status: 'ok',
                items: [
                    ['Total Solved', lcData.totalSolved],
                    ['Easy / Med / Hard', `${lcData.easySolved}/${lcData.mediumSolved}/${lcData.hardSolved}`],
                    ['Active Days (yr)', lcData.activeDays],
                    ['Global Rank', lcData.ranking > 0 ? `#${lcData.ranking.toLocaleString()}` : 'N/A'],
                ],
            },
            {
                name: 'GitHub',
                icon: '🐙',
                color: 'bg-slate-50 border-slate-200',
                status: 'ok',
                items: [
                    ['Public Repos', ghData.public_repos],
                    ['Yearly Contributions', ghData.yearlyContributions || 0],
                    ['Activity (last 30d)', ghData.recentCommits || 0],
                    ['Total Stars', ghData.totalStars],
                    ['Followers', ghData.followers],
                ],
            },
            {
                name: 'Codeforces',
                icon: '🔵',
                color: 'bg-blue-50 border-blue-200',
                status: 'ok',
                items: [
                    ['Rating', cfData.rating || 'Unrated'],
                    ['Max Rating', cfData.maxRating || 'N/A'],
                    ['Rank', cfData.rank],
                    ['Problems Solved', cfData.solvedCount],
                ],
            },
            {
                name: 'CodeChef',
                icon: '👨‍🍳',
                color: 'bg-orange-50 border-orange-200',
                status: ccData.skipped ? 'skipped' : 'ok',
                items: ccData.skipped ? [] : [
                    ['Rating', ccData.currentRating],
                    ['Stars', ccData.stars],
                    ['Solved', ccData.fullySolved],
                    ['Global Rank', ccData.globalRank ? `#${ccData.globalRank}` : 'N/A'],
                ],
            },
        ]
        setPlatformCards(cards)

        // ── FIX 3: experience block removed from here — set in handleExperienceNext
        const mapped: Partial<WizardFormData> = {
            academic: {
                cgpa: data.cgpa,
                cgpaScale: data.cgpaScale,
                tenthPct: data.tenthPct,
                twelfthPct: data.twelfthPct,
                branch: data.branch,
                year: data.year,
                backlogs: data.backlogs,
            },
            coding: {
                lcTotalSolved: lcData.totalSolved,
                lcEasySolved: lcData.easySolved,
                lcMediumSolved: lcData.mediumSolved,
                lcHardSolved: lcData.hardSolved,
                lcActiveDays: lcData.activeDays,
                lcRanking: lcData.ranking,
                githubRepos: ghData.public_repos,
                githubFollowers: ghData.followers,
                githubStars: ghData.totalStars,
                githubYearlyContributions: ghData.yearlyContributions,
                githubRecentCommits: ghData.recentCommits,
                cfRating: cfData.rating,
                cfMaxRating: cfData.maxRating,
                cfRank: cfData.rank,
                cfSolved: cfData.solvedCount,
                ccRating: ccData.skipped ? 0 : (ccData.currentRating || 0),
                ccStars: ccData.skipped ? '0★' : (ccData.stars || '0★'),
                ccSolved: ccData.skipped ? 0 : (ccData.fullySolved || 0),
                ccGlobalRank: ccData.skipped ? 0 : (ccData.globalRank || 0),
                lcSubmissions: lcData.totalSolved,
                hrBadges: 0,
                hrMedHardSolved: lcData.mediumSolved + lcData.hardSolved,
                githubContributions: ghData.yearlyContributions,
                githubCollaborations: ghData.followers,
                githubMonthlyActive: ghData.yearlyContributions > 50 || lcData.activeDays > 30,
            },
        }

        setFormData(mapped)
        setIsVerifying(false)
        setVerifyStatus('')
        setStep(2)
    }

    function handleExperienceNext() {
        setFormData(prev => ({
            ...prev,
            experience: {
                internshipType,
                internshipCount,
                internshipStipendAbove10k: stipendAbove10k,
                projectsIndustry,
                projectsDomain:
                    projectsDomain > 0
                        ? projectsDomain
                        : (prev.coding?.githubRepos ?? 0) > 10
                            ? 3
                            : (prev.coding?.githubRepos ?? 0) > 5
                                ? 2
                                : 1,
                certsGlobal,
                certsNptel,
                certsRbu,
                hackathonFirst,
                hackathonSecond,
                hackathonThird,
                hackathonParticipation,
            },
            // ── FIX 4: lors and hackathonCerts removed — not part of WizardFormData.
            // handleFinalSubmit reads them directly from component state instead.
        }))
        setStep(3)
    }

    async function handleFinalSubmit() {
        if (!resumeFile) return

        // POST LOR entries — reads directly from component state (not formData)
        for (const lor of lors) {
            try {
                await fetch('/api/v1/extras/lors', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify(lor),
                })
            } catch {
                // non-fatal
            }
        }

        // POST hackathon cert entries
        for (const cert of hackathonCerts) {
            try {
                await fetch('/api/v1/extras/hackathon-certs', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify(cert),
                })
            } catch {
                // non-fatal
            }
        }

        submitAnalysis.mutate({ ...formData, resumeFile } as WizardFormData)
    }

    return (
        <PageLayout maxWidth="2xl">
            {(submitAnalysis.isPending || isVerifying) && (
                <LoadingOverlay message={verifyStatus || 'Analysing your profile with AI...'} />
            )}

            <div className="mb-8">
                <StepIndicator currentStep={step} totalSteps={3} stepName={STEP_LABELS[step - 1]} />
                <ProgressBar currentStep={step} totalSteps={3} stepLabels={STEP_LABELS} />
            </div>

            {/* ─── STEP 1: Academics + Usernames ─── */}
            {step === 1 && (
                <form onSubmit={form.handleSubmit(handleVerifyAndProceed)} className="flex flex-col gap-8">
                    {verifyError && (
                        <div className="p-4 bg-red-50 text-red-700 rounded-xl border border-red-200 text-sm font-medium">
                            {verifyError}
                        </div>
                    )}

                    {/* Academic Details */}
                    <div>
                        <SectionHeader>Academic Details</SectionHeader>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            <FormInput label="CGPA" type="number" step="0.01" placeholder="e.g. 7.8"
                                error={form.formState.errors.cgpa?.message}
                                {...form.register('cgpa', { valueAsNumber: true })} />
                            <div className="flex flex-col gap-1">
                                <label className="text-sm font-medium text-slate-700">CGPA Scale</label>
                                <select className="rounded-xl border border-slate-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                                    {...form.register('cgpaScale', { valueAsNumber: true })}>
                                    <option value={10}>10.0 scale</option>
                                    <option value={4}>4.0 scale</option>
                                </select>
                            </div>
                            <FormInput label="10th Board %" type="number" step="0.01" placeholder="e.g. 85.4"
                                error={form.formState.errors.tenthPct?.message}
                                {...form.register('tenthPct', { valueAsNumber: true })} />
                            <FormInput label="12th Board %" type="number" step="0.01" placeholder="e.g. 78.2"
                                error={form.formState.errors.twelfthPct?.message}
                                {...form.register('twelfthPct', { valueAsNumber: true })} />
                            <div className="flex flex-col gap-1">
                                <label className="text-sm font-medium text-slate-700">Branch</label>
                                <select className="rounded-xl border border-slate-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                                    {...form.register('branch')}>
                                    <option value="">Select branch</option>
                                    {BRANCHES.map((b) => <option key={b} value={b}>{b}</option>)}
                                </select>
                                {form.formState.errors.branch && (
                                    <p className="text-xs text-red-500">{form.formState.errors.branch.message}</p>
                                )}
                            </div>
                            <div className="flex flex-col gap-1">
                                <label className="text-sm font-medium text-slate-700">Year</label>
                                <select className="rounded-xl border border-slate-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                                    {...form.register('year', { valueAsNumber: true })}>
                                    {[1, 2, 3, 4].map((y) => <option key={y} value={y}>Year {y}</option>)}
                                </select>
                            </div>
                            <FormInput label="Active Backlogs" type="number" min={0} placeholder="e.g. 0"
                                error={form.formState.errors.backlogs?.message}
                                {...form.register('backlogs', { valueAsNumber: true })} />
                        </div>
                    </div>

                    {/* Coding Profiles */}
                    <div>
                        <SectionHeader>Coding Platform Usernames</SectionHeader>
                        <p className="text-sm text-slate-500 mb-1">
                            We fetch your <span className="font-semibold text-slate-700">real stats</span> directly from each platform API — problems solved per difficulty, active days, ratings, and more.
                        </p>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4">
                            <FormInput
                                label="LeetCode Username *"
                                placeholder="e.g. tanmayygupta"
                                error={form.formState.errors.leetcodeUsername?.message}
                                {...form.register('leetcodeUsername')}
                            />
                            <FormInput
                                label="GitHub Username *"
                                placeholder="e.g. octocat"
                                error={form.formState.errors.githubUsername?.message}
                                {...form.register('githubUsername')}
                            />
                            <FormInput
                                label="Codeforces Handle *"
                                placeholder="e.g. tourist"
                                error={form.formState.errors.codeforcesHandle?.message}
                                {...form.register('codeforcesHandle')}
                            />
                            <FormInput
                                label="CodeChef Username (optional)"
                                placeholder="e.g. coder_123"
                                error={form.formState.errors.codechefUsername?.message}
                                {...form.register('codechefUsername')}
                            />
                        </div>

                        <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
                            <div className="p-3 bg-indigo-50 border border-indigo-100 rounded-xl text-xs text-indigo-700">
                                <p className="font-semibold mb-1">📊 What we fetch:</p>
                                <ul className="space-y-0.5">
                                    <li>🟨 LeetCode: solved per difficulty, active days, ranking</li>
                                    <li>🐙 GitHub: repos, stars, followers</li>
                                    <li>🔵 Codeforces: rating, rank, problems solved</li>
                                    <li>👨‍🍳 CodeChef: rating, stars (if API is up)</li>
                                </ul>
                            </div>
                            <div className="p-3 bg-amber-50 border border-amber-100 rounded-xl text-xs text-amber-700">
                                <p className="font-semibold mb-1">⚠️ Note on CodeChef:</p>
                                <p>CodeChef does not have a stable free API. We try our best to fetch your data, but it may show as unavailable. Your Codeforces rating is the primary competitive programming signal.</p>
                            </div>
                        </div>
                    </div>

                    <div className="flex justify-end">
                        <Button type="submit">Verify & Fetch Stats →</Button>
                    </div>
                </form>
            )}

            {/* ─── STEP 2: Experience & Extras ─── */}
            {step === 2 && (
                <div className="flex flex-col gap-8">

                    {/* Internship */}
                    <div>
                        <SectionHeader>Internship Experience</SectionHeader>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            <div className="flex flex-col gap-1">
                                <label className="text-sm font-medium text-slate-700">Internship Type</label>
                                <select
                                    className="rounded-xl border border-slate-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                                    value={internshipType}
                                   onChange={e => setInternshipType(e.target.value as InternshipType)}
                                >
                                    <option value="none">No internship</option>
                                    <option value="international">International internship</option>
                                    <option value="it_company">IT company / Reputed institute</option>
                                    <option value="eduskills">EduSkills</option>
                                </select>
                            </div>

                            {internshipType !== 'none' && (
                                <div className="flex flex-col gap-1">
                                    <label className="text-sm font-medium text-slate-700">Number of Internships</label>
                                    <input
                                        type="number" min={0} max={10}
                                        className="rounded-xl border border-slate-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                                        value={internshipCount}
                                        onChange={e => setInternshipCount(Number(e.target.value))}
                                    />
                                </div>
                            )}

                            {internshipType !== 'none' && (
                                <div className="flex items-center gap-3 col-span-2 p-3 bg-slate-50 rounded-xl border border-slate-200">
                                    <input
                                        type="checkbox" id="stipend"
                                        className="w-4 h-4 accent-indigo-600"
                                        checked={stipendAbove10k}
                                        onChange={e => setStipendAbove10k(e.target.checked)}
                                    />
                                    <label htmlFor="stipend" className="text-sm text-slate-700">
                                        Total stipend received was ₹10,000 or more
                                    </label>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Projects */}
                    <div>
                        <SectionHeader>Projects</SectionHeader>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            <div className="flex flex-col gap-1">
                                <label className="text-sm font-medium text-slate-700">Industry / SIH / GOI projects</label>
                                <input type="number" min={0}
                                    className="rounded-xl border border-slate-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                                    value={projectsIndustry}
                                    onChange={e => setProjectsIndustry(Number(e.target.value))}
                                />
                            </div>
                            <div className="flex flex-col gap-1">
                                <label className="text-sm font-medium text-slate-700">Domain-specific projects</label>
                                <input type="number" min={0}
                                    className="rounded-xl border border-slate-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                                    value={projectsDomain}
                                    onChange={e => setProjectsDomain(Number(e.target.value))}
                                />
                            </div>
                        </div>
                    </div>

                    {/* Certifications */}
                    <div>
                        <SectionHeader>Certifications</SectionHeader>
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                            <div className="flex flex-col gap-1">
                                <label className="text-sm font-medium text-slate-700">Global certs (AWS / Azure / GCP…)</label>
                                <input type="number" min={0}
                                    className="rounded-xl border border-slate-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                                    value={certsGlobal}
                                    onChange={e => setCertsGlobal(Number(e.target.value))}
                                />
                            </div>
                            <div className="flex flex-col gap-1">
                                <label className="text-sm font-medium text-slate-700">NPTEL courses</label>
                                <input type="number" min={0} max={2}
                                    className="rounded-xl border border-slate-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                                    value={certsNptel}
                                    onChange={e => setCertsNptel(Number(e.target.value))}
                                />
                                <p className="text-xs text-slate-400">Max 2 counted</p>
                            </div>
                            <div className="flex flex-col gap-1">
                                <label className="text-sm font-medium text-slate-700">RBU online courses</label>
                                <input type="number" min={0} max={2}
                                    className="rounded-xl border border-slate-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                                    value={certsRbu}
                                    onChange={e => setCertsRbu(Number(e.target.value))}
                                />
                                <p className="text-xs text-slate-400">Max 2 counted</p>
                            </div>
                        </div>
                    </div>

                    {/* Hackathons */}
                    <div>
                        <SectionHeader>Hackathons & Competitions</SectionHeader>
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                            {(
                                [
                                    { label: '1st prize wins', value: hackathonFirst, set: setHackathonFirst },
                                    { label: '2nd prize wins', value: hackathonSecond, set: setHackathonSecond },
                                    { label: '3rd / consolation', value: hackathonThird, set: setHackathonThird },
                                    { label: 'Participations', value: hackathonParticipation, set: setHackathonParticipation },
                                ] as { label: string; value: number; set: (n: number) => void }[]
                            ).map(({ label, value, set }) => (
                                <div key={label} className="flex flex-col gap-1">
                                    <label className="text-sm font-medium text-slate-700">{label}</label>
                                    <input type="number" min={0}
                                        className="rounded-xl border border-slate-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                                        value={value}
                                        onChange={e => set(Number(e.target.value))}
                                    />
                                </div>
                            ))}
                        </div>

                        {/* Hackathon cert detail rows */}
                        <div className="mt-4">
                            <p className="text-sm text-slate-500 mb-2">
                                Optionally list your hackathon results for a more detailed score breakdown:
                            </p>
                            {hackathonCerts.map((cert, i) => (
                                <div key={i} className="grid grid-cols-2 gap-3 mb-2 p-3 bg-slate-50 rounded-xl border border-slate-100">
                                    <input
                                        className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
                                        placeholder="Event name e.g. SIH 2025"
                                        value={cert.event_name}
                                        onChange={e => {
                                            const updated = [...hackathonCerts]
                                            updated[i] = { ...updated[i], event_name: e.target.value }
                                            setHackathonCerts(updated)
                                        }}
                                    />
                                    <select
                                        className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
                                        value={cert.prize_level}
                                        onChange={e => {
                                            const updated = [...hackathonCerts]
                                            updated[i] = { ...updated[i], prize_level: e.target.value as CertEntry['prize_level'] }
                                            setHackathonCerts(updated)
                                        }}
                                    >
                                        <option value="first">1st prize</option>
                                        <option value="second">2nd prize</option>
                                        <option value="third">3rd / consolation</option>
                                        <option value="participation">Participation</option>
                                    </select>
                                    <button
                                        type="button"
                                        className="text-xs text-red-500 col-span-2 text-left"
                                        onClick={() => setHackathonCerts(hackathonCerts.filter((_, j) => j !== i))}
                                    >
                                        Remove
                                    </button>
                                </div>
                            ))}
                            <button
                                type="button"
                                className="text-sm text-indigo-600 font-medium hover:text-indigo-800"
                                onClick={() => setHackathonCerts([...hackathonCerts, { event_name: '', prize_level: 'participation' }])}
                            >
                                + Add a hackathon result
                            </button>
                        </div>
                    </div>

                    {/* LOR */}
                    <div>
                        <SectionHeader>Letters of Recommendation</SectionHeader>
                        <p className="text-sm text-slate-500 mb-3">Optional — adds a meaningful boost, especially from industry mentors.</p>
                        {lors.map((lor, i) => (
                            <div key={i} className="grid grid-cols-2 gap-3 mb-2 p-3 bg-slate-50 rounded-xl border border-slate-100">
                                <select
                                    className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
                                    value={lor.source_type}
                                    onChange={e => {
                                        const updated = [...lors]
                                        updated[i] = { ...updated[i], source_type: e.target.value as LOREntry['source_type'] }
                                        setLors(updated)
                                    }}
                                >
                                    <option value="industry">Industry mentor</option>
                                    <option value="academic_strong">Academic — strong dept.</option>
                                    <option value="academic_standard">Academic — standard</option>
                                </select>
                                <input
                                    className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
                                    placeholder="Institution (optional)"
                                    value={lor.institution}
                                    onChange={e => {
                                        const updated = [...lors]
                                        updated[i] = { ...updated[i], institution: e.target.value }
                                        setLors(updated)
                                    }}
                                />
                                <button
                                    type="button"
                                    className="text-xs text-red-500 col-span-2 text-left"
                                    onClick={() => setLors(lors.filter((_, j) => j !== i))}
                                >
                                    Remove
                                </button>
                            </div>
                        ))}
                        {lors.length < 3 && (
                            <button
                                type="button"
                                className="text-sm text-indigo-600 font-medium hover:text-indigo-800"
                                onClick={() => setLors([...lors, { source_type: 'academic_standard', institution: '' }])}
                            >
                                + Add a letter of recommendation
                            </button>
                        )}
                    </div>

                    {/* Navigation */}
                    <div className="flex justify-between">
                        <Button variant="outline" onClick={() => setStep(1)}>← Back</Button>
                        <Button onClick={handleExperienceNext}>Next — Upload Resume →</Button>
                    </div>
                </div>
            )}

            {/* ─── STEP 3: Platform Stats + Resume ─── */}
            {step === 3 && (
                <div className="flex flex-col gap-6">
                    {platformCards.length > 0 && (
                        <div>
                            <SectionHeader>✅ Live Platform Stats Fetched</SectionHeader>
                            <p className="text-sm text-slate-500 mb-3">
                                These real numbers power your AI analysis. Gemini will use all of this data to generate your personalised placement prediction.
                            </p>
                            <PlatformCards cards={platformCards} />
                        </div>
                    )}

                    <div>
                        <SectionHeader>Upload Your Resume (PDF)</SectionHeader>
                        <FileDropzone
                            file={resumeFile}
                            onFileChange={setResumeFile}
                            error={submitAnalysis.isError ? 'Submission failed. Please try again.' : undefined}
                        />
                        <div className="mt-3 p-4 bg-indigo-50 rounded-xl border border-indigo-100 text-sm">
                            <p className="font-semibold text-indigo-800 mb-1">🤖 What happens next:</p>
                            <ul className="text-indigo-700 text-xs space-y-1">
                                <li>• Your resume text is extracted and matched against 80+ ATS keywords across 9 categories</li>
                                <li>• Gemini AI reads your entire profile + resume to generate a personalised probability</li>
                                <li>• Recommendations are specific to YOUR actual numbers — not generic advice</li>
                            </ul>
                        </div>
                    </div>

                    <div className="flex justify-between">
                        <Button variant="outline" onClick={() => setStep(2)}>← Back</Button>
                        <Button
                            onClick={handleFinalSubmit}
                            disabled={!resumeFile || submitAnalysis.isPending}
                        >
                            {submitAnalysis.isPending ? 'Analysing with AI...' : 'Analyse My Profile 🚀'}
                        </Button>
                    </div>
                </div>
            )}
        </PageLayout>
    )
}
