#!/usr/bin/env python3
"""Local end-to-end Soft7 pipeline.

The Robinhood Chain contracts already do two steps:

* Soft7RoyaltyRouter ``0x64c00a1c2d354F66aD5660548098F7cA25CEeb38`` keeps 80% of
  each royalty for the creator and forwards 20% (the dividend slice, 1.5% of
  the sale) to the giveback vault.
* The vault ``0x6B0E22d322c967DFBDB57D027cE53D1D32F7711A`` pays that slice
  pro-rata to the seven card holders once a quarter (``QUARTER_SECONDS`` =
  7_776_000). Share math matches ``previewDistribution(uint256)``: each card
  gets ``amount // 7``, and the remainder goes to the last distinct holder.

Three links are not on that mainnet path, so a full loop cannot run there:

* supply is already 7, so a test mint reverts
* nothing stakes a card
* the vault pays holders in ETH; it does not route a staked card to USDG and
  SpaceX (SPCX)

This module is the loop those links were missing. It does not send mainnet
transactions. ``fetch_live_distribution`` reads the vault so the share math
can be checked against chain state.
"""
from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass, field

SOFT7_SUPPLY = 7
QUARTER_SECONDS = 7_776_000  # 90 days, vault QUARTER_SECONDS()
FEE_BPS = 750  # 7.5% secondary creator fee
CREATOR_BPS = 8_000
VAULT_BPS = 2_000
DENOMINATOR = 10_000
# Even split of a staked card's dividend. The live contracts publish no other
# USDG/SPCX weight; both destinations are named, so neither is preferred.
USDG_BPS = 5_000
SPCX_BPS = 5_000

# Robinhood Chain mainnet (chain id 4663).
RPC_URL = "https://rpc.mainnet.chain.robinhood.com"
SOFT7_NFT = "0x73D7b2611509C14078e16f572bE5aC7D91879DC2"
ROYALTY_ROUTER = "0x64c00a1c2d354F66aD5660548098F7cA25CEeb38"
GIVEBACK_VAULT = "0x6B0E22d322c967DFBDB57D027cE53D1D32F7711A"
CREATOR = "0xe53bdb2118585d5b2cd06a117d3a036afa70677a"
USDG = "0x5fc5360D0400a0Fd4f2af552ADD042D716F1d168"  # Global Dollar
SPCX = "0x84F72719DCd75b5289fD2316bD51f5140965A476"  # SPACE EXPLORATION TECHNOLOGIES CORP

# previewDistribution(uint256), ownerOf(uint256), distribute()
_PREVIEW = "0xc318ef12"
_OWNER_OF = "0x6352211e"
_DISTRIBUTE = "0xe4fc6b6d"


class PipelineError(Exception):
    """A Soft7 pipeline step refused to run."""


class MaxSupply(PipelineError):
    pass


class NotMinted(PipelineError):
    pass


class NotOwner(PipelineError):
    pass


class AlreadyStaked(PipelineError):
    pass


class TooEarly(PipelineError):
    pass


class NothingToDistribute(PipelineError):
    pass


class SupplyNotFull(PipelineError):
    pass


class RouteMissed(PipelineError):
    pass


def _norm(address: str) -> str:
    text = address.strip().lower()
    if not text.startswith("0x") or len(text) != 42:
        raise PipelineError(f"not an address: {address}")
    return text


def holder_payouts(owners: list[str], amount: int) -> list[tuple[str, int]]:
    """Return ``(holder, wei)`` in first-seen order, matching the live vault.

    ``owners`` is token 1 through token 7. Each token is worth ``amount // 7``.
    ``amount % 7`` is added to the last holder that appears in that walk.
    """
    if len(owners) != SOFT7_SUPPLY:
        raise PipelineError(f"expected {SOFT7_SUPPLY} owners, got {len(owners)}")
    if amount < 0:
        raise PipelineError("amount must be non-negative")

    seen: list[str] = []
    weights: dict[str, int] = {}
    for owner in owners:
        key = _norm(owner)
        if key not in weights:
            seen.append(key)
            weights[key] = 0
        weights[key] += 1

    base = amount // SOFT7_SUPPLY
    payouts = {holder: weights[holder] * base for holder in seen}
    if seen:
        payouts[seen[-1]] += amount % SOFT7_SUPPLY
    return [(holder, payouts[holder]) for holder in seen]


def royalty_split(sale_price: int) -> tuple[int, int, int]:
    """Return ``(fee, creator_wei, vault_wei)`` for a secondary sale.

    The fee is 7.5% of the sale. The router pays the creator
    ``fee * 8000 / 10000`` and the vault receives whatever remains, which is
    the on-chain 20% dividend slice including rounding dust.
    """
    if sale_price < 0:
        raise PipelineError("sale price must be non-negative")
    fee = sale_price * FEE_BPS // DENOMINATOR
    creator = fee * CREATOR_BPS // DENOMINATOR
    vault = fee - creator
    return fee, creator, vault


def route_staked_payout(staked_wei: int) -> tuple[int, int]:
    """Split a staked card's dividend between USDG and SpaceX.

    USDG takes ``USDG_BPS`` of the wei. SpaceX takes the rest, so the two
    legs sum to ``staked_wei``. A 1-wei payout cannot reach both sinks.
    """
    if staked_wei < 0:
        raise PipelineError("staked payout must be non-negative")
    usdg = staked_wei * USDG_BPS // DENOMINATOR
    spacex = staked_wei - usdg
    return usdg, spacex


@dataclass
class LoopReport:
    token_id: int
    staker: str
    sale_price: int
    fee: int
    creator_wei: int
    vault_wei: int
    staker_share: int
    usdg_wei: int
    spacex_wei: int
    holder_eth: dict[str, int]
    next_distribute_at: int

    def lines(self) -> list[str]:
        return [
            f"minted test token #{self.token_id} to {self.staker}",
            f"dividend slice of sale {self.sale_price}: fee {self.fee} -> creator {self.creator_wei}, vault {self.vault_wei}",
            f"staked card #{self.token_id}",
            f"treasury payout of staker share {self.staker_share} -> USDG {self.usdg_wei} ({USDG}), SpaceX {self.spacex_wei} ({SPCX})",
            f"holder ETH not routed: {self.holder_eth}",
            f"next distribute at {self.next_distribute_at}",
        ]


@dataclass
class Soft7Pipeline:
    """In-memory Soft7 mint, dividend slice, stake, and treasury route."""

    now: int = 0
    next_distribute_at: int = 0
    vault_balance: int = 0
    creator_balance: int = 0
    owners: dict[int, str] = field(default_factory=dict)
    staked: dict[int, str] = field(default_factory=dict)
    holder_eth: dict[str, int] = field(default_factory=dict)
    routed: dict[str, int] = field(default_factory=lambda: {_norm(USDG): 0, _norm(SPCX): 0})

    def mint_test_token(self, to: str) -> int:
        """Mint the next card id in ``1..7`` to ``to``.

        The mainnet collection is already full (``MAX_SUPPLY`` is 7 and the
        constructor minted them). This is the test mint that path cannot do.
        """
        if len(self.owners) >= SOFT7_SUPPLY:
            raise MaxSupply("Soft7 supply is 7")
        token_id = len(self.owners) + 1
        self.owners[token_id] = _norm(to)
        return token_id

    def trigger_dividend_slice(self, sale_price: int) -> int:
        """Take the 7.5% fee and drop the vault's 20% into the dividend balance.

        Returns the wei credited to the vault. Does not pay holders; staking
        still has to happen before the treasury route.
        """
        _fee, creator, vault = royalty_split(sale_price)
        self.creator_balance += creator
        self.vault_balance += vault
        return vault

    def stake_card(self, token_id: int, staker: str) -> None:
        """Lock ``token_id`` to ``staker``. Only the current owner can stake."""
        owner = self.owners.get(token_id)
        if owner is None:
            raise NotMinted(f"token {token_id} is not minted")
        who = _norm(staker)
        if who != owner:
            raise NotOwner(f"{who} does not own token {token_id}")
        if token_id in self.staked:
            raise AlreadyStaked(f"token {token_id} is already staked")
        self.staked[token_id] = who

    def route_treasury_payout(self) -> tuple[int, int]:
        """Pay the vault balance. Staked cards route to USDG and SpaceX.

        Unstaked cards are paid to their holder in ETH, which is what the live
        vault does for every card. Returns ``(usdg_wei, spacex_wei)`` credited
        by this call.
        """
        if len(self.owners) != SOFT7_SUPPLY:
            raise SupplyNotFull(f"{len(self.owners)} of {SOFT7_SUPPLY} cards are minted")
        if self.now < self.next_distribute_at:
            raise TooEarly(f"next distribute at {self.next_distribute_at}, now {self.now}")
        amount = self.vault_balance
        if amount == 0:
            raise NothingToDistribute("vault balance is 0")

        owners = [self.owners[token_id] for token_id in range(1, SOFT7_SUPPLY + 1)]
        usdg_total = 0
        spacex_total = 0
        for holder, payout in holder_payouts(owners, amount):
            weight = sum(1 for token_id, owner in self.owners.items() if owner == holder)
            staked_weight = sum(
                1
                for token_id, owner in self.staked.items()
                if owner == holder and self.owners.get(token_id) == holder
            )
            staked_wei = payout * staked_weight // weight
            unstaked_wei = payout - staked_wei
            usdg, spacex = route_staked_payout(staked_wei)
            usdg_total += usdg
            spacex_total += spacex
            if unstaked_wei:
                self.holder_eth[holder] = self.holder_eth.get(holder, 0) + unstaked_wei

        self.routed[_norm(USDG)] += usdg_total
        self.routed[_norm(SPCX)] += spacex_total
        self.vault_balance = 0
        self.next_distribute_at = self.now + QUARTER_SECONDS
        return usdg_total, spacex_total

    def run(self, staker: str, sale_price: int, other_holders: list[str]) -> LoopReport:
        """Mint a test card, slice a sale, stake that card, and route its payout.

        ``other_holders`` must contain 6 addresses. They receive cards 2–7 so
        the dividend still divides across the live supply of 7.
        """
        if len(other_holders) != SOFT7_SUPPLY - 1:
            raise PipelineError(f"need {SOFT7_SUPPLY - 1} other holders")
        if sale_price <= 0:
            raise PipelineError("sale price must be positive")

        token_id = self.mint_test_token(staker)
        for holder in other_holders:
            self.mint_test_token(holder)
        vault_wei = self.trigger_dividend_slice(sale_price)
        self.stake_card(token_id, staker)
        usdg_wei, spacex_wei = self.route_treasury_payout()
        if usdg_wei <= 0 or spacex_wei <= 0:
            raise RouteMissed(
                f"staked payout did not reach both sinks (USDG {usdg_wei}, SpaceX {spacex_wei})"
            )

        fee, creator_wei, _vault = royalty_split(sale_price)
        owners = [self.owners[i] for i in range(1, SOFT7_SUPPLY + 1)]
        staker_share = dict(holder_payouts(owners, vault_wei))[_norm(staker)]
        return LoopReport(
            token_id=token_id,
            staker=_norm(staker),
            sale_price=sale_price,
            fee=fee,
            creator_wei=creator_wei,
            vault_wei=vault_wei,
            staker_share=staker_share,
            usdg_wei=usdg_wei,
            spacex_wei=spacex_wei,
            holder_eth=dict(self.holder_eth),
            next_distribute_at=self.next_distribute_at,
        )


def _rpc(method: str, params: list) -> dict:
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    request = urllib.request.Request(
        RPC_URL,
        data=body,
        headers={
            "content-type": "application/json",
            "User-Agent": "Mozilla/5.0",
            "origin": "https://robinhoodchain.blockscout.com",
        },
    )
    with urllib.request.urlopen(request, timeout=40) as response:
        payload = json.load(response)
    if "error" in payload:
        raise PipelineError(str(payload["error"]))
    return payload


def _decode_address_amount_pairs(data: str) -> list[tuple[str, int]]:
    raw = bytes.fromhex(data[2:])
    off0 = int.from_bytes(raw[0:32], "big")
    off1 = int.from_bytes(raw[32:64], "big")

    def words(offset: int) -> list[bytes]:
        count = int.from_bytes(raw[offset : offset + 32], "big")
        return [
            raw[offset + 32 + i * 32 : offset + 64 + i * 32]
            for i in range(count)
        ]

    holders = ["0x" + word[-20:].hex() for word in words(off0)]
    amounts = [int.from_bytes(word, "big") for word in words(off1)]
    if len(holders) != len(amounts):
        raise PipelineError("previewDistribution returned uneven arrays")
    return list(zip(holders, amounts))


def fetch_live_distribution(amount: int) -> list[tuple[str, int]]:
    """Read ``previewDistribution(amount)`` from the mainnet giveback vault."""
    data = _PREVIEW + amount.to_bytes(32, "big").hex()
    result = _rpc("eth_call", [{"to": GIVEBACK_VAULT, "data": data}, "latest"])["result"]
    return _decode_address_amount_pairs(result)


def fetch_live_owners() -> list[str]:
    """Return ``ownerOf(1)`` … ``ownerOf(7)`` from the mainnet Soft7 NFT."""
    owners = []
    for token_id in range(1, SOFT7_SUPPLY + 1):
        data = _OWNER_OF + token_id.to_bytes(32, "big").hex()
        result = _rpc("eth_call", [{"to": SOFT7_NFT, "data": data}, "latest"])["result"]
        owners.append("0x" + result[-40:])
    return owners


def live_distribute_revert() -> str:
    """Return the error string from a mainnet ``distribute()`` eth_call.

    The deployed vault reverts until the quarter elapses and the balance is
    non-zero. This call does not send a transaction.
    """
    request = urllib.request.Request(
        RPC_URL,
        data=json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "eth_call",
                "params": [{"to": GIVEBACK_VAULT, "data": _DISTRIBUTE}, "latest"],
            }
        ).encode(),
        headers={
            "content-type": "application/json",
            "User-Agent": "Mozilla/5.0",
            "origin": "https://robinhoodchain.blockscout.com",
        },
    )
    with urllib.request.urlopen(request, timeout=40) as response:
        payload = json.load(response)
    if "error" not in payload:
        raise PipelineError(f"distribute() did not revert: {payload}")
    return str(payload["error"])


def main() -> int:
    staker = "0x0000000000000000000000000000000000000001"
    others = [f"0x000000000000000000000000000000000000000{i}" for i in range(2, 8)]
    report = Soft7Pipeline().run(staker, 10**18, others)
    print("Soft7 pipeline loop")
    for line in report.lines():
        print(f"  {line}")
    print("  loop clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
