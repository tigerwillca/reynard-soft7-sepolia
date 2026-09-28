#!/usr/bin/env python3
"""Print setBaseURI calldata for the live Soft7 contract.

Does not broadcast a transaction. The owner sends this only after the proof
PNGs are approved. The base must end in a slash and must be a directory of
JSON files whose image fields are one PNG or GIF each.
"""
from __future__ import annotations

import sys

from Crypto.Hash import keccak

SELECTOR_SIG = "setBaseURI(string)"
LIVE = "0x73D7b2611509C14078e16f572bE5aC7D91879DC2"


def selector() -> str:
    digest = keccak.new(digest_bits=256)
    digest.update(SELECTOR_SIG.encode())
    return digest.hexdigest()[:8]


def encode(base: str) -> str:
    if not base.endswith("/"):
        raise SystemExit("base URI must end with /")
    raw = base.encode()
    # head: offset 0x20, then length, then padded bytes
    body = raw.hex()
    if len(body) % 64:
        body = body.ljust(((len(body) + 63) // 64) * 64, "0")
    return "0x" + selector() + f"{0x20:064x}" + f"{len(raw):064x}" + body


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <baseURI>", file=sys.stderr)
        return 2
    data = encode(sys.argv[1])
    print(f"to: {LIVE}")
    print("data:")
    print(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
