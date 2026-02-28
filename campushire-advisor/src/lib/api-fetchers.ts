// ===========================================================================
// API FETCHERS — All platform stat fetchers with proper endpoints & fallbacks
// ===========================================================================

// ─── LeetCode ────────────────────────────────────────────────────────────────
// Uses alfa-leetcode-api.onrender.com:
//   /{username}         → profile (ranking, reputation, etc.)
//   /{username}/solved  → easySolved, mediumSolved, hardSolved, solvedProblem
//   /{username}/calendar → totalActiveDays, submissionCalendar

export interface LeetCodeStats {
    totalSolved: number
    easySolved: number
    mediumSolved: number
    hardSolved: number
    activeDays: number
    ranking: number
    username: string
}

export async function fetchLeetCodeStats(username: string): Promise<LeetCodeStats | null> {
    if (!username?.trim()) return null
    const BASE = 'https://alfa-leetcode-api.onrender.com'

    try {
        // Fetch profile + solved + calendar in parallel
        const [profileRes, solvedRes, calendarRes] = await Promise.all([
            fetch(`${BASE}/${username}`, { signal: AbortSignal.timeout(15000) }).catch(() => null),
            fetch(`${BASE}/${username}/solved`, { signal: AbortSignal.timeout(15000) }).catch(() => null),
            fetch(`${BASE}/${username}/calendar`, { signal: AbortSignal.timeout(15000) }).catch(() => null),
        ])

        // Check if user exists by looking at profile
        if (!profileRes?.ok) return null
        const profileData = await profileRes.json().catch(() => null)
        if (!profileData || profileData.errors) return null  // invalid username

        let easySolved = 0, mediumSolved = 0, hardSolved = 0, totalSolved = 0
        let activeDays = 0
        const ranking: number = profileData.ranking || 0

        // Parse solved counts from /solved endpoint
        if (solvedRes?.ok) {
            const solvedData = await solvedRes.json().catch(() => null)
            if (solvedData && !solvedData.errors) {
                totalSolved = solvedData.solvedProblem || 0
                easySolved = solvedData.easySolved || 0
                mediumSolved = solvedData.mediumSolved || 0
                hardSolved = solvedData.hardSolved || 0
            }
        }

        // Parse active days from /calendar endpoint
        if (calendarRes?.ok) {
            const calData = await calendarRes.json().catch(() => null)
            if (calData && !calData.errors) {
                activeDays = calData.totalActiveDays || 0
                // Fallback: count keys in submissionCalendar object
                if (!activeDays && calData.submissionCalendar) {
                    const cal = typeof calData.submissionCalendar === 'string'
                        ? JSON.parse(calData.submissionCalendar)
                        : calData.submissionCalendar
                    activeDays = Object.keys(cal).length
                }
            }
        }

        return { totalSolved, easySolved, mediumSolved, hardSolved, activeDays, ranking, username }
    } catch {
        return null
    }
}

// ─── GitHub ──────────────────────────────────────────────────────────────────
export interface GithubStats {
    public_repos: number
    followers: number
    following: number
    totalStars: number
    username: string
    name: string | null
}

export async function fetchGithubStats(username: string): Promise<GithubStats | null> {
    if (!username?.trim()) return null
    try {
        const [userRes, reposRes] = await Promise.all([
            fetch(`https://api.github.com/users/${username}`, { signal: AbortSignal.timeout(10000) }),
            fetch(`https://api.github.com/users/${username}/repos?per_page=100&sort=updated`, { signal: AbortSignal.timeout(10000) }),
        ])

        if (!userRes.ok) return null
        const userData = await userRes.json()

        let totalStars = 0
        if (reposRes.ok) {
            const repos = await reposRes.json()
            if (Array.isArray(repos)) {
                totalStars = repos.reduce((s: number, r: { stargazers_count?: number }) => s + (r.stargazers_count || 0), 0)
            }
        }

        return {
            public_repos: userData.public_repos || 0,
            followers: userData.followers || 0,
            following: userData.following || 0,
            totalStars,
            username: userData.login,
            name: userData.name || null,
        }
    } catch {
        return null
    }
}

// ─── Codeforces (Official API — always works) ─────────────────────────────────
export interface CodeforcesStats {
    handle: string
    rating: number
    maxRating: number
    rank: string
    maxRank: string
    solvedCount: number
    contribution: number
}

export async function fetchCodeforcesStats(handle: string): Promise<CodeforcesStats | null> {
    if (!handle?.trim()) return null
    try {
        // Fetch user info + submission history in parallel
        const [userRes, statusRes] = await Promise.all([
            fetch(`https://codeforces.com/api/user.info?handles=${handle}`, { signal: AbortSignal.timeout(12000) }),
            fetch(`https://codeforces.com/api/user.status?handle=${handle}&from=1&count=10000`, { signal: AbortSignal.timeout(15000) }).catch(() => null),
        ])

        if (!userRes.ok) return null
        const userData = await userRes.json()
        if (userData.status !== 'OK' || !userData.result?.[0]) return null

        const user = userData.result[0]

        // Count unique accepted problems
        let solvedCount = 0
        if (statusRes?.ok) {
            const statusData = await statusRes.json().catch(() => null)
            if (statusData?.status === 'OK') {
                const solved = new Set<string>()
                for (const sub of statusData.result) {
                    if (sub.verdict === 'OK' && sub.problem) {
                        solved.add(`${sub.problem.contestId}-${sub.problem.index}`)
                    }
                }
                solvedCount = solved.size
            }
        }

        return {
            handle: user.handle,
            rating: user.rating || 0,
            maxRating: user.maxRating || 0,
            rank: user.rank || 'unrated',
            maxRank: user.maxRank || 'unrated',
            solvedCount,
            contribution: user.contribution || 0,
        }
    } catch {
        return null
    }
}

// ─── CodeChef (best-effort — free APIs often go down) ────────────────────────
// NOTE: Most free CodeChef APIs have been taken down or paywalled.
// We try multiple known endpoints; if all fail it gracefully degrades.
export interface CodeChefStats {
    username: string
    currentRating: number
    stars: string
    fullySolved: number
    globalRank: number
    skipped?: boolean
    reason?: string
}

export async function fetchCodeChefStats(username: string): Promise<CodeChefStats> {
    const fallback: CodeChefStats = { username, currentRating: 0, stars: '0★', fullySolved: 0, globalRank: 0, skipped: true, reason: 'API unavailable' }
    if (!username?.trim()) return { ...fallback, reason: 'No username provided' }

    const apis = [
        `https://codechef-api.vercel.app/handle/${username}`,
        `https://codechef-api-two.vercel.app/${username}`,
    ]

    for (const url of apis) {
        try {
            const res = await fetch(url, {
                signal: AbortSignal.timeout(6000),
                headers: { 'User-Agent': 'Mozilla/5.0' },
            })
            if (!res.ok) continue
            const data = await res.json()
            if (data.success === false || data.status === 'error' || data.message) continue

            return {
                username,
                currentRating: data.currentRating || data.rating || 0,
                stars: data.stars || '0★',
                fullySolved: data.fully_solved || data.problemsSolved || 0,
                globalRank: data.globalRank || data.global_rank || 0,
            }
        } catch {
            continue
        }
    }

    return fallback
}
