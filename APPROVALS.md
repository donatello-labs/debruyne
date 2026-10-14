# Approvals & signals (you are the gate)

Nothing important lands on `main` or as a **version release** without your say-so.

## What you must approve

| Signal | What it is | Where you act |
|--------|------------|---------------|
| **PR review** | Contributor wants to merge code | Email + [Pull requests](https://github.com/donatello-labs/debruyne/pulls) → Review → Approve → Merge |
| **Release environment** | Someone (or you) asked to cut `vX.Y.Z` | Email + [Actions](https://github.com/donatello-labs/debruyne/actions) → run waiting → **Review deployments** → Approve |

## Email — turn these on (once)

1. GitHub → **Settings → Notifications**: https://github.com/settings/notifications  
   - Enable **Email** for Participating / Issue & PR activity.  
   - Enable **Actions** / workflow notifications if listed.  
2. Watch the repo: open https://github.com/donatello-labs/debruyne → **Watch → Custom**  
   - Tick **Pull requests**, **Releases**, **Deployments** (and **Actions** if available).  
3. Confirm the email under https://github.com/settings/emails is verified and not “noreply only” for notifications.

Optional: GitHub Mobile app → same notification toggles (good “señal” on the phone).

## How a contributor ships code

1. Opens a **Pull Request** → you get a **CODEOWNERS review request** (email).  
2. You review → **Approve** → **Merge**.  
3. Direct push to `main` by others is blocked by rulesets.

## How a new version is published

1. `CHANGELOG.md` must already contain `## [X.Y.Z]`.  
2. Actions → **Release (needs your approval)** → Run workflow → enter version + summary.  
3. Job pauses on environment **`release`** → you get a **deployment approval** email/signal.  
4. You **Approve** → tag `vX.Y.Z` + GitHub Release are created.

Until you approve that environment, **no new release is published**.

## Repo protections already configured

- Ruleset **Protect main — owner approval** (PR + code owner review).  
- Environment **`release`** with required reviewer `@donatello-labs/maintainers`.  
- Tag ruleset for `v*` (no force-move of version tags).  
- `.github/CODEOWNERS` → `* @donatello-labs/maintainers`
