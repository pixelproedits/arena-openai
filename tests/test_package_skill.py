"""Validate the release archive output without publishing it."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKAGER = os.path.join(REPO, "scripts", "package_skill.py")
EXPECTED = {"arena/SKILL.md", "arena/rubric.md", "arena/bracket.py",
            "arena/strategies.json", "arena/LICENSE", "arena/CREDITS.md",
            "arena/guard.py", "arena/secure_io.py", "arena/invoke.py", "arena/agents/openai.yaml"}


class PackageSkill(unittest.TestCase):
    def test_versioned_zip_contains_installable_payload(self):
        with tempfile.TemporaryDirectory(prefix="arena-package-") as temp:
            result = subprocess.run([sys.executable, PACKAGER, "--tag", "v0.3.6",
                                     "--output-dir", os.path.realpath(temp)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            archive = os.path.join(os.path.realpath(temp), "arena-skill-v0.3.6.zip")
            with zipfile.ZipFile(archive) as package:
                self.assertEqual(set(package.namelist()), EXPECTED)
                for name in ("LICENSE", "CREDITS.md"):
                    with open(os.path.join(REPO, name), "rb") as source:
                        self.assertEqual(package.read("arena/" + name), source.read())

    def test_rejects_tag_that_does_not_match_manifest(self):
        with tempfile.TemporaryDirectory(prefix="arena-package-") as temp:
            result = subprocess.run([sys.executable, PACKAGER, "--tag", "v0.0.0",
                                     "--output-dir", os.path.realpath(temp)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("does not match plugin version", result.stderr)

    def test_archive_is_private_and_existing_archive_is_preserved(self):
        with tempfile.TemporaryDirectory(prefix="arena-package-") as temp:
            root = os.path.realpath(temp)
            command = [sys.executable, PACKAGER, "--tag", "v0.3.6", "--output-dir", root]
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
            archive = Path(root) / "arena-skill-v0.3.6.zip"
            original = archive.read_bytes()
            self.assertEqual(archive.stat().st_mode & 0o777, 0o600)
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertEqual(archive.read_bytes(), original)

    def test_archive_symlink_does_not_overwrite_its_target(self):
        with tempfile.TemporaryDirectory(prefix="arena-package-") as temp:
            root = Path(os.path.realpath(temp))
            sentinel = root / "sentinel"
            sentinel.write_text("synthetic sentinel")
            (root / "arena-skill-v0.3.6.zip").symlink_to(sentinel)
            command = [sys.executable, PACKAGER, "--tag", "v0.3.6", "--output-dir", str(root)]
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertEqual(sentinel.read_text(), "synthetic sentinel")


if __name__ == "__main__":
    unittest.main(verbosity=2)
