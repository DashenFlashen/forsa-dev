# Import Existing Branch Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Let users create a forsa-dev environment from an existing git branch via a new "Import Branch" card in the dashboard.

**Architecture:** Two new `git.py` functions handle listing and checking out existing branches. `up_env` gets an `existing_branch` parameter that bypasses branch creation. A new `ImportBranch.jsx` card in the dashboard fetches available branches, derives an env name from the selected branch, and submits to the existing `POST /api/environments` endpoint.

**Tech Stack:** Python (backend), React + Tailwind (frontend). No new dependencies.

---

### Task 1: `git.list_branches`

**Files:**
- Modify: `src/forsa_dev/git.py`
- Test: `tests/test_git.py`

The function lists all branches available to import: local + remote-tracking (via DWIM), minus branches already checked out in a worktree, minus `main`. Fetch failures are silently ignored (no remote in tests).

**Step 1: Write the failing test**

Add to `tests/test_git.py`:
```python
import subprocess
from forsa_dev.git import list_branches  # add to existing import

def test_list_branches_returns_available_branches(git_repo, tmp_path):
    # Create two branches
    subprocess.run(["git", "branch", "old-work"], check=True, capture_output=True, cwd=git_repo)
    subprocess.run(["git", "branch", "feature/cool-thing"], check=True, capture_output=True, cwd=git_repo)
    branches = list_branches(git_repo)
    assert "old-work" in branches
    assert "feature/cool-thing" in branches
    assert "main" not in branches


def test_list_branches_excludes_worktree_branches(git_repo, tmp_path):
    subprocess.run(["git", "branch", "in-use"], check=True, capture_output=True, cwd=git_repo)
    subprocess.run(["git", "branch", "available"], check=True, capture_output=True, cwd=git_repo)
    # Check out in-use as a worktree
    wt = tmp_path / "wt"
    subprocess.run(["git", "worktree", "add", str(wt), "in-use"], check=True, capture_output=True, cwd=git_repo)
    branches = list_branches(git_repo)
    assert "in-use" not in branches
    assert "available" in branches
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_git.py::test_list_branches_returns_available_branches tests/test_git.py::test_list_branches_excludes_worktree_branches -v
```
Expected: FAIL with `ImportError` (function doesn't exist yet).

**Step 3: Implement `list_branches` in `src/forsa_dev/git.py`**

Add after the existing functions:
```python
def list_branches(repo: Path) -> list[str]:
    """List branches available to import (excludes main and worktree-checked-out branches)."""
    _git(["fetch", "--all", "--quiet"], repo)  # ignore failure — no remote in tests

    local = _git(["branch", "--format=%(refname:short)"], repo)
    local_branches = {b.strip() for b in local.stdout.splitlines() if b.strip()}

    remote = _git(["branch", "-r", "--format=%(refname:short)"], repo)
    remote_branches = set()
    for b in remote.stdout.splitlines():
        b = b.strip()
        if not b or "HEAD" in b:
            continue
        if b.startswith("origin/"):
            remote_branches.add(b[len("origin/"):])

    all_branches = local_branches | remote_branches

    worktree_result = _git(["worktree", "list", "--porcelain"], repo)
    in_use = set()
    for line in worktree_result.stdout.splitlines():
        if line.startswith("branch "):
            in_use.add(line.split("refs/heads/", 1)[-1])

    return sorted(all_branches - in_use - {"main"})
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_git.py::test_list_branches_returns_available_branches tests/test_git.py::test_list_branches_excludes_worktree_branches -v
```
Expected: PASS

**Step 5: Run full test suite**

```bash
uv run pytest -q
```
Expected: all pass

**Step 6: Commit**

```bash
git add src/forsa_dev/git.py tests/test_git.py
git commit -m "feat: add git.list_branches"
```

---

### Task 2: `git.create_worktree_from_branch`

**Files:**
- Modify: `src/forsa_dev/git.py`
- Test: `tests/test_git.py`

Checks out an existing branch as a worktree without creating a new branch.

**Step 1: Write the failing test**

Add to `tests/test_git.py`:
```python
from forsa_dev.git import create_worktree_from_branch  # add to existing import

def test_create_worktree_from_branch(git_repo, tmp_path):
    subprocess.run(["git", "branch", "existing"], check=True, capture_output=True, cwd=git_repo)
    wt = tmp_path / "worktrees" / "existing"
    create_worktree_from_branch(repo=git_repo, branch="existing", worktree=wt)
    assert wt.exists()
    # Verify it's on the expected branch
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        capture_output=True, text=True, cwd=wt,
    )
    assert result.stdout.strip() == "existing"


def test_create_worktree_from_branch_fails_for_missing_branch(git_repo, tmp_path):
    wt = tmp_path / "worktrees" / "no-such"
    with pytest.raises(RuntimeError, match="git worktree add failed"):
        create_worktree_from_branch(repo=git_repo, branch="no-such-branch", worktree=wt)
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_git.py::test_create_worktree_from_branch tests/test_git.py::test_create_worktree_from_branch_fails_for_missing_branch -v
```
Expected: FAIL with `ImportError`.

**Step 3: Implement in `src/forsa_dev/git.py`**

Add after `list_branches`:
```python
def create_worktree_from_branch(repo: Path, branch: str, worktree: Path) -> None:
    """Check out an existing branch as a worktree (does not create a new branch)."""
    worktree.parent.mkdir(parents=True, exist_ok=True)
    result = _git(["worktree", "add", str(worktree), branch], repo)
    if result.returncode != 0:
        raise RuntimeError(f"git worktree add failed: {result.stderr}")
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_git.py::test_create_worktree_from_branch tests/test_git.py::test_create_worktree_from_branch_fails_for_missing_branch -v
```
Expected: PASS

**Step 5: Run full test suite and commit**

```bash
uv run pytest -q
git add src/forsa_dev/git.py tests/test_git.py
git commit -m "feat: add git.create_worktree_from_branch"
```

---

### Task 3: Extend `up_env` with `existing_branch`

**Files:**
- Modify: `src/forsa_dev/operations.py`
- Test: `tests/test_operations.py`

When `existing_branch` is provided: skip branch creation, use `create_worktree_from_branch`, set `env.branch = existing_branch`. In the error rollback, skip `delete_branch` since we didn't create it.

**Step 1: Write the failing test**

Add to `tests/test_operations.py`:
```python
def test_up_env_from_existing_branch(up_cfg, git_repo):
    cfg = up_cfg
    # Create a branch to import
    import subprocess
    subprocess.run(["git", "branch", "my-feature"], check=True, capture_output=True, cwd=git_repo)
    with patch("forsa_dev.operations.tmux.create_session"), \
         patch("forsa_dev.operations.ttyd.start_ttyd", return_value=1):
        env = up_env(cfg, USER, "my-feature", existing_branch="my-feature")
    assert env.name == "my-feature"
    assert env.branch == "my-feature"


def test_up_env_from_existing_branch_does_not_delete_branch_on_rollback(up_cfg, git_repo):
    cfg = up_cfg
    import subprocess
    subprocess.run(["git", "branch", "keep-me"], check=True, capture_output=True, cwd=git_repo)
    with patch("forsa_dev.operations.allocate_ports", side_effect=RuntimeError("no ports")), \
         patch("forsa_dev.operations.git.remove_worktree") as mock_remove, \
         patch("forsa_dev.operations.git.delete_branch") as mock_delete:
        with pytest.raises(RuntimeError):
            up_env(cfg, USER, "keep-me", existing_branch="keep-me")
    mock_remove.assert_called_once()
    mock_delete.assert_not_called()
```

Note: `up_cfg` fixture uses `git_repo` — check how the fixture is defined; the `git_repo` fixture must be accessible. Looking at `up_cfg` in the test file, it takes `git_repo` as a parameter already, so add `git_repo` parameter to these test functions.

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_operations.py::test_up_env_from_existing_branch tests/test_operations.py::test_up_env_from_existing_branch_does_not_delete_branch_on_rollback -v
```
Expected: FAIL.

**Step 3: Modify `up_env` in `src/forsa_dev/operations.py`**

Change the signature:
```python
def up_env(
    cfg: Config,
    user: str,
    name: str,
    from_branch: str = "main",
    with_claude: bool = False,
    data_dir: Path | None = None,
    existing_branch: str | None = None,
) -> Environment:
```

Replace the branch creation block (currently `git.create_branch_and_worktree(...)`) with:
```python
    if existing_branch:
        git.create_worktree_from_branch(cfg.repo, existing_branch, worktree)
        branch = existing_branch
    else:
        git.create_branch_and_worktree(cfg.repo, name, worktree, from_branch)
        branch = name
```

Update the `Environment(...)` constructor — change `branch=name` to `branch=branch`.

Update the `except Exception` rollback block — change:
```python
    except Exception:
        git.remove_worktree(cfg.repo, worktree)
        git.delete_branch(cfg.repo, name, force=True)
        raise
```
to:
```python
    except Exception:
        git.remove_worktree(cfg.repo, worktree)
        if not existing_branch:
            git.delete_branch(cfg.repo, name, force=True)
        raise
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_operations.py -v
```
Expected: all pass (including existing tests).

**Step 5: Run full suite and commit**

```bash
uv run pytest -q
git add src/forsa_dev/operations.py tests/test_operations.py
git commit -m "feat: extend up_env with existing_branch parameter"
```

---

### Task 4: `GET /api/branches` endpoint + `existing_branch` in `CreateEnvRequest`

**Files:**
- Modify: `src/forsa_dev/dashboard/server.py`
- Test: `tests/test_dashboard_server.py`

**Step 1: Write the failing tests**

Add to `tests/test_dashboard_server.py`:
```python
def test_get_branches_returns_list(cfg_and_env):
    cfg, _ = cfg_and_env
    with patch("forsa_dev.dashboard.server.git.list_branches", return_value=["feature-a", "feature-b"]):
        app = create_app(cfg)
        client = TestClient(app)
        response = client.get("/api/branches")
    assert response.status_code == 200
    assert response.json() == {"branches": ["feature-a", "feature-b"]}


def test_post_create_environment_with_existing_branch(cfg_and_env):
    cfg, _ = cfg_and_env
    mock_env = MagicMock()
    mock_env.name = "my-feature"
    mock_env.port = 3003
    mock_env.ttyd_port = 7603
    payload = {"name": "my-feature", "from_branch": "main", "existing_branch": "feature/my-feature"}
    with patch("forsa_dev.dashboard.server.up_env", return_value=mock_env) as mock_up:
        app = create_app(cfg)
        client = TestClient(app)
        response = client.post("/api/environments", json=payload)
    assert response.status_code == 200
    mock_up.assert_called_once_with(
        cfg, USER, "my-feature",
        from_branch="main",
        with_claude=True,
        data_dir=None,
        existing_branch="feature/my-feature",
    )
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_dashboard_server.py::test_get_branches_returns_list tests/test_dashboard_server.py::test_post_create_environment_with_existing_branch -v
```
Expected: FAIL.

**Step 3: Modify `src/forsa_dev/dashboard/server.py`**

Add `git` to the import:
```python
from forsa_dev import git, tmux, ttyd
```

Add `existing_branch` to `CreateEnvRequest`:
```python
class CreateEnvRequest(BaseModel):
    name: str
    from_branch: str = "main"
    with_claude: bool = True
    data_dir: str | None = None
    existing_branch: str | None = None
```

Add the endpoint (before `post_create_environment`):
```python
    @app.get("/api/branches")
    def get_branches() -> dict[str, list[str]]:
        try:
            branches = git.list_branches(cfg.repo)
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e))
        return {"branches": branches}
```

Update `post_create_environment` to pass `existing_branch`:
```python
    @app.post("/api/environments")
    def post_create_environment(body: CreateEnvRequest) -> dict[str, Any]:
        user = getpass.getuser()
        data_dir = Path(body.data_dir) if body.data_dir else None
        try:
            env = up_env(
                cfg, user, body.name,
                from_branch=body.from_branch,
                with_claude=body.with_claude,
                data_dir=data_dir,
                existing_branch=body.existing_branch or None,
            )
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_dashboard_server.py -v
```
Expected: all pass.

**Step 5: Run full suite and commit**

```bash
uv run pytest -q && uv run ruff check src/ tests/
git add src/forsa_dev/dashboard/server.py tests/test_dashboard_server.py
git commit -m "feat: add GET /api/branches and existing_branch to CreateEnvRequest"
```

---

### Task 5: `ImportBranch.jsx` component

**Files:**
- Create: `dashboard/src/components/ImportBranch.jsx`

**Step 1: Create the component**

```jsx
import { useEffect, useState } from 'react'
import { Download, RefreshCw } from 'lucide-react'

const NAME_RE = /^[a-z0-9][a-z0-9_-]*$/

function deriveName(branch) {
  return branch.split('/').pop().toLowerCase().replace(/[^a-z0-9_-]/g, '-').replace(/^-+/, '')
}

export default function ImportBranch({ onCreate, defaultDataDir }) {
  const [branches, setBranches] = useState([])
  const [branch, setBranch] = useState('')
  const [name, setName] = useState('')
  const [dataDir, setDataDir] = useState('')
  const [loading, setLoading] = useState(false)
  const [loadingBranches, setLoadingBranches] = useState(true)

  useEffect(() => {
    fetch('/api/branches')
      .then((r) => r.json())
      .then((d) => { setBranches(d.branches); setLoadingBranches(false) })
      .catch(() => setLoadingBranches(false))
  }, [])

  useEffect(() => {
    if (defaultDataDir && !dataDir) setDataDir(defaultDataDir)
  }, [defaultDataDir])

  function handleBranchChange(e) {
    const b = e.target.value
    setBranch(b)
    setName(b ? deriveName(b) : '')
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!branch || !name.trim()) return
    setLoading(true)
    try {
      await onCreate(name.trim(), 'main', dataDir.trim() || null, branch)
      setBranch('')
      setName('')
    } finally {
      setLoading(false)
    }
  }

  const nameValid = NAME_RE.test(name)

  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900 px-5 py-4">
      <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-gray-500">
        Import Branch
      </h2>
      <form onSubmit={handleSubmit} className="flex flex-col gap-2">
        <div className="flex flex-wrap gap-2">
          <select
            value={branch}
            onChange={handleBranchChange}
            disabled={loadingBranches}
            className="flex-1 min-w-48 rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-100 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/50 disabled:opacity-50"
          >
            <option value="">{loadingBranches ? 'Loading…' : 'Select branch…'}</option>
            {branches.map((b) => (
              <option key={b} value={b}>{b}</option>
            ))}
          </select>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Environment name"
            className={`flex-1 min-w-32 rounded-md border px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-1 ${
              name && !nameValid
                ? 'border-red-500 bg-gray-800 focus:ring-red-500/50'
                : 'border-gray-700 bg-gray-800 focus:border-blue-500 focus:ring-blue-500/50'
            }`}
          />
          <button
            type="submit"
            disabled={loading || !branch || !nameValid}
            className="flex items-center gap-1.5 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50 transition-colors"
          >
            {loading
              ? <RefreshCw className="h-3.5 w-3.5 animate-spin" />
              : <Download className="h-3.5 w-3.5" />}
            {loading ? 'Importing…' : 'Import'}
          </button>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-xs text-gray-500 whitespace-nowrap w-16">Data dir</label>
          <input
            type="text"
            value={dataDir}
            onChange={(e) => setDataDir(e.target.value)}
            placeholder="/data/dev"
            className="flex-1 rounded-md border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm font-mono text-gray-300 placeholder-gray-600 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
          />
        </div>
      </form>
    </div>
  )
}
```

**Step 2: Commit**

```bash
git add dashboard/src/components/ImportBranch.jsx
git commit -m "feat: add ImportBranch component"
```

---

### Task 6: Wire `ImportBranch` into `App.jsx`, build, and install

**Files:**
- Modify: `dashboard/src/App.jsx`

**Step 1: Update `App.jsx`**

Add the import at the top:
```jsx
import ImportBranch from './components/ImportBranch'
```

Update `handleCreate` to accept an optional 4th `existingBranch` parameter:
```jsx
const handleCreate = useCallback(async (name, fromBranch, dataDir, existingBranch = null) => {
  try {
    await apiFetch('/api/environments', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name,
        from_branch: fromBranch,
        data_dir: dataDir || null,
        existing_branch: existingBranch || null,
      }),
    })
    await fetchEnvs()
  } catch (e) {
    setError(e.message)
  }
}, [fetchEnvs])
```

Add `ImportBranch` in the JSX, right after `CreateEnvironment`:
```jsx
<CreateEnvironment onCreate={handleCreate} defaultDataDir={defaultDataDir} />
<ImportBranch onCreate={handleCreate} defaultDataDir={defaultDataDir} />
```

**Step 2: Build the dashboard**

```bash
cd dashboard && npm run build
```
Expected: build succeeds with no errors.

**Step 3: Run full test suite and ruff**

```bash
uv run pytest -q && uv run ruff check src/ tests/
```
Expected: all pass, no lint errors.

**Step 4: Commit built assets and reinstall**

```bash
# Stage source changes
git add dashboard/src/App.jsx

# Stage rotated static assets (old files deleted, new files added)
git add src/forsa_dev/dashboard/static/
git rm src/forsa_dev/dashboard/static/assets/index-*.js src/forsa_dev/dashboard/static/assets/index-*.css 2>/dev/null || true
git add src/forsa_dev/dashboard/static/assets/

git commit -m "feat: wire ImportBranch into dashboard"

uv tool install --reinstall /path/to/forsa-dev
```

Replace `/path/to/forsa-dev` with the actual project root path (find it with `pwd` from project root).
