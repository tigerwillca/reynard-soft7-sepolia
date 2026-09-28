#!/usr/bin/env python3
"""In-house Soft7 staking.

Every card 1–7 is staked by existing in this project. Rewards come from the
treasury slice of a secondary sale. Weight is time held. Selling cracks the
mask: unpaid rewards return to the treasury, the hold resets, and the card
earns less until a full quarter of holding heals it.

No Anvil. No third-party staking protocol. Pulse, Project X, and Soft7 feed
one another and book every leg into the same treasury.
"""
from __future__ import annotations

FEE_BPS = 750
CREATOR_OF_FEE_BPS = 8_000
BPS = 10_000
SUPPLY = 7
DEFAULT_QUARTER = 90 * 24 * 60 * 60
LOOP = ("pulse", "project-x", "soft7")
TREASURY = "0x6B0E22d322c967DFBDB57D027cE53D1D32F7711A"


def slice_sale(sale_wei: int) -> dict[str, int]:
    """Split a secondary sale the way the royalty router does.

    Creator receives ``fee * 8000 / 10000``. The treasury keeps the rest of
    the 7.5% fee, including dust. That remainder is 1.5% of the sale when the
    fee divides evenly.
    """
    if sale_wei < 0:
        raise ValueError("sale_wei must be >= 0")
    fee = sale_wei * FEE_BPS // BPS
    creator = fee * CREATOR_OF_FEE_BPS // BPS
    treasury = fee - creator
    return {"fee": fee, "creator": creator, "treasury": treasury}


class TokenStake:
    def __init__(self, token_id: int, holder: str, held_since: int) -> None:
        self.token_id = token_id
        self.holder = holder
        self.held_since = held_since
        self.mask = "whole"
        self.pending = 0


class StakeBook:
    """Seven in-project stakes drawing on one treasury balance."""

    def __init__(
        self,
        now: int,
        holders: dict[int, str],
        quarter: int = DEFAULT_QUARTER,
    ) -> None:
        if quarter <= 0:
            raise ValueError("quarter must be > 0")
        if set(holders) != set(range(1, SUPPLY + 1)):
            raise ValueError("holders must cover tokens 1..7")
        if any(not holder for holder in holders.values()):
            raise ValueError("holder must be non-empty")
        self.quarter = quarter
        self.now = now
        self.treasury = 0
        self.funded = 0
        self.paid: dict[str, int] = {}
        self.tokens = {
            token_id: TokenStake(token_id, holder, now)
            for token_id, holder in holders.items()
        }

    def _held(self, token: TokenStake, now: int) -> int:
        if now < token.held_since:
            raise ValueError("time went backwards")
        return now - token.held_since

    def _heal(self, token: TokenStake, now: int) -> None:
        if token.mask == "cracked" and self._held(token, now) >= self.quarter:
            token.mask = "whole"

    def weight(self, token_id: int, now: int) -> int:
        """Hold seconds, scaled down while the mask is cracked."""
        token = self.tokens[token_id]
        self._heal(token, now)
        held = self._held(token, now)
        if held == 0:
            return 0
        if token.mask == "cracked":
            multiplier = held * BPS // self.quarter
        else:
            multiplier = BPS
        return held * multiplier // BPS

    def fund(self, amount: int, now: int) -> dict[int, int]:
        """Accrue a treasury-slice deposit onto the seven cards.

        A card with zero weight (just acquired, or still cracked with no
        healed time) takes nothing. Undistributed wei stays in the treasury.
        """
        if amount < 0:
            raise ValueError("amount must be >= 0")
        self.treasury += amount
        self.funded += amount
        weights = {token_id: self.weight(token_id, now) for token_id in self.tokens}
        total = sum(weights.values())
        credited = {token_id: 0 for token_id in self.tokens}
        if amount == 0 or total == 0:
            self.now = now
            return credited
        distributed = 0
        for token_id, card_weight in weights.items():
            share = amount * card_weight // total
            self.tokens[token_id].pending += share
            credited[token_id] = share
            distributed += share
        self.treasury -= distributed
        self.now = now
        return credited

    def sell(self, token_id: int, new_holder: str, now: int) -> int:
        """Leave the stake. The mask cracks and unpaid rewards return."""
        if not new_holder:
            raise ValueError("holder must be non-empty")
        token = self.tokens[token_id]
        self._heal(token, now)
        forfeited = token.pending
        self.treasury += forfeited
        token.pending = 0
        token.holder = new_holder
        token.held_since = now
        token.mask = "cracked"
        self.now = now
        return forfeited

    def claim(self, holder: str, now: int) -> int:
        paid = 0
        for token in self.tokens.values():
            self._heal(token, now)
            if token.holder == holder and token.pending:
                paid += token.pending
                token.pending = 0
        if paid:
            self.paid[holder] = self.paid.get(holder, 0) + paid
        self.now = now
        return paid

    def conserved(self) -> bool:
        pending = sum(token.pending for token in self.tokens.values())
        paid = sum(self.paid.values())
        return self.treasury + pending + paid == self.funded


class TreasuryLoop:
    """Pulse feeds Project X, Project X feeds Soft7, Soft7 feeds Pulse.

    Each leg is booked into one treasury. Nothing is split across three pots.
    """

    def __init__(self, address: str = TREASURY) -> None:
        if not address:
            raise ValueError("treasury address required")
        self.address = address
        self.balance = 0
        self.legs: list[tuple[str, str, int]] = []

    @staticmethod
    def next_project(project: str) -> str:
        try:
            index = LOOP.index(project)
        except ValueError as exc:
            raise ValueError(f"unknown project {project}") from exc
        return LOOP[(index + 1) % len(LOOP)]

    def feed(self, project: str, amount: int) -> str:
        if amount <= 0:
            raise ValueError("amount must be > 0")
        dest = self.next_project(project)
        self.balance += amount
        self.legs.append((project, dest, amount))
        return dest

    def draw(self) -> int:
        """Hand the shared balance to staking. The treasury is empty after."""
        amount = self.balance
        self.balance = 0
        return amount
