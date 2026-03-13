# WAIMS Workflow Guide

Use this guide whenever you want to test a new feature safely without affecting the live demo.

---

## Branch Setup

- `main` = live stable WAIMS demo
- `codex/staging` = safe testing branch

The files keep the same names on both branches. The branch decides whether you are working on live or staging.

---

## Local Testing

Before every local test, open PowerShell in `C:\GitHub\waims-python` and run:

```powershell
git branch --show-current
```

You want to see:

```powershell
codex/staging
```

If you see `main`, switch first:

```powershell
git checkout codex/staging
```

Then run the app:

```powershell
streamlit run dashboard.py
```

---

## Safe Staging Flow

1. Switch to staging:

```powershell
git checkout codex/staging
```

2. Run WAIMS locally:

```powershell
streamlit run dashboard.py
```

3. Test the feature.

4. Commit and push your changes on staging:

```powershell
git status
git add .
git commit -m "Describe the feature"
git push
```

5. Test the staging Streamlit app online.

Staging Streamlit settings:

- Branch: `codex/staging`
- Main file path: `dashboard.py`

6. Only after staging looks good, merge `codex/staging` into `main`.

---

## Merge To Live

When staging is ready:

1. Switch to `main`
2. Merge `codex/staging` into `main`
3. Push `main`
4. Recheck the live Streamlit app

GitHub Desktop flow:

1. Commit and push `codex/staging`
2. Switch branch to `main`
3. Click `Branch`
4. Click `Merge into current branch...`
5. Choose `codex/staging`
6. Push `main`

---

## Fail-Safes

### 1. Always check your branch first

Run this before local testing:

```powershell
git branch --show-current
```

### 2. Keep two Streamlit apps

- live app -> `main`
- staging app -> `codex/staging`

### 3. Protect `main` on GitHub

Branch protection is set on the GitHub website, not GitHub Desktop.

Recommended rule for `main`:

- require a pull request before merging
- prevent direct pushes to `main`

This helps stop accidental live changes before staging is tested.

---

## Quick Daily Checklist

```powershell
cd C:\GitHub\waims-python
git branch --show-current
git checkout codex/staging
streamlit run dashboard.py
```

If you are already on `codex/staging`, the checkout just confirms it.
