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
PROOF_DIR = REPO_ROOT / "proofs" / "meta"
ART_DIR = REPO_ROOT / "proofs" / "art"

REQUIRED_FIELDS = ("name", "description", "image")
PROOF_TRAITS = ("tier", "color", "eyes", "signature", "globe")
CANON_DESCRIPTION = (
    "reynard-soft7 mascot cards on robinhood chain. ten percent of every mint "
    "routes back to soft7 holders proportional to what they hold. stake your card, "
    "feed the treasury, pull when you're ready."
)

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


def _check_png_or_gif(path: Path) -> str:
    raw = path.read_bytes()
    if raw.startswith(b"\x89PNG\r\n\x1a\n"):
        return ""
    if raw.startswith(b"GIF8"):
        return ""
    return f"{path.name} is not a PNG or GIF (starts with {raw[:4].hex()})"


def validate_proofs() -> list[str]:
    """The approval set: one real PNG or GIF per proof, five traits, unique signatures."""
    errors: list[str] = []
    if not PROOF_DIR.is_dir():
        return ["proof metadata directory missing"]

    signatures: list[str] = []
    colors: list[str] = []
    for n in range(1, 8):
        path = PROOF_DIR / f"{n}.json"
        if not path.exists():
            errors.append(f"missing {path.relative_to(REPO_ROOT)}")
            continue
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            errors.append(f"{path.name}: invalid JSON: {exc}")
            continue
        if data.get("description") != CANON_DESCRIPTION:
            errors.append(f"{path.name}: description is not the canon sentence")
        image = data.get("image")
        if not isinstance(image, str) or not (image.endswith(".png") or image.endswith(".gif")):
            errors.append(f"{path.name}: image must be one png or gif path")
        else:
            art = REPO_ROOT / image
            if not art.is_file():
                errors.append(f"{path.name}: image file missing: {image}")
            else:
                err = _check_png_or_gif(art)
                if err:
                    errors.append(f"{path.name}: {err}")
        attrs = data.get("attributes")
        if not isinstance(attrs, list) or len(attrs) != 5:
            errors.append(f"{path.name}: must have exactly 5 traits")
            continue
        found = []
        for attr in attrs:
            if not isinstance(attr, dict) or "trait_type" not in attr or "value" not in attr:
                errors.append(f"{path.name}: malformed trait")
                continue
            found.append(attr["trait_type"])
        if tuple(found) != PROOF_TRAITS:
            errors.append(f"{path.name}: traits must be {PROOF_TRAITS}, got {found}")
            continue
        by_type = {attr["trait_type"]: attr["value"] for attr in attrs}
        if by_type["tier"] != n:
            errors.append(f"{path.name}: tier must be {n}")
        signatures.append(str(by_type["signature"]))
        colors.append(str(by_type["color"]))
        # Fox proofs share the mascot eyes. They do not share face paint.
        if n in (1, 4, 5) and by_type["eyes"] != "Amber Lock":
            errors.append(f"{path.name}: fox eyes must stay Amber Lock")

    if len(signatures) != len(set(signatures)):
        errors.append("signatures (face paint) are not unique")
    if len(colors) != len(set(colors)):
        errors.append("colors are not unique across tiers")

    banner = ART_DIR / "banner.png"
    if not banner.is_file():
        errors.append("missing proofs/art/banner.png")
    else:
        err = _check_png_or_gif(banner)
        if err:
            errors.append(err)
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

    proof_errors = validate_proofs()
    if proof_errors:
        total_errors += len(proof_errors)
        print("FAIL proofs")
        for err in proof_errors:
            print(f"     - {err}")
    else:
        print("OK   proofs/meta/1.json–7.json  (png, five traits, unique signatures)")

    print("-" * 60)
    if total_errors:
        print(f"FAILED: {total_errors} problem(s) across {len(files)} file(s)")
        return 1
    print(f"PASSED: {len(files)} metadata file(s) and 7 proofs validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
