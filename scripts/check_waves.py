#!/usr/bin/env python3
"""Integer checks for the wave cap and the 10% stake dividend.

Mirrors Soft7MascotCards. Does not touch a chain.
"""
from __future__ import annotations

SCALE = 10**18
PAYOUT = "77a"


def wave_cap(weeks_elapsed: int) -> int:
    cap = 7 + weeks_elapsed * 77
    return 777 if cap > 777 else cap


class Pool:
    def __init__(self) -> None:
        self.total = 0
        self.acc = 0
        self.count: dict[str, int] = {}
        self.debt: dict[str, int] = {}
        self.accrued: dict[str, int] = {}
        self.paid = {PAYOUT: 0, "a": 0, "b": 0}

    def settle(self, holder: str) -> None:
        count = self.count.get(holder, 0)
        extra = count * self.acc // SCALE
        debt = self.debt.get(holder, 0)
        if extra > debt:
            self.accrued[holder] = self.accrued.get(holder, 0) + (extra - debt)
        self.debt[holder] = count * self.acc // SCALE

    def stake(self, holder: str) -> None:
        self.settle(holder)
        self.count[holder] = self.count.get(holder, 0) + 1
        self.total += 1
        self.debt[holder] = self.count[holder] * self.acc // SCALE

    def dividend(self, value: int) -> None:
        cut = value // 10
        self.paid[PAYOUT] = self.paid.get(PAYOUT, 0) + (value - cut)
        if cut == 0:
            return
        if self.total == 0:
            self.paid[PAYOUT] += cut
            return
        self.acc += cut * SCALE // self.total

    def pull(self, holder: str) -> int:
        self.settle(holder)
        amount = self.accrued.get(holder, 0)
        self.accrued[holder] = 0
        self.paid[holder] = self.paid.get(holder, 0) + amount
        return amount


def main() -> int:
    assert [wave_cap(w) for w in range(0, 12)] == [
        7, 84, 161, 238, 315, 392, 469, 546, 623, 700, 777, 777
    ]
    pool = Pool()
    pool.dividend(10 * 10**18)  # nobody staked: 100% to the 77a wallet
    assert pool.paid[PAYOUT] == 10 * 10**18

    pool.stake("a")
    pool.dividend(10 * 10**18)  # 1 ETH accrues to the only staker
    assert pool.pull("a") == 10**18

    pool.stake("b")
    pool.dividend(10 * 10**18)  # 1 ETH split across two staked cards
    assert pool.pull("a") == 10**18 // 2
    assert pool.pull("b") == 10**18 // 2
    print("PASSED: wave cap hits 777 on week 10, dividend splits with stake weight")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
