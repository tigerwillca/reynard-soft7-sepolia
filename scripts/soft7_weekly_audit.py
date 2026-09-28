#!/usr/bin/env python3
"""Write a short Soft7 on-chain status report.

Reads Robinhood Chain (chain id 4663) over JSON-RPC:

  * SOFT7 total supply and ownerOf(1..supply)
  * holder distribution
  * ETH balances of the NFT, royalty router, and giveback vault
  * royaltyInfo for a 10_000 wei sale (expects 750 / 7.5% to the router)

Failed-transaction counts and historical royalty inflows are not visible from
a plain JSON-RPC node. Pass the figures from a Blockscout review:

    python3 scripts/soft7_weekly_audit.py \\
        --tx-count 12 \\
        --failed-tx-count 0 \\
        --royalty-received-wei 0

The report is written to audits/YYYY-MM-DD.md (UTC).
"""
from __future__ import annotations

import argparse
import json
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

RPC = "https://rpc.mainnet.chain.robinhood.com"
NFT = "0x73D7b2611509C14078e16f572bE5aC7D91879DC2"
ROUTER = "0x64c00a1c2d354F66aD5660548098F7cA25CEeb38"
VAULT = "0x6B0E22d322c967DFBDB57D027cE53D1D32F7711A"
CHAIN_ID = 4663

LABELS = {
    "0x7c440909184ff4b45d96175ecccde4bd21901ab1": "EIP-7702 account",
    "0xd8da6bf26964af9d7eed9e03e53415d37aa96045": "vitalik.eth",
    "0x86df4d2faa9ac25d408aa4e4fb890b9918c5f066": "deployer",
}

REPO_ROOT = Path(__file__).resolve().parent.parent


def rpc(method: str, params: list) -> object:
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    request = urllib.request.Request(
        RPC,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": "soft7-weekly-audit"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    if "error" in payload:
        raise SystemExit(f"RPC {method} failed: {payload['error']}")
    return payload["result"]


def call(to: str, data: str) -> str:
    return str(rpc("eth_call", [{"to": to, "data": data}, "latest"]))


def word_address(word: str) -> str:
    return "0x" + word[-40:]


def checksum(address: str) -> str:
    hexed = address.lower().removeprefix("0x")
    # EIP-55 without an external keccak dependency: compare via the RPC client's
    # mixed-case form when we already stored one, otherwise print lowercase.
    return "0x" + hexed


def wei_to_eth(wei: int) -> str:
    whole, frac = divmod(wei, 10**18)
    return f"{whole}.{frac:018d}".rstrip("0").rstrip(".") or "0"


def collect() -> dict:
    block_hex = str(rpc("eth_blockNumber", []))
    block = int(block_hex, 16)
    header = rpc("eth_getBlockByNumber", [block_hex, False])
    if not isinstance(header, dict):
        header = rpc("eth_getBlockByNumber", ["latest", False])
    if not isinstance(header, dict):
        raise SystemExit("block header missing")
    timestamp = int(header["timestamp"], 16)
    block = int(header["number"], 16)
    chain_id = int(str(rpc("eth_chainId", [])), 16)
    if chain_id != CHAIN_ID:
        raise SystemExit(f"unexpected chain id {chain_id}")

    supply = int(call(NFT, "0x18160ddd"), 16)
    owners = []
    for token_id in range(1, supply + 1):
        data = "0x6352211e" + hex(token_id)[2:].zfill(64)
        owners.append((token_id, checksum(word_address(call(NFT, data)))))

    sale = 10_000
    royalty = call(NFT, "0x2a55205a" + hex(1)[2:].zfill(64) + hex(sale)[2:].zfill(64))
    receiver = checksum(word_address(royalty[0:66]))
    royalty_amount = int(royalty[66:130], 16)

    balances = {
        name: int(str(rpc("eth_getBalance", [addr, "latest"])), 16)
        for name, addr in (("nft", NFT), ("router", ROUTER), ("vault", VAULT))
    }
    return {
        "block": block,
        "timestamp": timestamp,
        "supply": supply,
        "owners": owners,
        "royalty_receiver": receiver,
        "royalty_amount": royalty_amount,
        "sale": sale,
        "balances": balances,
    }


def render(state: dict, args: argparse.Namespace) -> tuple[str, str]:
    when = datetime.fromtimestamp(state["timestamp"], timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    report_day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    grouped: dict[str, list[int]] = defaultdict(list)
    for token_id, owner in state["owners"]:
        grouped[owner].append(token_id)
    supply = state["supply"]
    lines = [
        f"# Soft7 weekly status — {report_day}",
        "",
        f"Chain Robinhood mainnet ({CHAIN_ID}), block {state['block']} ({when}).",
        f"Contract `{NFT}` (Reynard Soft7 / SOFT7).",
        "",
        "## Token count",
        "",
        f"Total supply is **{supply}**. `ownerOf` returns an owner for tokens 1 through {supply}.",
        "",
        "## Holder distribution",
        "",
        "| Holder | Tokens | Count | Share |",
        "| --- | --- | ---: | ---: |",
    ]
    for owner, token_ids in sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0])):
        label = LABELS.get(owner.lower())
        shown = f"`{owner}`" + (f" ({label})" if label else "")
        ids = ", ".join(f"#{token_id}" for token_id in token_ids)
        count = len(token_ids)
        share = (count * 100) / supply if supply else 0
        lines.append(f"| {shown} | {ids} | {count} | {share:.2f}% |")
    lines += [
        "",
        f"{len(grouped)} holders, {supply} tokens.",
        "",
        "## Failed transactions",
        "",
    ]
    if args.tx_count is None or args.failed_tx_count is None:
        lines.append(
            "Blockscout review was not attached to this run, so failed-transaction totals are omitted. "
            "Re-run with `--tx-count` and `--failed-tx-count` after reading the NFT transaction list."
        )
    else:
        lines.append(
            f"Reviewed {args.tx_count} NFT transactions on Blockscout. "
            f"**{args.failed_tx_count}** failed."
        )
    lines += [
        "",
        "## Royalty payments received",
        "",
        f"`royaltyInfo(1, {state['sale']})` pays {state['royalty_amount']} wei "
        f"({state['royalty_amount'] / state['sale'] * 100:.1f}%) to `{state['royalty_receiver']}`.",
        f"Router balance: {wei_to_eth(state['balances']['router'])} ETH.",
        f"Giveback vault balance: {wei_to_eth(state['balances']['vault'])} ETH.",
        f"NFT balance: {wei_to_eth(state['balances']['nft'])} ETH.",
    ]
    if args.royalty_received_wei is None:
        lines.append("Historical royalty inflow was not attached. Balances above are the funds sitting there now.")
    else:
        lines.append(
            f"Royalty payments received (router and vault inflows in this review): "
            f"**{wei_to_eth(args.royalty_received_wei)} ETH**."
        )
    lines += [
        "",
        "Next audit: Sunday 23:00 UTC.",
        "",
    ]
    return report_day, "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Write the Soft7 weekly on-chain status report.")
    parser.add_argument("--tx-count", type=int, default=None)
    parser.add_argument("--failed-tx-count", type=int, default=None)
    parser.add_argument("--royalty-received-wei", type=int, default=None)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    state = collect()
    report_day, body = render(state, args)
    output = args.output or (REPO_ROOT / "audits" / f"{report_day}.md")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(body)
    print(output)


if __name__ == "__main__":
    main()
