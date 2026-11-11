import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import release


class ReleaseTests(unittest.TestCase):
    def populate(self, path):
        for name in release.expected_assets("0.18.2"):
            (path / name).write_bytes(b"synthetic package")

    def test_complete_set_gets_checksums(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            self.populate(path)
            assets = release.checksums(path, "0.18.2")
            self.assertEqual(len(assets), 27)
            digest = hashlib.sha256(b"synthetic package").hexdigest()
            self.assertEqual(len((path / "SHA256SUMS.txt").read_text().splitlines()), 26)
            self.assertTrue(all(line.startswith(digest) for line in (path / "SHA256SUMS.txt").read_text().splitlines()))

    def test_missing_unexpected_and_empty_packages_are_rejected(self):
        for failure in ("missing", "unexpected", "empty"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                path = Path(directory)
                self.populate(path)
                package = path / "openpdf-web-0.18.2.zip"
                if failure == "missing":
                    package.unlink()
                elif failure == "empty":
                    package.write_bytes(b"")
                else:
                    (path / "unexpected.zip").write_bytes(b"extra")
                with self.assertRaises(ValueError):
                    release.checksums(path, "0.18.2")
                self.assertFalse((path / "SHA256SUMS.txt").exists())

    def test_published_release_cannot_be_replaced(self):
        data = json.dumps([[{"tag_name": "v0.18.2", "draft": False}]])
        with patch.object(release, "gh", return_value=data), self.assertRaisesRegex(ValueError, "already published"):
            release.existing_release("v0.18.2")

    def test_paginated_draft_is_found(self):
        data = json.dumps([[], [{"tag_name": "v0.18.2", "draft": True}]])
        with patch.object(release, "gh", return_value=data):
            self.assertTrue(release.existing_release("v0.18.2"))
            self.assertFalse(release.existing_release("v0.18.3"))

    def test_existing_tag_must_match_build_commit(self):
        for kind, sha in (("commit", "b" * 40), ("tag", "a" * 40)):
            refs = [{"ref": "refs/tags/v0.18.2", "object": {"type": kind, "sha": sha}}]
            with self.subTest(kind=kind), patch.object(release, "gh", return_value=json.dumps(refs)):
                with self.assertRaisesRegex(ValueError, "does not point directly"):
                    release.validate_tag("v0.18.2", "a" * 40)

    def test_draft_does_not_write_when_tag_names_another_commit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Cargo.toml").write_text('[workspace.package]\nversion="0.18.2"\n')
            packages = root / "dist/release"
            packages.mkdir(parents=True)
            self.populate(packages)

            def respond(*args):
                if args[0] == "api" and "matching-refs" in args[1]:
                    return json.dumps([{"ref": "refs/tags/v0.18.2", "object": {"type": "commit", "sha": "b" * 40}}])
                if args[0] == "api":
                    return "[[]]"
                return ""

            env = {"GITHUB_REPOSITORY": release.REPOSITORY, "GITHUB_REF": "refs/heads/release", "GITHUB_SHA": "a" * 40}
            with patch.dict("os.environ", env, clear=True), patch.object(release, "gh", side_effect=respond) as gh:
                with self.assertRaisesRegex(ValueError, "does not point directly"):
                    release.draft(root)
                self.assertTrue(all(call.args[0] == "api" for call in gh.call_args_list))

    def test_absent_matching_or_longer_tag_is_allowed(self):
        for refs in ([], [{"ref": "refs/tags/v0.18.2", "object": {"type": "commit", "sha": "a" * 40}}],
                     [{"ref": "refs/tags/v0.18.20", "object": {"type": "commit", "sha": "b" * 40}}]):
            with patch.object(release, "gh", return_value=json.dumps(refs)):
                release.validate_tag("v0.18.2", "a" * 40)

    def test_wrong_repository_or_branch_cannot_create_release(self):
        for env in ({"GITHUB_REPOSITORY": "other/repo", "GITHUB_REF": "refs/heads/release"},
                    {"GITHUB_REPOSITORY": release.REPOSITORY, "GITHUB_REF": "refs/heads/main"}):
            with patch.dict("os.environ", env, clear=True), patch.object(release, "gh") as gh:
                with self.assertRaises(ValueError):
                    release.draft(Path("unused"))
                gh.assert_not_called()

    def test_current_sources_are_valid(self):
        release.validate_sources(release.ROOT)

    def test_source_replacement_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / ".cargo").mkdir()
            (path / ".cargo/config.toml").write_text('[source.crates-io]\nreplace-with="other"\n')
            with self.assertRaisesRegex(ValueError, "overrides"):
                release.validate_sources(path)
