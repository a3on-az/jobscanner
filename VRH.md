# Project Mission: Vegas Rapid Hire Automation

### #jobscanner

I need to automate the job application lifecycle for Richard Herrera and CHristine Gonzales.
We are targeting Security and Housekeeping roles in Las Vegas.

### Setup:

File: /.agent/rules/agent.md

You are the "Vegas Jobs Lead Architect." Your goal is to manage a high-speed recruitment pipeline for security and housekeeping roles. You must prioritize PILB compliance for security and rapid response times for all roles. Maintain a status_tracker.json to monitor every application's progress across multiple candidates.

File: /.agent/skills/SKILLS.md

JobScanner: Can use the Antigravity Browser Agent to search Indeed, LinkedIn, and MGM/Caesars career portals.

ResumeCustomizer: Can read PDF resumes from /resumes and edit them in the Editor to match specific Job Descriptions.

GmailManager: Can use MCP (Model Context Protocol) to draft and send follow-up emails via the user's Gmail.

### Phase 1: Infrastructure Setup (The Harness)

1. Initialize a local database (status_tracker.json) to track: Candidate Name, Target Role, Company, App Link, Date Submitted, and Follow-up Status.
2. Verify all resumes in the /resumes folder are readable. If any are missing key info (phone/email), flag them immediately.

### Phase 2: Autonomous Job Hunting (The Scraper)

1. Use the Browser Agent to identify 10 active openings for "Security Guard" (focus on PILB-required roles) and "Housekeeping" at major Strip properties (MGM, Caesars, Wynn).
2. For each role, parse the Job Description (JD).

### Phase 3: Tailored Application (The Submission)

1. For every opening found, use the Editor to create a "Tailored Resume" version that highlights specific keywords from the JD.
2. If the site allows for direct submission or email-based applying, draft the application.
3. Note: If a site requires a manual login, stop, generate an "Artifact" with the link and the tailored resume, and ask me to complete the final click.

### Phase 4: Communication Loop

1. Set up a /workflows command called "CheckInbox" that scans my Gmail for any keywords: "Interview", "Application Received", or "Schedule".
2. If an interview request is found, update status_tracker.json and notify me via the Terminal.

Go. Start with Phase 1 and 2, then present an Artifact of the first 5 job matches for my approval.