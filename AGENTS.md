# PFS repository guidance for coding agents

If a user provides only `https://github.com/Lu18835713910/paper-figure-story` and asks you to install or upgrade the Skill, follow this document and [INSTALL.md](INSTALL.md). The user is requesting an **installation**, not a demo, research run, or development checkout.

## Canonical install (supported Codex user Skill location)

1. Identify the target Agent and its **real active Skills directory**. For Codex user-level Skills it is `~/.codex/skills/paper-figure-story`. If running in another host or workspace, do not silently install in Codex's directory; determine its supported location and use `--target`.
2. Locate every potentially active `paper-figure-story` Skill with the host's discovery mechanism. An existing workspace Skill may override a newly installed user Skill. Do not promise to have replaced other copies you have not inspected.
3. Use the **real owner repository** and a clean, separate Git clone of `main` (not `v1.0.0`, `v1.1.0`, or `v1.1.1`). Check the Git remote points to `https://github.com/Lu18835713910/paper-figure-story`. Read `VERSION`, `SKILL.md`, `INSTALL.md`, and the installer before execution. The installer copies only Git-tracked files.
4. Run `python scripts/install_pfs_skill.py --dry-run` then `python scripts/install_pfs_skill.py` from the **clone**; set `--target` only for a verified alternate directory. Do not merge-copy into an existing Skill. The installer stages the new tree, backs up the old tree outside the active Skills directory, swaps directories and checks file hashes, with recovery on failure.
5. Confirm the installed `VERSION` is `1.2.0`, that `SKILL.md` and `scripts/run_pfs.py` exist, and the installed working content matches the source. Ask the user to start a new Agent session; where possible verify the **actual loaded** Skill path in that new session.
6. Report actual installed path, version, Git commit, backup location, alternate installs not changed, and any limitations or errors. A successful install does not prove Artifact-host render or scientific reconstruction passes.

Never `git reset --hard`, delete unrecognized folders, copy the checkout's `.git` directory to Skills, install to an assumed location for another Agent, remove private work, edit old release tags, or imply that the frozen v1.2.0 ZIP has gained post-release fixes. Do not run Git-hosted content automatically without examining it and respecting host/user permissions.

## Host discovery and mixed-version prevention (mandatory)

If the user sends only the repository URL and asks for an install/upgrade, the Agent must complete all of the following. "Installer exit 0" is not proof of these.

1. **Identify the real host first.** Ask the host for its actual Skill discovery result (registered Skill list / cache / tool-returned base directory). Do not infer the host from the repository docs. Known user-level locations differ and are **not interchangeable**:
   - WorkBuddy: `~/.workbuddy/skills/paper-figure-story`
   - Codex: `~/.codex/skills/paper-figure-story`
   Also check project/workspace-level Skills directories, other same-name registrations, and whether any candidate path is a symlink / Windows junction / reparse point. A backup, a plain Git clone, or a research working copy is **not** an active Skill.
2. **Enumerate every PFS copy** and record for each: path, `VERSION`, `SKILL.md` SHA-256, Git revision or install source, whether it is in the active search path, whether it is old, and whether it conflicts with another copy. Installers must be pointed at the verified active directory with `--target`; never assume the Codex default for a WorkBuddy host.
3. **Record both version and revision.** `main` can still read `VERSION=1.2.0` while containing post-release maintenance commits. Always record `git rev-parse HEAD` of the selected baseline together with `VERSION`; never use `VERSION` alone as version identity.
4. **Back up, preflight, replace, verify.** Take a full backup of the old active tree (including `.git` and any user-modified files) in addition to the installer's own backup. Run `--dry-run`, then install. Afterwards verify: no old-version files remain, every installed tracked file's SHA-256 equals the selected Git baseline, and the backup path plus restore command are reported. Never merge-copy old and new scripts or delete unknown directories.
5. **Session registration is a startup snapshot.** A Skill installed mid-session is generally NOT discovered by the current session. Do not claim the current session reloaded it. Start a **new host session** and verify through the host's own `Skill(paper-figure-story)` entry point: the returned `SKILL.md` path, that path's `VERSION`, and the SHA-256 of `SKILL.md` plus the key runtime scripts against the install manifest. If the current Agent cannot start such a session, deliver runnable verification commands and record automatic loading as `NOT_TESTED`; manually reading the new files or directly invoking its scripts in the old session is **not** a loading PASS.
6. **Script consistency for real runs.** For any paper task, log the absolute paths and SHA-256 of `scripts/run_pfs.py`, `project_research_logic.py`, `render_logic.py` and `build_pptx.py` that actually executed. They must all come from the same verified installation. Loading a v1.1.0 `SKILL.md` while running v1.2.0 scripts (or the reverse), or mixing install directories between the model, A and B, is a FAIL even if the output looks correct.
7. **Same-model A/B entry point.** A hand-authored Builder summary graph on a main-deck page is NOT the source-adjudicated A. To place the real A into the main deck, use the official Research Logic projection plus `render_logic.py --page-map`; do not label a legacy Builder summary as "same-source A". `render-products` requires the resolved `--metadata` carrying the Research Logic record (`RESEARCH_LOGIC_REQUIRED` is a contract gate, not a renderer bug).

Report `OLD_VERSION_DISCOVERY`, `SAFE_UPGRADE`, `ACTIVE_VERSION_IDENTITY`, `SKILL_AUTO_LOADING`, `SCRIPT_VERSION_CONSISTENCY` and `LEGACY_PATH_REGRESSION` separately. If the active version is still old or a single run mixes script versions, release readiness stays `NOT_READY`.

## Scientific generation after install

Installing is not equivalent to running PFS on a paper. For paper analysis, read the **actual installed** `SKILL.md`. For the source-bound A/B workflow, the Agent must adjudicate the actual paper's Research Logic and explicitly supply `--research-logic` and `--products with-network` when generating the same-model A/B views. `balanced` alone is not a topology switch. Represent one true research trajectory as one; preserve documented branches, shared evidence, and convergences, without inventing relations to make a complex-looking figure. Report Artifact and Office limits, and avoid claiming Full success for portable-only output.
