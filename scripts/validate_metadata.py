#!/usr/bin/env python3
"""Validate the Reynard Soft7 (Sepolia) ERC-721 token metadata.

Checks every file in ``meta/*.json``:
  * is well-formed JSON
  * has the required ERC-721 fields (name, description, image)
  * has an ``image`` that is either a decodable base64 data-URI resolving to a
    real image, or an http(s) URL
  * has an ``attributes`` array of ``{trait_type, value}`` objects when present

Exits non-zero if any file fails, printing a per-file report. This is the
canonical integrity check for the metadata repo and is safe to run repeatedly.
"""
from __future__ import annotations

import base64
import binascii
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
META_DIR = REPO_ROOT / "meta"

REQUIRED_FIELDS = ("name", "description", "image")

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

    image = data.get("image")
    if isinstance(image, str) and image:
        if image.startswith("data:"):
            err = _check_data_uri(image)
            if err:
                errors.append(err)
        elif not image.startswith(("http://", "https://")):
            errors.append("image must be a data-URI or http(s) URL")

    attrs = data.get("attributes")
    if attrs is not None:
        if not isinstance(attrs, list):
            errors.append("'attributes' must be an array")
        else:
            for i, attr in enumerate(attrs):
                if not isinstance(attr, dict) or "trait_type" not in attr or "value" not in attr:
                    errors.append(f"attribute[{i}] must have 'trait_type' and 'value'")

    return errors


def main() -> int:
    if not META_DIR.is_dir():
        print(f"ERROR: metadata directory not found: {META_DIR}", file=sys.stderr)
        return 1

    files = sorted(META_DIR.glob("*.json"))
    if not files:
        print(f"ERROR: no metadata files found in {META_DIR}", file=sys.stderr)
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
