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

## Scientific generation after install

Installing is not equivalent to running PFS on a paper. For paper analysis, read the **actual installed** `SKILL.md`. For the source-bound A/B workflow, the Agent must adjudicate the actual paper's Research Logic and explicitly supply `--research-logic` and `--products with-network` when generating the same-model A/B views. `balanced` alone is not a topology switch. Represent one true research trajectory as one; preserve documented branches, shared evidence, and convergences, without inventing relations to make a complex-looking figure. Report Artifact and Office limits, and avoid claiming Full success for portable-only output.
