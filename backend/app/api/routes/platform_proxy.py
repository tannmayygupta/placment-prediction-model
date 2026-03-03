import httpx
import json
import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter

router = APIRouter()


def count_active_days(cal):
    try:
        if isinstance(cal, str):
            cal = json.loads(cal)
        cutoff = datetime.now(timezone.utc).timestamp() - 365 * 24 * 3600
        days = set()
        for ts, count in cal.items():
            if float(ts) >= cutoff and count > 0:
                d = datetime.fromtimestamp(float(ts), tz=timezone.utc)
                days.add(f"{d.year}-{d.month}-{d.day}")
        return len(days)
    except:
        return 0


@router.get("/leetcode-active-days/{username}")
async def get_leetcode_active_days(username: str):

    # ── Strategy 1: faisalshohag API (confirmed working, has submissionCalendar) ──
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.get(
                f"https://leetcode-api-faisalshohag.vercel.app/{username}",
                headers={"Accept": "application/json"}
            )
            if r.status_code == 200:
                data = r.json()
                if not data.get("errors"):
                    # submissionCalendar is a dict of {timestamp: count}
                    calendar = data.get("submissionCalendar")
                    if calendar:
                        active = count_active_days(calendar)
                        if active > 0:
                            return {"activeDays": active, "source": "faisalshohag"}
    except:
        pass

    # ── Strategy 2: alfa-leetcode-api ──────────────────────────────────────
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.get(
                f"https://alfa-leetcode-api.onrender.com/userProfile/{username}",
                headers={"Accept": "application/json"}
            )
            if r.status_code == 200:
                data = r.json()
                calendar = data.get("submissionCalendar") or data.get("submission_calendar")
                if calendar:
                    active = count_active_days(calendar)
                    if active > 0:
                        return {"activeDays": active, "source": "alfa-api"}
    except:
        pass

    # ── Strategy 3: leetcode-stats-api ─────────────────────────────────────
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.get(
                f"https://leetcode-stats-api.herokuapp.com/{username}",
                headers={"Accept": "application/json"}
            )
            if r.status_code == 200:
                data = r.json()
                if data.get("status") != "error":
                    active = data.get("totalActiveDays") or data.get("active_days") or 0
                    if active > 0:
                        return {"activeDays": active, "source": "leetcode-stats-api"}
    except:
        pass

    # ── Strategy 4: Direct LeetCode GraphQL (works locally) ────────────────
    try:
        query = "query userProfileCalendar($username: String!, $year: Int) { matchedUser(username: $username) { userCalendar(year: $year) { totalActiveDays submissionCalendar } } }"
        headers = {
            "Content-Type": "application/json",
            "Referer": "https://leetcode.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Origin": "https://leetcode.com",
        }
        yr = datetime.now().year

        async def fetch_year(client, year):
            try:
                r = await client.post(
                    "https://leetcode.com/graphql",
                    headers=headers,
                    json={"operationName": "userProfileCalendar", "query": query,
                          "variables": {"username": username, "year": year}}
                )
                if r.status_code == 200:
                    return r.json().get("data", {}).get("matchedUser", {}).get("userCalendar")
            except:
                pass
            return None

        async with httpx.AsyncClient(timeout=20.0) as client:
            cur, prev = await asyncio.gather(
                fetch_year(client, yr),
                fetch_year(client, yr - 1)
            )

        if cur and cur.get("totalActiveDays", 0) > 0:
            return {"activeDays": cur["totalActiveDays"], "source": "leetcode-graphql"}

        merged = {}
        for c in [cur, prev]:
            if c and c.get("submissionCalendar"):
                cal = c["submissionCalendar"]
                merged.update(json.loads(cal) if isinstance(cal, str) else cal)
        if merged:
            return {"activeDays": count_active_days(merged), "source": "leetcode-graphql-calendar"}
    except:
        pass

    return {"activeDays": 0, "source": "all-failed"}
