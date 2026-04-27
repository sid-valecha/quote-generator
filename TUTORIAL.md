# Cross-agent code review with mngr

---

## The problem

Claude Code and Codex are both good, but they're not the same - they make different calls, catch different things, and sometimes one misses what the other wouldn't. The natural move is to run both. The problem is doing that manually is tedious: separate terminals, separate directories, manually diffing the results. Most people just pick one and move on, which means they're leaving a free second opinion on the table.

---

## What this tutorial shows

mngr lets you spawn multiple coding agents in parallel, each working in an isolated git worktree, and gives you the tools to pull their work back and compare it. Vet adds a structured second-opinion layer, reviewing each agent's diff for correctness and goal adherence using your existing Claude Code or Codex subscription. Both tools work with the agent CLIs you already have, no API keys required.

---

## The setup

The demo repo is a small FastAPI app called quote-generator. It serves random quotes from a 48k-entry JSON file at `GET /api/quote`. The feature we're adding: an optional `?category=` query parameter that filters by genre (the dataset has 32 categories: `life`, `funny`, `friendship`, and so on), returning HTTP 404 when no quotes match.

The same prompt goes to both agents:

```
You are working in the quote-generator repo. Read api/main.py and
engines/quote_engine.py before changing anything.

Task: Add category filtering to the quote API.

1. Update engines/quote_engine.py — add optional `category: str | None = None`
   param to generate_quote(). Filter quotes by Category field (case-insensitive).
   Raise ValueError("No quotes found for category: <category>") if no matches.

2. Update api/main.py — add optional `category` query param to GET /api/quote.
   Pass to generate_quote(). On ValueError, return HTTP 404 with detail
   "No quotes found for that category."

3. Add tests/test_category_filter.py using pytest and FastAPI TestClient:
   - No category → returns a quote
   - category=life → returns non-empty quote
   - category=nonexistent_xyz → HTTP 404
   Import app from api.main.
```

---

## Running both agents in parallel

```bash
mngr create claude-impl --message "$(cat prompt.txt)" --no-connect -- --dangerously-skip-permissions
mngr create codex-impl codex --message "$(cat prompt.txt)" --no-connect -- --full-auto
```

mngr creates a separate git worktree for each agent and launches them in their own tmux sessions. They run at the same time, completely independently. `mngr list` shows both in state `RUNNING`:

> 📸 **Screenshot:** `mngr list` showing claude-impl and codex-impl both RUNNING

---

## What they wrote

Both agents got the structure right: filter quotes by category before random selection, raise `ValueError` on no match, catch it in the API layer and return 404. The differences were in the details.

Claude used FastAPI's `Query(default=None)` wrapper to declare the parameter:

```python
def generate_quote(category: str | None = Query(default=None)):
```

Codex skipped `Query` and let FastAPI infer the query parameter from the type annotation:

```python
def generate_quote(category: str | None = None):
```

Both work. Codex also pre-computed `category_filter = category.lower()` once before the list comprehension; Claude called `.lower()` twice per element. Codex updated the docstring with an `Args:` section. Claude didn't touch it.

> 📸 **Screenshot:** claude-impl diff showing quote_engine.py changes

> 📸 **Screenshot:** codex-impl diff showing quote_engine.py changes

---

## The cross-review

Codex reviewed Claude's diff, Claude reviewed Codex's, then vet ran on both branches:

```bash
# Spawn cross-review agents
mngr create review-claude codex --message "Review this diff against the goal..." --no-connect -- --full-auto
mngr create review-codex --message "Review this diff against the goal..." --no-connect -- --dangerously-skip-permissions

# Read reviews
mngr transcript review-claude
mngr transcript review-codex

# Vet both branches
git checkout claude-impl && vet "$(cat prompt.txt)" --base-commit main --agentic --agent-harness claude
git checkout codex-impl && vet "$(cat prompt.txt)" --base-commit main --agentic --agent-harness codex
git checkout main
```

> 📸 **Screenshot:** `mngr transcript review-claude` showing Codex's critique of Claude's implementation

Vet found three issues in Claude's implementation and none in Codex's. Two are worth calling out. The docstring for `generate_quote` was never updated to document the new `category` parameter or the `ValueError` it now raises - a caller reading only the docstring has no idea the function can throw. The more interesting one: **`json.JSONDecodeError` is a subclass of `ValueError` since Python 3.5**. That means a corrupted or missing quotes file gets silently caught by the `except ValueError` block in `api/main.py` and returned to the caller as HTTP 404 with "No quotes found for that category" - an infrastructure failure masquerading as a normal empty result.

> 📸 **Screenshot:** vet output on claude-impl showing the three issues

---

## What I'd actually merge

Codex's implementation. It's cleaner, it documented what it changed, and it passed vet with no issues. The `Query()` wrapper Claude used is fine for more complex parameter validation, but unnecessary here. I'd add a `pytest` entry to `requirements.txt` either way, since neither agent did that.

---

## Going further: remote sandboxes

Everything above ran locally. That's fine for a demo, but local agents share your machine's resources. mngr supports Modal sandboxes with one flag change:

```bash
mngr create claude-impl@.modal --message "$(cat prompt.txt)" --no-connect -- --dangerously-skip-permissions
mngr create codex-impl@.modal codex --message "$(cat prompt.txt)" --no-connect -- --full-auto
```

The `@.modal` syntax spins up a fresh Modal sandbox per agent. It auto-shuts down when idle, so you only pay for inference and a short tail of compute after the agent finishes.

> 📸 **Screenshot:** terminal showing mngr create on Modal

---

## Who this is for

If you already have both the Claude Code and Codex subscriptions, this is a way to actually get value from both at the same time. I'm on the $20 plan for each - and running them in parallel on the same task gets me more useful output than upgrading either one to a higher tier. You're not adding a new review step, you're just using what you're already paying for more deliberately.

It's also useful if you want to understand where each model actually excels. Running them on the same prompt back to back is one of the better ways to build an intuition for that - not from reading benchmarks, but from seeing the actual differences in how they approach the same problem. Over time that makes it easier to decide which one to reach for depending on what you're doing, instead of just defaulting to the same one every time.

Small teams doing informal review can use vet as a pre-review gate. It catches the mechanical things - undocumented parameters, swallowed exceptions, missing dependencies in requirement files - so the human reviewer isn't spending attention on them.

---

## Install and setup feedback

I ran both tools from scratch for this tutorial. Here's what I actually ran into.

### What worked well

- `mngr list` is genuinely useful. Seeing both agents running in parallel with their states at a glance is exactly what you'd want.
- The `transcript` command is good for observability. Being able to read the agent's full reasoning after the fact, without having been connected live, is the kind of thing that's actually useful rather than just decorative.
- Vet's output was specific and actionable. The `JSONDecodeError` finding was the kind of thing a human reviewer would likely miss - it didn't just say "bad error handling," it explained exactly why the `except ValueError` clause was too broad and what the actual failure mode would be.
- The `--agentic` flag is a smart call: it uses your existing Claude Code or Codex subscription instead of separate API credits, so there's no extra cost to running it.
- Both agents produced working, correct code on the first try with no intervention. That's not nothing.

### What I ran into

- **The plugin wizard gets silently skipped if you install non-interactively** (i.e., piping the install script to bash). Without it, the Claude plugin isn't installed, which means `mngr transcript` doesn't work and events aren't captured. You won't know this until you try to read a transcript and get nothing back. By then, the run is already done and you can't recover it. The fix is `mngr plugin install-wizard`, but you have to destroy and recreate your agents to get transcripts on the next run. A clear prompt after install - even just "run `mngr plugin install-wizard` before creating agents" - would prevent this entirely.

- **Agents block on every action without permission bypass flags.** Without passing `--dangerously-skip-permissions` (Claude) or `--full-auto` (Codex) through the `--` passthrough, the agents pause and wait for you to manually approve every file read and write. Nothing in the quickstart mentions this as a required step for unattended use. I had to connect to each agent and babysit them before figuring out what was happening.

- **There's no "verify your setup works" step before running real tasks.** A simple smoke test - `mngr create test --message "say hello" --no-connect`, check the transcript, destroy it - would catch the missing plugin issue in under a minute. Without it, you find out something's broken after a full implementation run.

- **`mngr pull` doesn't create a git branch.** It syncs the agent's files to your working tree, which means you have to manually `git checkout -b` and commit before you can do `git diff main...branch`. The "git for agents" framing sets a reasonable expectation that pull would land on a named ref.

- **mngr isn't on PATH immediately after install.** It lands in `~/.local/bin` but that path isn't sourced automatically, so the first command after install returns `mngr: command not found`.

- **The pip package is `verify-everything` but the CLI is `vet`.** If you search for "vet" on PyPI you find nothing. Easy to assume the install failed.

- **Destroying an agent doesn't always clean up its git branch.** When agent creation fails partway through, mngr leaves behind a `mngr/<name>` branch. Re-running `mngr create` with the same name fails with "branch already exists" - and the error message doesn't tell you that's the cause.

- **vet exit code 10 means "issues found," not "something went wrong."** In a chained command, a non-zero exit code looks like a failure. Worth a note in the docs, especially for anyone scripting this or running it in CI.

### Overall

The core concept works and the output is genuinely useful. The rough edges are almost entirely in initial setup, not in what the tools do once they're running. The friction points are fixable documentation gaps rather than fundamental problems.
