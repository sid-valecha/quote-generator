# Cross-agent code review with mngr

## The problem

I use both Claude Code and Codex depending on what I'm working on. They're not interchangeable - they make different tradeoffs and catch different things. The annoying part isn't choosing one, it's that running both on the same task and comparing what they produce is a slow, manual process. You'd need to set up separate working directories, track which agent touched what, and then squint at two diffs side by side. Most people don't bother, which means you're leaving a cheap source of signal on the table.

## What this tutorial shows

mngr lets you spawn multiple coding agents in parallel, each working in an isolated git worktree, and gives you the tools to pull their work back and compare it. Vet adds a structured second-opinion layer, reviewing each agent's diff for correctness and goal adherence using your existing Claude Code or Codex subscription. Both tools work with the agent CLIs you already have, no API keys required.

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

## Running both agents in parallel

```bash
mngr create claude-impl --message "$(cat prompt.txt)" --no-connect -- --dangerously-skip-permissions
mngr create codex-impl codex --message "$(cat prompt.txt)" --no-connect -- --full-auto
```

mngr creates a separate git worktree for each agent and launches them in their own tmux sessions. They run at the same time, completely independently. `mngr list` shows both in state `RUNNING`:

[SCREENSHOT: mngr list showing claude-impl and codex-impl both RUNNING]

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

[SCREENSHOT: claude-impl diff showing quote_engine.py changes]

[SCREENSHOT: codex-impl diff showing quote_engine.py changes]

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

[SCREENSHOT: mngr transcript review-claude showing Codex's critique of Claude's implementation]

Vet found three issues in Claude's implementation and none in Codex's. Two are worth calling out. The docstring for `generate_quote` was never updated to document the new `category` parameter or the `ValueError` it now raises - a caller reading only the docstring has no idea the function can throw. The more interesting one: **`json.JSONDecodeError` is a subclass of `ValueError` since Python 3.5**. That means a corrupted or missing quotes file gets silently caught by the `except ValueError` block in `api/main.py` and returned to the caller as HTTP 404 with "No quotes found for that category" - an infrastructure failure masquerading as a normal empty result.

[SCREENSHOT: vet output on claude-impl showing the three issues]

## What I'd actually merge

Codex's implementation. It's cleaner, it documented what it changed, and it passed vet with no issues. The `Query()` wrapper Claude used is fine for more complex parameter validation, but unnecessary here. I'd add a `pytest` entry to `requirements.txt` either way, since neither agent did that.

## Going further: remote sandboxes

Everything above ran locally. That's fine for a demo, but local agents share your machine's resources. mngr supports Modal sandboxes with one flag change:

```bash
mngr create claude-impl@.modal --message "$(cat prompt.txt)" --no-connect -- --dangerously-skip-permissions
mngr create codex-impl@.modal codex --message "$(cat prompt.txt)" --no-connect -- --full-auto
```

The `@.modal` syntax spins up a fresh Modal sandbox per agent. It auto-shuts down when idle, so you only pay for inference and a short tail of compute after the agent finishes.

[SCREENSHOT: terminal showing mngr create on Modal]

## Who this is for

If you already use Claude Code and Codex, this is a cheap way to get a second opinion without changing your tools. You're not adding a new review step - you're running two agents instead of one and having them check each other's work while you do something else.

It's also useful if you're hitting Anthropic rate limits. Instead of waiting, you spill the same task to Codex, compare the results, and pick the better output. Running both in parallel often takes less total time than waiting for one to finish under rate limiting.

Small teams doing informal review can use vet as a pre-review gate. It catches the mechanical things - undocumented parameters, swallowed exceptions, missing dependencies in requirement files - so the human reviewer isn't spending attention on them.

## Install and setup feedback

[FEEDBACK SECTION — insert verbatim from separate file]
