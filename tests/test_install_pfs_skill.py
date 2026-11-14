"""Regression tests for first install, old-version replacement, and rollback."""
from __future__ import annotations

import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import os
import subprocess
import unittest
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "install_pfs_skill.py"
spec = importlib.util.spec_from_file_location("install_pfs_skill", SCRIPT)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.repo = self.base / "repo"
        self.repo.mkdir()
        (self.repo / "scripts").mkdir()
        (self.repo / "VERSION").write_text("1.2.0\n", encoding="utf-8")
        (self.repo / "SKILL.md").write_text("---\nname: paper-figure-story\n---\n", encoding="utf-8")
        (self.repo / "scripts" / "run_pfs.py").write_text("print('ok')\n", encoding="utf-8")
        (self.repo / "README.md").write_text("Current", encoding="utf-8")
        (self.repo / "PRIVATE.txt").write_text("untracked secret", encoding="utf-8")
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "add", "VERSION", "SKILL.md",
                        "scripts/run_pfs.py", "README.md"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "-c", "user.name=Test",
                        "-c", "user.email=test@example.com", "commit", "-qm", "test"], check=True)
        self.target = self.base / "home" / ".codex" / "skills" / "paper-figure-story"

    def old_version(self, version="1.1.1"):
        self.target.mkdir(parents=True)
        (self.target / "SKILL.md").write_text("---\nname: paper-figure-story\n---\n")
        (self.target / "VERSION").write_text(version)

    def test_fresh_install_excludes_git_and_untracked_files(self):
        result = installer.install(self.repo, self.target)
        self.assertEqual(result["status"], "INSTALLED")
        self.assertIsNone(result["backup"])
        self.assertEqual((self.target / "VERSION").read_text().strip(), "1.2.0")
        self.assertFalse((self.target / ".git").exists())
        self.assertFalse((self.target / "PRIVATE.txt").exists())

    def test_upgrade_replaces_tree_and_backs_up_old_data(self):
        self.old_version("1.0.0")
        (self.target / "OLD_PLUGIN.py").write_text("old")
        result = installer.install(self.repo, self.target)
        self.assertFalse((self.target / "OLD_PLUGIN.py").exists())
        backup = Path(result["backup"])
        self.assertTrue((backup / "OLD_PLUGIN.py").is_file())
        self.assertFalse(str(backup).startswith(str(self.target.parent) + os.sep))

    def test_stage_activation_failure_restores_old(self):
        self.old_version()
        orig = Path.rename
        def fail_stage(path, new):
            if path.name.startswith(".pfs-stage-"):
                raise OSError("simulated activation failure")
            return orig(path, new)
        with mock.patch.object(Path, "rename", fail_stage):
            with self.assertRaises(installer.InstallError):
                installer.install(self.repo, self.target)
        self.assertEqual((self.target / "VERSION").read_text(), "1.1.1")

    def test_post_activation_validation_failure_restores_old(self):
        self.old_version()
        orig = installer.validate_skill
        def fail_check(path):
            if path == self.target:
                raise installer.InstallError("simulated validation failure")
            return orig(path)
        with mock.patch.object(installer, "validate_skill", fail_check):
            with self.assertRaises(installer.InstallError):
                installer.install(self.repo, self.target)
        self.assertEqual((self.target / "VERSION").read_text(), "1.1.1")

    def test_refuse_unrelated_directory(self):
        self.target.mkdir(parents=True)
        (self.target / "valuable.txt").write_text("do not overwrite")
        with self.assertRaises(installer.InstallError):
            installer.install(self.repo, self.target)
        self.assertTrue((self.target / "valuable.txt").is_file())

    def test_dry_run_does_not_write(self):
        self.assertEqual(installer.install(self.repo, self.target, True)["status"], "DRY_RUN")
        self.assertFalse(self.target.parent.exists())

    def test_tracked_symlink_rejected(self):
        outside = self.base / "outside.txt"
        outside.write_text("private")
        try:
            (self.repo / "link").symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("symlink unsupported")
        subprocess.run(["git", "-C", str(self.repo), "add", "link"], check=True)
        with self.assertRaises(installer.InstallError):
            installer.install(self.repo, self.target)

    def test_modified_checkout_rejected(self):
        (self.repo / "README.md").write_text("modified")
        with self.assertRaises(installer.InstallError):
            installer.install(self.repo, self.target)


if __name__ == "__main__":
    unittest.main()
