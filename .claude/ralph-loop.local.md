---
active: true
mode: prd
prd_path: "/Users/CorcosS/code/home.treasury.gov/plans/security-hardening-ssm.prd.json"
progress_path: "/Users/CorcosS/code/home.treasury.gov/plans/security-hardening-ssm-progress.txt"
iteration: 1
max_iterations: 26
completion_promise: "PRD_COMPLETE"
started_at: "2026-01-13T19:57:32Z"
supervised: false
supervisor_instructions: ""
supervisor_threshold: 0.8
---

You are executing a PRD-based sprint.

## PRD File
@/Users/CorcosS/code/home.treasury.gov/plans/security-hardening-ssm.prd.json

## Progress Log
@/Users/CorcosS/code/home.treasury.gov/plans/security-hardening-ssm-progress.txt

## Instructions

1. **Find highest-priority incomplete story**
   - Read userStories array in the PRD
   - Find a story where passes=false
   - Choose by priority: high > medium > low

2. **Implement ONLY that one story**
   - Keep changes small and focused
   - One feature per iteration prevents context bloat

3. **Run feedback loops**
   - validate: `cd terraform && terraform validate`
   - plan: `cd terraform && terraform plan -out=tfplan`
   - test: `cd deploy && ./validate-config.sh`
   - All must pass before marking story complete
   - Fix any failures before proceeding

4. **Verify the story**
   - Follow the verification steps in the story
   - Actually test - don't assume it works
   - Use browser automation if UI verification needed

5. **Update PRD**
   - Edit the PRD file to set passes=true for completed story

6. **APPEND to progress file**
   Add a section like:
   ---
   ## Iteration N - {Story Title}
   - Completed: {what was done}
   - Learnings: {anything notable for future iterations}
   - Next: {suggested next story by priority}
   ---

7. **Git commit**
   - Stage: PRD file, progress file, and code changes
   - Message: 'feat: {story-title}'

## CRITICAL RULES

- ONLY work on ONE user story per iteration
- ALWAYS run feedback loops before marking complete
- APPEND to progress file (don't overwrite)
- Commit after each story completion

## Exit Condition

When ALL userStories have passes=true, output:
<promise>PRD_COMPLETE</promise>

Do NOT output this until EVERY story passes.
