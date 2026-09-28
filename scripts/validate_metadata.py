#!/usr/bin/env python3
"""Validate Reynard Soft7 ERC-721 token metadata.

Checks every JSON file under ``meta/``, ``mask-depth-reynard/``, and
``reynard-prime/meta/``:

  * is well-formed JSON
  * has the required ERC-721 fields (name, description, image)
  * has an ``image`` that is either a decodable base64 data-URI resolving to a
    real image, or an https URL pinned to a commit on this repo's jsDelivr mirror
  * has https ``external_url`` / ``external_link`` values that stay on this
    project's Pages site or this GitHub repository
  * has an ``attributes`` array of ``{trait_type, value}`` objects when present

Exits non-zero if any file fails, printing a per-file report. This is the
canonical integrity check for the metadata repo and is safe to run repeatedly.
"""
from __future__ import annotations

import base64
import binascii
import json
import re
import sys
import urllib.parse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
METADATA_DIRS = (
    REPO_ROOT / "meta",
    REPO_ROOT / "mask-depth-reynard",
    REPO_ROOT / "reynard-prime" / "meta",
)

REQUIRED_FIELDS = ("name", "description", "image")
LINK_FIELDS = ("external_url", "external_link")
IMAGE_URL_FIELDS = ("image", "banner_image")

# Commit-pinned jsDelivr URLs. A branch name such as @main does not match.
PINNED_IMAGE_URL = re.compile(
    r"^https://cdn\.jsdelivr\.net/gh/tigerwillca/reynard-soft7-sepolia@[0-9a-f]{40}/.+"
)
LINK_PREFIXES = (
    "https://tigerwillca.github.io/reynard-soft7-sepolia",
    "https://github.com/tigerwillca/reynard-soft7-sepolia",
)
ACCOUNT_PAGES_ROOT = "https://tigerwillca.github.io"

# Magic-number prefixes for the image formats we expect in data-URIs.
IMAGE_MAGIC = {
    "jpeg": b"\xff\xd8\xff",
    "png": b"\x89PNG\r\n\x1a\n",
    "gif": b"GIF8",
    "webp": b"RIFF",
}


def _check_data_uri(image: str) -> str:
    """Return an error string for a data-URI image, or "" when valid."""
    header, _, payload = image.partition(",")
    if ";base64" not in header:
        return "data-URI is not base64-encoded"
    try:
        raw = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError) as exc:
        return f"data-URI base64 failed to decode: {exc}"
    if not raw:
        return "data-URI decoded to zero bytes"
    if not any(raw.startswith(magic) for magic in IMAGE_MAGIC.values()):
        return f"decoded bytes are not a known image format (starts with {raw[:4].hex()})"
    return ""


def _has_bounded_prefix(url: str, prefix: str) -> bool:
    if not url.startswith(prefix):
        return False
    rest = url[len(prefix) :]
    return rest == "" or rest[0] in "/?#"


def _check_image_url(url: str, field: str) -> str:
    if url.startswith("data:"):
        if field != "image":
            return f"{field} must be a pinned https image URL"
        return _check_data_uri(url)
    if url.startswith("http://"):
        return f"{field} must use https"
    if not PINNED_IMAGE_URL.match(url):
        return f"{field} must be a commit-pinned jsDelivr URL for this repository"
    return ""


def _check_link(url: str, field: str) -> str:
    if not isinstance(url, str) or not url.strip():
        return f"{field} must be a non-empty string"
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname:
        return f"{field} must be an https URL"
    if parsed.username or parsed.password or "@" in parsed.netloc:
        return f"{field} must not include credentials"
    bare = url.split("#", 1)[0].split("?", 1)[0].rstrip("/")
    if bare == ACCOUNT_PAGES_ROOT:
        return f"{field} must not point at the account Pages root"
    if not any(_has_bounded_prefix(url, prefix) for prefix in LINK_PREFIXES):
        return f"{field} must point at this project's site or repository"
    return ""


def validate_file(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        return [f"invalid JSON: {exc}"]

    if not isinstance(data, dict):
        return ["top-level JSON is not an object"]

    for field in REQUIRED_FIELDS:
        if field not in data:
            errors.append(f"missing required field '{field}'")
        elif not isinstance(data[field], str) or not data[field].strip():
            errors.append(f"field '{field}' must be a non-empty string")

    for field in IMAGE_URL_FIELDS:
        value = data.get(field)
        if value is None:
            continue
        if not isinstance(value, str) or not value.strip():
            errors.append(f"field '{field}' must be a non-empty string")
            continue
        err = _check_image_url(value, field)
        if err:
            errors.append(err)

    for field in LINK_FIELDS:
        if field not in data:
            continue
        err = _check_link(data[field], field)
        if err:
            errors.append(err)

    attrs = data.get("attributes")
    if attrs is not None:
        if not isinstance(attrs, list):
            errors.append("'attributes' must be an array")
        else:
            for i, attr in enumerate(attrs):
                if not isinstance(attr, dict) or "trait_type" not in attr or "value" not in attr:
                    errors.append(f"attribute[{i}] must have 'trait_type' and 'value'")

    return errors


def metadata_files() -> list[Path]:
    files: list[Path] = []
    for directory in METADATA_DIRS:
        if directory.is_dir():
            files.extend(directory.glob("*.json"))
    return sorted(files)


def main() -> int:
    if not (REPO_ROOT / "meta").is_dir():
        print(f"ERROR: metadata directory not found: {REPO_ROOT / 'meta'}", file=sys.stderr)
        return 1

    files = metadata_files()
    if not files:
        print("ERROR: no metadata files found", file=sys.stderr)
        return 1

    total_errors = 0
    for path in files:
        errors = validate_file(path)
        rel = path.relative_to(REPO_ROOT)
        if errors:
            total_errors += len(errors)
            print(f"FAIL {rel}")
            for err in errors:
                print(f"     - {err}")
        else:
            data = json.loads(path.read_text())
            kind = "data-URI" if str(data.get("image", "")).startswith("data:") else "url"
            print(f"OK   {rel}  ({data.get('name', '?')}, image={kind})")

    print("-" * 60)
    if total_errors:
        print(f"FAILED: {total_errors} problem(s) across {len(files)} file(s)")
        return 1
    print(f"PASSED: {len(files)} metadata file(s) validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
