# Skills

## JobScanner
- Uses Antigravity Browser Agent for role discovery.
- Sources: Indeed, LinkedIn, MGM Careers, Caesars Careers, Wynn Careers.
- Outputs structured job match artifacts with role, company, link, and compliance notes.

## ResumeCustomizer
- Reads candidate resumes from `/resumes`.
- Produces tailored resume variants aligned to each job description.
- Highlights required keywords and role-specific experience.

## GmailManager
- Uses MCP Gmail integration to draft and send follow-up messages.
- Supports inbox scanning for interview and scheduling keywords.
- Updates application state in `status_tracker.json`.

