# Branch Selector Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Return branch metadata (name, last commit date, worktree status) from the API and use it in the frontend to filter stale branches and fix the base branch selector.

**Architecture:** Change `list_branches()` to return rich branch objects instead of plain strings. The API endpoint passes this through. The frontend handles all filtering: worktree exclusion for import, date-based staleness, and a "Show all" toggle.

**Tech Stack:** Python (git subprocess), FastAPI, React

**Spec:** `docs/superpowers/specs/2026-03-28-branch-selector-design.md`

---

### Task 1: Update `list_branches()` tests for new return type

**Files:**
- Modify: `tests/test_git.py:81-101`

The existing tests assert against `list[str]`. Update them to assert against `list[dict]` with `name`, `last_commit`, and `in_worktree` keys. Also add a test for deduplication (local/remote same branch keeps more recent date).

- [ ] **Step 1: Update `test_list_branches_returns_available_branches`**

Replace the existing test at line 81-89 with:

```python
def test_list_branches_returns_branch_metadata(git_repo, tmp_path):
    subprocess.run(["git", "branch", "old-work"], check=True, capture_output=True, cwd=git_repo)
    subprocess.run(
        ["git", "branch", "feature/cool-thing"], check=True, capture_output=True, cwd=git_repo
    )
    branches = list_branches(git_repo)
    names = [b["name"] for b in branches]
    assert "old-work" in names
    assert "feature/cool-thing" in names
    assert "main" in names  # main is no longer excluded
    for b in branches:
        assert "name" in b
        assert "last_commit" in b
        assert "in_worktree" in b
        assert isinstance(b["in_worktree"], bool)
```

- [ ] **Step 2: Update `test_list_branches_excludes_worktree_branches`**

Replace the existing test at line 92-101 with:

```python
def test_list_branches_tags_worktree_branches(git_repo, tmp_path):
    subprocess.run(["git", "branch", "in-use"], check=True, capture_output=True, cwd=git_repo)
    subprocess.run(["git", "branch", "available"], check=True, capture_output=True, cwd=git_repo)
    wt = tmp_path / "wt"
    subprocess.run(
        ["git", "worktree", "add", str(wt), "in-use"], check=True, capture_output=True, cwd=git_repo
    )
    branches = list_branches(git_repo)
    by_name = {b["name"]: b for b in branches}
    assert by_name["in-use"]["in_worktree"] is True
    assert by_name["available"]["in_worktree"] is False
```

- [ ] **Step 3: Add deduplication test**

This test requires simulating a branch that exists both locally and on a remote. Create a local "remote" repo and fetch from it to produce both `refs/heads/` and `refs/remotes/origin/` entries for the same branch.

```python
def test_list_branches_deduplicates_local_and_remote(git_repo, tmp_path):
    """When a branch exists locally and on a remote, keep the more recent date."""
    # Create a "remote" repo with a branch
    remote = tmp_path / "remote"
    remote.mkdir()
    subprocess.run(["git", "init", "-b", "main", str(remote)], check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], check=True, capture_output=True, cwd=remote)
    subprocess.run(["git", "config", "user.name", "T"], check=True, capture_output=True, cwd=remote)
    (remote / "f.txt").write_text("v1")
    subprocess.run(["git", "add", "."], check=True, capture_output=True, cwd=remote)
    subprocess.run(["git", "commit", "-m", "init"], check=True, capture_output=True, cwd=remote)
    subprocess.run(["git", "checkout", "-b", "shared"], check=True, capture_output=True, cwd=remote)
    (remote / "f.txt").write_text("v2")
    subprocess.run(["git", "add", "."], check=True, capture_output=True, cwd=remote)
    subprocess.run(["git", "commit", "-m", "remote-update"], check=True, capture_output=True, cwd=remote)

    # Add as remote and fetch
    subprocess.run(
        ["git", "remote", "add", "origin", str(remote)], check=True, capture_output=True, cwd=git_repo
    )
    subprocess.run(["git", "fetch", "origin"], check=True, capture_output=True, cwd=git_repo)

    # Create a local branch "shared" from an older point (main)
    subprocess.run(["git", "branch", "shared"], check=True, capture_output=True, cwd=git_repo)

    branches = list_branches(git_repo)
    names = [b["name"] for b in branches]
    assert names.count("shared") == 1  # deduplicated, not listed twice
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `uv run pytest tests/test_git.py::test_list_branches_returns_branch_metadata tests/test_git.py::test_list_branches_tags_worktree_branches tests/test_git.py::test_list_branches_deduplicates_local_and_remote -v`
Expected: FAIL — `list_branches` returns strings, not dicts.

- [ ] **Step 5: Commit**

```bash
git add tests/test_git.py
git commit -m "test: update list_branches tests for rich metadata return type"
```

---

### Task 2: Implement new `list_branches()` return type

**Files:**
- Modify: `src/forsa_dev/git.py:79-103`

- [ ] **Step 1: Rewrite `list_branches()`**

Replace lines 79-103 of `src/forsa_dev/git.py` with:

```python
def list_branches(repo: Path) -> list[dict]:
    """List all branches with metadata (name, last_commit, in_worktree)."""
    _git(["fetch", "--all", "--quiet"], repo)  # ignore failure — no remote in tests

    # Get branch names and commit dates in one pass.
    # Unix timestamp for reliable comparison, ISO for display.
    ref_result = _git(
        ["for-each-ref", "--format=%(refname:short) %(committerdate:unix) %(committerdate:iso)", "refs/heads/", "refs/remotes/origin/"],
        repo,
    )

    branches: dict[str, tuple[int, str]] = {}  # name -> (unix_ts, iso_date)
    for line in ref_result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        # Format: "branch-name 1711545000 2026-03-27 14:30:00 +0200"
        parts = line.split(maxsplit=2)  # [name, unix_ts, iso_rest]
        if len(parts) < 3:
            continue
        name = parts[0]
        unix_ts = int(parts[1])
        iso_date = parts[2]

        if "HEAD" in name:
            continue
        if name.startswith("origin/"):
            name = name[len("origin/"):]

        if name not in branches or unix_ts > branches[name][0]:
            branches[name] = (unix_ts, iso_date)

    # Get worktree-checked-out branches
    worktree_result = _git(["worktree", "list", "--porcelain"], repo)
    in_use = set()
    for line in worktree_result.stdout.splitlines():
        if line.startswith("branch "):
            in_use.add(line.split("refs/heads/", 1)[-1])

    return sorted(
        [
            {"name": name, "last_commit": iso_date, "in_worktree": name in in_use}
            for name, (_ts, iso_date) in branches.items()
        ],
        key=lambda b: b["name"],
    )
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `uv run pytest tests/test_git.py -v`
Expected: All tests pass, including the two updated ones.

- [ ] **Step 3: Commit**

```bash
git add src/forsa_dev/git.py
git commit -m "feat: return branch metadata from list_branches()"
```

---

### Task 3: Update API endpoint and its test

**Files:**
- Modify: `src/forsa_dev/dashboard/server.py:228-235`
- Modify: `tests/test_dashboard_server.py:517-528`

- [ ] **Step 1: Update the dashboard server test mock**

Update `test_get_branches_returns_list` at line 517-528 of `tests/test_dashboard_server.py`. Change the mock return value and assertion to use the new dict format:

```python
def test_get_branches_returns_list(setup):
    user_configs, _, _ = setup
    with patch(
        "forsa_dev.dashboard.server.git.list_branches",
        return_value=[
            {"name": "feature-a", "last_commit": "2026-03-27 14:30:00 +0200", "in_worktree": False},
            {"name": "feature-b", "last_commit": "2026-03-26 10:00:00 +0200", "in_worktree": False},
        ],
    ):
        app = create_app(user_configs)
        client = TestClient(app)
        client.cookies.set("forsa_user", TEST_USER)
        response = client.get("/api/branches")
    assert response.status_code == 200
    data = response.json()
    names = [b["name"] for b in data["branches"]]
    assert "feature-a" in names
    assert "feature-b" in names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_dashboard_server.py::test_get_branches_returns_list -v`
Expected: FAIL — the mock returns dicts but the old assertion expects strings.

- [ ] **Step 3: Update the type annotation**

Change the `get_branches` function (lines 228-229) in `src/forsa_dev/dashboard/server.py` from:

```python
    @app.get("/api/branches")
    def get_branches(user: str = Depends(get_user)) -> dict[str, list[str]]:
```

to:

```python
    @app.get("/api/branches")
    def get_branches(user: str = Depends(get_user)) -> dict[str, list[dict]]:
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_dashboard_server.py::test_get_branches_returns_list tests/test_dashboard_server.py::test_get_branches_500_on_runtime_error -v`
Expected: Both pass.

- [ ] **Step 5: Commit**

```bash
git add src/forsa_dev/dashboard/server.py tests/test_dashboard_server.py
git commit -m "fix: update /api/branches return type and test for branch metadata"
```

---

### Task 4: Update frontend to handle branch objects and add filtering

**Files:**
- Modify: `dashboard/src/components/CreateEnvironment.jsx`

This task updates the frontend to:
1. Handle branch objects instead of strings
2. Filter stale branches (>90 days) by default
3. Add a "Show all" toggle per dropdown
4. Fix the base branch selector to include `main` and worktree branches

- [ ] **Step 1: Add filtering state and helper**

At the top of the component (after the existing state declarations around line 22), add:

```jsx
const [showAllBase, setShowAllBase] = useState(false)
const [showAllImport, setShowAllImport] = useState(false)

const STALE_DAYS = 90
```

Add a filtering helper before the return statement:

```jsx
function filterBranches(branchList, { excludeWorktree = false, alwaysInclude = [], showAll = false }) {
  const cutoff = new Date()
  cutoff.setDate(cutoff.getDate() - STALE_DAYS)
  return branchList.filter((b) => {
    if (excludeWorktree && b.in_worktree) return false
    if (alwaysInclude.includes(b.name)) return true
    if (!showAll && new Date(b.last_commit) < cutoff) return false
    return true
  })
}
```

- [ ] **Step 2: Update "From branch" tab dropdown**

Replace lines 157-167 (the select in the branch tab) to use filtered branch objects:

```jsx
<select
  value={branch}
  onChange={handleBranchChange}
  disabled={loadingBranches}
  className="flex-1 min-w-48 rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-100 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/50 disabled:opacity-50"
>
  <option value="">{loadingBranches ? 'Loading…' : 'Select branch…'}</option>
  {filterBranches(branches, { excludeWorktree: true, showAll: showAllImport }).map((b) => (
    <option key={b.name} value={b.name}>{b.name}</option>
  ))}
</select>
```

Add a "Show all" toggle after the select (inside the same `flex-wrap` div or just after it):

```jsx
{!showAllImport && branches.some((b) => !b.in_worktree && new Date(b.last_commit) < new Date(new Date().setDate(new Date().getDate() - STALE_DAYS))) && (
  <button
    type="button"
    onClick={() => setShowAllImport(true)}
    className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
  >
    Show all branches
  </button>
)}
```

- [ ] **Step 3: Update "New" tab base branch selector**

Replace lines 123-128 (the options inside the base branch select) to use filtered branch objects, always including `main`:

```jsx
<option value="main">main</option>
{filterBranches(branches, { alwaysInclude: [], showAll: showAllBase }).filter((b) => b.name !== 'main').map((b) => (
  <option key={b.name} value={b.name}>{b.name}</option>
))}
```

Add a "Show all" toggle after the base branch select row (after the closing `</div>` of the "From" row, around line 129):

```jsx
{!showAllBase && branches.some((b) => b.name !== 'main' && new Date(b.last_commit) < new Date(new Date().setDate(new Date().getDate() - STALE_DAYS))) && (
  <button
    type="button"
    onClick={() => setShowAllBase(true)}
    className="text-xs text-gray-500 hover:text-gray-300 transition-colors ml-18"
  >
    Show all branches
  </button>
)}
```

- [ ] **Step 4: Update `handleBranchChange` to work with branch name strings**

The `handleBranchChange` function (line 35-39) and `handleBranchSubmit` (line 56-67) pass `branch` as a string to `onCreate`. Since the select `value` is now `b.name` (still a string), these should continue to work without changes. Verify this is the case.

- [ ] **Step 5: Build and verify**

Run: `cd dashboard && npm run build && cd ..`
Expected: Build succeeds with no errors.

- [ ] **Step 6: Commit**

```bash
git add dashboard/src/components/CreateEnvironment.jsx
git commit -m "feat: filter stale branches and fix base branch selector"
```

---

### Task 5: Manual smoke test

- [ ] **Step 1: Deploy and test**

```bash
uv run pytest && uv run ruff check src/ tests/
uv tool install --force --reinstall .
systemctl --user restart forsa-dashboard
```

- [ ] **Step 2: Verify in browser**

1. Open the dashboard, go to "Create Environment"
2. On the "New" tab, click "Options…" — verify `main`, `next`, and other worktree-checked-out branches appear in the base branch selector
3. Verify stale branches (>90 days old) are hidden by default
4. Click "Show all branches" — verify stale branches appear
5. Switch to "From branch" tab — verify worktree-checked-out branches are excluded
6. Verify stale filtering and "Show all" toggle work here too

- [ ] **Step 3: Commit any fixes, then final commit**

```bash
git add -A  # after git status
git commit -m "chore: build dashboard for branch selector improvements"
```
