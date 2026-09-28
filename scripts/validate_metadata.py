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
STAKING_LOOP = REPO_ROOT / "staking-loop.json"
LANDING = REPO_ROOT / "index.html"

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


def _trait(data: dict, trait_type: str) -> str | None:
    for attr in data.get("attributes") or []:
        if isinstance(attr, dict) and attr.get("trait_type") == trait_type:
            value = attr.get("value")
            return value if isinstance(value, str) else None
    return None


def validate_staking_loop() -> list[str]:
    """The Fox card locks FOX, the Tiger card locks tigerwillca, both burn to treasury."""
    errors: list[str] = []
    if not STAKING_LOOP.is_file():
        return ["staking-loop.json is missing"]
    try:
        loop = json.loads(STAKING_LOOP.read_text())
    except json.JSONDecodeError as exc:
        return [f"staking-loop.json is invalid JSON: {exc}"]

    locks = loop.get("locks")
    rewards = loop.get("rewards")
    treasury = loop.get("treasury") or {}
    if not isinstance(locks, list) or len(locks) != 2:
        errors.append("staking loop must lock exactly the fox and tiger cards")
    if not isinstance(rewards, list) or [r.get("symbol") for r in rewards] != ["USDG", "SPCX"]:
        errors.append("staking rewards must route to USDG then SpaceX (SPCX)")
    if treasury.get("action") != "burn" or not str(treasury.get("address", "")).startswith("0x"):
        errors.append("staking locks must burn to a treasury address")

    expected = {
        1: ("fox", "FOX", "0x387fbf7128868093D5E22A5528A5fC3D2BA8c9f5", "Fox"),
        2: ("tiger", "TIGER", "0x316C19b923B19E57A281996bfb9f8e96b2DA6427", "Tiger"),
    }
    by_id = {}
    if isinstance(locks, list):
        for lock in locks:
            if isinstance(lock, dict):
                by_id[lock.get("soft7TokenId")] = lock
    for token_id, (card, symbol, address, card_trait) in expected.items():
        lock = by_id.get(token_id)
        if not isinstance(lock, dict):
            errors.append(f"staking loop missing Soft7 #{token_id}")
            continue
        got = lock.get("lock") or {}
        if lock.get("card") != card or got.get("symbol") != symbol or got.get("address") != address:
            errors.append(f"Soft7 #{token_id} must be the {card} card locking {symbol} at {address}")
        meta_path = META_DIR / f"{token_id}.json"
        try:
            meta = json.loads(meta_path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{meta_path.name} unreadable: {exc}")
            continue
        if _trait(meta, "Card") != card_trait or _trait(meta, "Lock") != symbol:
            errors.append(f"meta/{token_id}.json card/lock traits must be {card_trait} / {symbol}")
        if _trait(meta, "Lock Contract") != address:
            errors.append(f"meta/{token_id}.json Lock Contract must be {address}")
        if _trait(meta, "Burn") != "Soft7 treasury" or _trait(meta, "Rewards") != "USDG + SpaceX":
            errors.append(f"meta/{token_id}.json must burn to treasury and reward USDG + SpaceX")
        if address not in meta.get("description", ""):
            errors.append(f"meta/{token_id}.json description must name the lock contract")

    if LANDING.is_file():
        html = LANDING.read_text()
        required = [
            "0x387fbf7128868093D5E22A5528A5fC3D2BA8c9f5",
            "0x316C19b923B19E57A281996bfb9f8e96b2DA6427",
            "0x6B0E22d322c967DFBDB57D027cE53D1D32F7711A",
            "0x5fc5360D0400a0Fd4f2af552ADD042D716F1d168",
            "0x4a0E65A3EcceC6dBe60AE065F2e7bb85Fae35eEa",
            'id="staking-loop"',
            "locks FOX",
            "locks tigerwillca",
            "burn to the Soft7 treasury",
            "Rewards route to USDG and SpaceX",
        ]
        for needle in required:
            if needle not in html:
                errors.append(f"index.html staking loop missing {needle!r}")
    else:
        errors.append("index.html is missing")
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

    loop_errors = validate_staking_loop()
    if loop_errors:
        total_errors += len(loop_errors)
        print("FAIL staking-loop.json")
        for err in loop_errors:
            print(f"     - {err}")
    else:
        print("OK   staking-loop.json  (fox locks FOX, tiger locks TIGER, burn treasury, rewards USDG+SPCX)")

    print("-" * 60)
    if total_errors:
        print(f"FAILED: {total_errors} problem(s) across {len(files)} file(s)")
        return 1
    print(f"PASSED: {len(files)} metadata file(s) validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
