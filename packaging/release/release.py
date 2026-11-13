"""Validate OpenPDF release inputs and stage a complete, explicitly unsigned draft."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import tomllib

REPOSITORY = "Open-Scientific-Software/OpenPDF"
ROOT = Path(__file__).resolve().parents[2]


def version(root):
    value = tomllib.loads((root / "Cargo.toml").read_text())["workspace"]["package"]["version"]
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?", value):
        raise ValueError("unsupported release version in Cargo.toml")
    return value


def validate_sources(root):
    for name in (".cargo/config", ".cargo/config.toml"):
        path = root / name
        if not path.exists():
            continue
        config = tomllib.loads(path.read_text())
        if "patch" in config or "paths" in config or any(
            isinstance(source, dict) and "replace-with" in source
            for source in config.get("source", {}).values()
        ):
            raise ValueError(f"{name} overrides dependency sources")
    packages = tomllib.loads((root / "Cargo.lock").read_text())["package"]
    for package in packages:
        source = package.get("source", "")
        if source.startswith("git+") and not source.startswith("git+https://github.com/storytold/"):
            raise ValueError("Cargo.lock contains an unapproved git dependency")
        if not source and package["name"].startswith("openpdf") and package["version"] != version(root):
            raise ValueError(f"stale workspace version for {package['name']}")


def expected_assets(v):
    names = {f"openpdf-{v}-macos-universal.dmg", f"openpdf-cli-{v}-macos-universal.zip",
             f"openpdf-{v}-freebsd-x86_64.tar.gz", f"openpdf-web-{v}.zip"}
    for arch in ("x64", "x86", "arm64"):
        names.update({f"openpdf-{v}-windows-{arch}.msi", f"openpdf-{v}-windows-{arch}-portable.zip"})
    for arch in ("x86_64", "aarch64"):
        names.update(f"openpdf-{v}-linux-{arch}.{ext}" for ext in
                     ("AppImage", "AppImage.zsync", "deb", "rpm", "tar.gz", "flatpak"))
        names.add(f"openpdf-cli-{v}-linux-{arch}.tar.gz")
    names.update({f"openpdf-{v}-linux-riscv64.tar.gz", f"openpdf-cli-{v}-linux-riscv64.tar.gz"})
    return names


def checksums(directory, v):
    expected = expected_assets(v)
    actual = {p.name for p in directory.iterdir()} - {"SHA256SUMS.txt"}
    if actual != expected:
        raise ValueError(f"incomplete release: missing={sorted(expected - actual)}, unexpected={sorted(actual - expected)}")
    lines = []
    for name in sorted(expected):
        path = directory / name
        if path.is_symlink() or not path.is_file() or not path.stat().st_size:
            raise ValueError(f"empty or invalid release asset: {name}")
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        lines.append(f"{digest}  {name}\n")
    (directory / "SHA256SUMS.txt").write_text("".join(lines))
    return [str(directory / name) for name in sorted(expected)] + [str(directory / "SHA256SUMS.txt")]


def gh(*args):
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout


def existing_release(tag):
    # Listing with pagination distinguishes an absent release from permission/network failures.
    pages = json.loads(gh("api", f"repos/{REPOSITORY}/releases?per_page=100", "--paginate", "--slurp"))
    matches = [release for page in pages for release in page if release["tag_name"] == tag]
    if len(matches) > 1:
        raise ValueError("multiple releases have the requested tag")
    if matches and not matches[0]["draft"]:
        raise ValueError(f"{tag} is already published; bump the version before releasing again")
    return bool(matches)


def validate_tag(tag, sha):
    refs = json.loads(gh("api", f"repos/{REPOSITORY}/git/matching-refs/tags/{tag}"))
    for ref in refs:
        if ref["ref"] == f"refs/tags/{tag}":
            # GitHub ignores --target when the tag already exists. Reject mismatches rather
            # than publishing source archives for a different build or moving a user's tag.
            if ref["object"]["type"] != "commit" or ref["object"]["sha"] != sha:
                raise ValueError(f"existing {tag} does not point directly to build commit {sha}; resolve the tag explicitly before releasing")


def draft(root):
    if os.environ.get("GITHUB_REPOSITORY") != REPOSITORY or os.environ.get("GITHUB_REF") != "refs/heads/release":
        raise ValueError("draft creation is restricted to OpenPDF's release branch")
    sha = os.environ.get("GITHUB_SHA", "")
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("missing release commit SHA")
    v = version(root)
    assets = checksums(root / "dist/release", v)
    tag = f"v{v}"
    validate_tag(tag, sha)
    exists = existing_release(tag)
    notes = (
        f"# OpenPDF {v}\n\n"
        "**Unsigned release:** Windows and Linux packages have no publisher signature. "
        "macOS packages are ad-hoc signed, not Developer ID signed or notarized. "
        "Operating systems may warn about or block installation.\n\n"
        "This OpenPDF release includes the fork's branding and packaging, plus toolbar, "
        "sidebar and Fill & Sign layout improvements.\n\n"
        "Compare downloads with `SHA256SUMS.txt` to check file integrity. "
        "These checksums are not a publisher signature.\n\n"
        f"Built from `{sha}`.\n"
    )
    with tempfile.TemporaryDirectory() as temporary:
        note_path = Path(temporary) / "notes.md"
        note_path.write_text(notes)
        args = ["release", "edit" if exists else "create", tag, "--repo", REPOSITORY,
                "--draft", "--target", sha, "--title", f"OpenPDF v{v}", "--notes-file", str(note_path)]
        if "-" in v:
            args.append("--prerelease")
        gh(*args)
    gh("release", "upload", tag, "--repo", REPOSITORY, "--clobber", *assets)
    print(f"Draft {tag}: {len(assets) - 1} packages and SHA256SUMS.txt; review before publishing")


def main():
    if sys.argv[1:] == ["prepare"]:
        validate_sources(ROOT)
        print(f"version={version(ROOT)}")
    elif sys.argv[1:] == ["draft"]:
        draft(ROOT)
    else:
        raise ValueError("usage: release.py prepare|draft")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        print(f"release failed: {error}", file=sys.stderr)
        sys.exit(1)
