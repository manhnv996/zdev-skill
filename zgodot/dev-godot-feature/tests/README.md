# Behavioral Evaluation Scenarios

These scenarios capture RED baseline behavior before `dev-godot-feature` exists.
The recorded evaluation base is `86028078717287b80e32f7ec7e3e0eccaf48243e`.

For every entry in `scenarios.json`:

1. Create a clean, detached, disposable worktree from the recorded base commit.
2. In that worktree, make a disposable seed commit that removes exactly these
   answer-bearing paths, then verify that `.agents/skills/dev-godot-feature` is
   absent:
   - `docs/design/development/dev-godot-skills-design.md`
   - `docs/design/development/plans/01-feature-runtime-foundation-implementation-plan.md`
   - `docs/design/development/plans/02-dev-godot-config-implementation-plan.md`
   - `docs/design/development/plans/03-dev-godot-mock-implementation-plan.md`
   - `docs/design/development/plans/04-dev-godot-feature-implementation-plan.md`
3. Dispatch one fresh evaluator with `fork_turns: "none"` and an explicit model.
   Give it only the scenario's `prompt`, never the `must` list. Tell it to inspect
   the real codebase, choose an architecture, implement and commit concrete
   evidence, and avoid Git history, the main checkout, and other worktrees.
4. Record the evaluator identity, explicit model and reasoning level, evaluation
   base, seed and head commits, clean/dirty worktree status, verification result,
   cleanup result, and its exact rationale. Inspect its committed artifacts before
   scoring.
5. Score each `must` item independently as pass or fail. The scenario passes only
   when every item passes. Quote actual evaluator language or a concrete committed
   code decision; never substitute the prompt for evidence.
6. Commit intentional evaluator changes before cleanup. Remove only clean
   worktrees with normal `git worktree remove`; preserve and report any cleanup
   blocker instead of forcing removal.

Run no more than two evaluators concurrently. Baseline agents must not see the
new skill, the withheld architecture documents, the hidden `must` lists, Git
history containing those documents, the main checkout, or another worktree.
