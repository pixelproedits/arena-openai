#!/usr/bin/env python3
"""Validate Arena release versions and build the installable skill ZIP."""
import argparse
import io
import json
import os
import sys
import zipfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(REPO, "skills", "arena")
sys.path.insert(0, SKILL)
import secure_io as SIO

PAYLOAD = ("SKILL.md", "rubric.md", "bracket.py", "guard.py", "secure_io.py",
           "strategies.json", "agents/openai.yaml", "LICENSE", "CREDITS.md")


def package(tag, output_dir):
    version = json.loads(SIO.read_text(os.path.join(REPO, "plugin.json")))["version"]
    installed_version = json.loads(SIO.read_text(os.path.join(REPO, ".codex-plugin", "plugin.json")))["version"]
    if version != installed_version:
        raise ValueError("plugin.json and .codex-plugin/plugin.json versions differ")
    if tag.removeprefix("v") != version:
        raise ValueError("release tag %r does not match plugin version %r" % (tag, version))
    SIO.make_dirs(output_dir)
    archive = os.path.join(output_dir, "arena-skill-v%s.zip" % version)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as output:
        for name in PAYLOAD:
            source = os.path.join(SKILL, name)
            contents = SIO.read_text(source).encode("utf-8")
            entry = zipfile.ZipInfo("arena/" + name)
            entry.external_attr = 0o100600 << 16
            entry.compress_type = zipfile.ZIP_DEFLATED
            output.writestr(entry, contents)
    SIO.write_bytes(archive, buffer.getvalue(), replace=False)
    return archive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True, help="published release tag, such as v0.3.2")
    parser.add_argument("--output-dir", default="dist")
    args = parser.parse_args()
    print("Created " + package(args.tag, os.path.abspath(args.output_dir)))


if __name__ == "__main__":
    main()
