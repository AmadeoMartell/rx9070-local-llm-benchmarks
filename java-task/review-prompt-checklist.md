You are reviewing LLM-agent-generated Java projects against a fixed fact checklist. READ-ONLY: do not build, do
not run gradle/docker, do not modify files. Ignore build/, .gradle/, bin/.

Read first, in this order:
1. RUBRIC.md — the checklist, the verdict rules and the output format.
2. SPEC.md — the phase-1 task (all projects).
3. SPEC-2.md — the phase-2 task (only projects marked "phase 2" below).
4. The FACTS file of each project: the harness's independent gradle verdicts and every test case that ran.
   Use it for the D and T items; a test passes only if FACTS lists it as passed.

Projects (anonymised; score each one on its own, the same way):
{{PROJECTS}}
<!-- one line per project: "<name>: <path>  FACTS: <path to facts .md>  scope: phase 1 | phase 1 + phase 2" -->

Rules that matter most:
- Every Y or P cites `path:line` (or a test name from FACTS). No evidence -> N.
- Judge the code, not NOTES.md or comments.
- Score every item listed for the project's scope; do not skip items and do not add your own.
- Section P (agent behaviour) comes from the FACTS "Agent behaviour" block; section O is your own opinion on
  architecture and code and never changes an item verdict.
Return the RUBRIC.md output format for each project and nothing else.
