from app.schemas.profile import ProfileSubmissionRequest, MatrixBreakdown, MatrixCategoryBreakdown

class MatrixScorer:
    """
    Calculates deterministic points out of 100 based on the RBU CDPC placement metric schema.
    Updated to use real platform data (LeetCode per-difficulty, Codeforces, CodeChef, GitHub stars).
    """

    @staticmethod
    def calculate_score(data: ProfileSubmissionRequest) -> tuple[float, MatrixBreakdown]:
        code = data.coding
        exp = data.experience

        # 1. Academics (Max 20 points)
        cgpa_normalized = data.academic.cgpa * (10 / data.academic.cgpaScale)

        academics_pts = 0.0
        if cgpa_normalized >= 9.0:
            academics_pts = 20.0
        elif cgpa_normalized >= 8.5:
            academics_pts = 17.0
        elif cgpa_normalized >= 8.0:
            academics_pts = 14.0
        elif cgpa_normalized >= 7.5:
            academics_pts = 11.0
        elif cgpa_normalized >= 7.0:
            academics_pts = 8.0
        elif cgpa_normalized >= 6.0:
            academics_pts = 4.0

        # Deduct 5 points per active backlog
        academics_pts = max(0.0, academics_pts - (data.academic.backlogs * 5))

        # 2. Internships (Max 20 points)
        internship_pts = 0.0
        if exp.internshipCount > 0:
            if exp.internshipType == 'international':
                internship_pts = 20.0
            elif exp.internshipType == 'it_company':
                internship_pts = 15.0 if exp.internshipStipendAbove10k else 10.0
            elif exp.internshipType == 'eduskills':
                internship_pts = 5.0

        # 3. Projects (Max 15 points)
        projects_pts = min(15.0, (exp.projectsIndustry * 10) + (exp.projectsDomain * 5))

        # 4. Coding Profile (Max 15 points) — uses real platform data
        lc_total = code.lcTotalSolved or code.lcSubmissions or 0
        lc_hard = code.lcHardSolved or 0
        lc_medium = code.lcMediumSolved or 0
        lc_active = code.lcActiveDays or 0

        # LeetCode subscore: up to 7 pts
        # - 2 pts per 100 solved (max 6), plus 1 pt bonus for active days >100
        lc_pts = min(6.0, (lc_total / 100) * 2.0)
        lc_pts += min(1.0, lc_hard / 30.0)   # bonus for hard problems
        lc_pts += min(0.5, lc_active / 200.0) # bonus for consistency
        lc_pts = min(7.0, lc_pts)

        # GitHub subscore: up to 3 pts
        gh_repos = code.githubRepos or (code.githubContributions // 10) or 0
        gh_stars = code.githubStars or 0
        gh_followers = code.githubFollowers or code.githubCollaborations or 0
        gh_pts = min(3.0, (gh_repos / 10.0) + (gh_stars / 50.0) + (gh_followers / 30.0))

        # Codeforces subscore: up to 3 pts
        cf_pts = 0.0
        if code.cfRating >= 2400:
            cf_pts = 3.0
        elif code.cfRating >= 1900:
            cf_pts = 2.5
        elif code.cfRating >= 1600:
            cf_pts = 2.0
        elif code.cfRating >= 1400:
            cf_pts = 1.5
        elif code.cfRating >= 1200:
            cf_pts = 1.0
        elif code.cfRating > 0:
            cf_pts = 0.5

        # CodeChef subscore: up to 2 pts
        cc_pts = 0.0
        cc_stars = code.ccStars or "0★"
        star_count = int(cc_stars[0]) if cc_stars and cc_stars[0].isdigit() else 0
        if code.ccRating >= 2000 or star_count >= 5:
            cc_pts = 2.0
        elif code.ccRating >= 1600 or star_count >= 4:
            cc_pts = 1.5
        elif code.ccRating >= 1400 or star_count >= 3:
            cc_pts = 1.0
        elif code.ccRating > 0 or star_count >= 1:
            cc_pts = 0.5

        coding_pts = min(15.0, lc_pts + gh_pts + cf_pts + cc_pts)

        # 5. Hackathons (Max 15 points)
        hackathon_pts = min(15.0,
            (exp.hackathonFirst * 10) +
            (exp.hackathonSecond * 8) +
            (exp.hackathonThird * 5) +
            (exp.hackathonParticipation * 2)
        )

        # 6. Certifications (Max 15 points)
        cert_pts = min(15.0,
            (exp.certsGlobal * 10) +
            (min(2, exp.certsNptel) * 5) +
            (min(2, exp.certsRbu) * 2)
        )

        # Total Matrix Score
        total_score = sum([academics_pts, internship_pts, projects_pts, coding_pts, hackathon_pts, cert_pts])

        breakdown = MatrixBreakdown(
            academics=MatrixCategoryBreakdown(score=round(academics_pts, 1), maxScore=20.0),
            internship=MatrixCategoryBreakdown(score=round(internship_pts, 1), maxScore=20.0),
            projects=MatrixCategoryBreakdown(score=round(projects_pts, 1), maxScore=15.0),
            coding=MatrixCategoryBreakdown(score=round(coding_pts, 1), maxScore=15.0),
            hackathons=MatrixCategoryBreakdown(score=round(hackathon_pts, 1), maxScore=15.0),
            certifications=MatrixCategoryBreakdown(score=round(cert_pts, 1), maxScore=15.0)
        )

        return (round(total_score, 1), breakdown)
