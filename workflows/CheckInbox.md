# CheckInbox Workflow

Purpose:
- Scan candidate inboxes for updates tied to active applications.

Keyword filters:
- "Interview"
- "Application Received"
- "Schedule"

Execution contract:
1. Read `status_tracker.json` and build candidate/company keyword pairs.
2. Query connected mail provider via MCP (Yahoo/Gmail/IMAP bridge) for matching unread and recent messages.
3. Classify updates:
   - `interview_request`
   - `application_received`
   - `schedule_request`
   - `other`
4. Update corresponding application entries in `status_tracker.json`.
5. Print a terminal summary with candidate, company, role, and next action.

Failure handling:
- If MCP/mail integration is unavailable, return a non-zero exit and do not mutate `status_tracker.json`.
