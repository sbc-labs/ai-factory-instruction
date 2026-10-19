# 09 — Environment, toolchain and access (set up before planning ends)

The first hours of the first project went to things that were not the product: a missing runtime, a container client configured for an app that was not installed, no git identity, a media tool that needed root. Check all of this in **planning Step 0** (02) and record the results; fix what can be fixed without the owner, and put the rest in `docs/BLOCKERS.md` as owner items with the exact command.

## 1. Inventory (write it into `docs/DECISIONS.md` as `ENV` lines and into `START_PROMPT.md` State)

The commands below are for a Node / pnpm / Docker stack, as examples; use the equivalents for the stack the spec names.

| Item | Check | Typical fix without root |
| --- | --- | --- |
| CPU, RAM, disk | `nproc`, `free -h`, `df -h /` | none — size the team to it (08 §1) |
| Language runtime | `node --version` (or the spec's runtime) | install at user level with a version manager (e.g. nvm); pin the version the spec names or the current LTS |
| Package manager | `corepack --version`, `pnpm --version` | `npm install -g corepack@latest` if the bundled one cannot fetch the pinned manager; clear its cache of the failed version |
| Containers | `docker version`, `docker compose version`, `docker info` | Docker **Engine** is enough; a `credsStore` entry pointing at a credential helper that is not installed must be removed — an owner item at every autonomy level (it is the owner's tool config, 12 §1); the architect proposes the exact edit and a backup command |
| Native tools the stack needs on the host (media, image, PDF tools) | `which <tool>` | a static build in `~/.local/bin`, checksum verified, recorded |
| Browser for E2E | the test runner's bundled browser; a system browser if media codecs are needed | install the runner's browsers; use the system browser channel for proprietary codecs |
| Git identity | `git config user.name` | per-commit `git -c user.name=… -c user.email=…` with the repo's existing identity; never write global config |
| Remote access | `gh auth status`, `git ls-remote origin` | owner logs in (`! gh auth login`) — an owner item |
| Paid-service keys | none must be present in agent environments | if keys exist in `.env`, the test harnesses must still force mock mode (05 "Safety and money") |

## 2. Non-interactive shells

Agents' shells usually do not load the user's shell profile: version-managed runtimes and `~/.local/bin` are not on `PATH`. Every kickoff prompt carries the exact `export PATH="…"` line, and every command an agent runs starts from it.

## 3. Pinning and reproducibility

- Pin exact versions for the runtime, the package manager (`packageManager` field), base images and key libraries; record them in the decisions log (`Versions`).
- Use the versions current at planning time (check official sources), not remembered ones; record the date checked.
- Lockfile installs only (`--frozen-lockfile`); a lockfile change belongs to the task that needs it and is called out in its report.
- Package managers may refuse releases younger than a minimum age (a supply-chain guard) or block install scripts by default; pin a version old enough, or record the explicit exclusion / allow-list entry in the decisions log — never disable the guard globally.

## 4. Remote and network quirks

- Pushes of many binary files (screenshots) can be reset by the remote. Push in steps through a temporary branch, then push the integration branch and delete the temporary one (01 "Commits and pushing").
- A permission layer may deny agents `git push` entirely; then agents commit locally and the integrator pushes (01 "Commits and pushing").
- Third-party documentation fetches can fail; when they do, use the installed package's type definitions as the source and record that in the decisions log.

## 5. Owner-run tooling hand-off

When the owner runs the project on their own machine, give exact commands: runtime version, package-manager fix, the mock-forced stack command, the health-wait command, and the URL. Note platform differences (e.g. a Linux browser inside images on an ARM laptop) and the fallback.

CHANGELOG
- 2026-10-18 created from the Content Studio Phase 1 retro (missing runtime, credential-helper misconfiguration, root-only media tool, old package-manager shim on the owner's laptop, remote resets on large pushes).
- 2026-10-18 review: inventory commands marked as examples for one stack; package-manager release-age / install-script guards; fixed two heading references.
- 2026-10-19 review 2: credential-helper config is an owner item at every level.
