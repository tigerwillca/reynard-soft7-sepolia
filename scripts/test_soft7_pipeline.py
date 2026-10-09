#!/usr/bin/env python3
"""End-to-end checks for the Soft7 mint, dividend, stake, and treasury route."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from soft7_pipeline import (
    SPCX,
    USDG,
    AlreadyStaked,
    MaxSupply,
    NothingToDistribute,
    NotOwner,
    Soft7Pipeline,
    TooEarly,
    fetch_live_distribution,
    fetch_live_owners,
    holder_payouts,
    live_distribute_revert,
    royalty_split,
)

SALE = 10**18
STAKER = "0x0000000000000000000000000000000000000001"
OTHERS = [f"0x000000000000000000000000000000000000000{i}" for i in range(2, 8)]


class PipelineLoopTest(unittest.TestCase):
    def test_full_loop_routes_staked_card_to_usdg_and_spacex(self) -> None:
        pipeline = Soft7Pipeline()
        report = pipeline.run(STAKER, SALE, OTHERS)

        self.assertEqual(report.token_id, 1)
        self.assertEqual(report.staker, STAKER)
        fee, creator, vault = royalty_split(SALE)
        self.assertEqual((report.fee, report.creator_wei, report.vault_wei), (fee, creator, vault))
        self.assertEqual(fee, 75_000_000_000_000_000)
        self.assertEqual(creator, 60_000_000_000_000_000)
        self.assertEqual(vault, 15_000_000_000_000_000)
        self.assertEqual(creator + vault, fee)
        self.assertEqual(pipeline.creator_balance, creator)
        self.assertEqual(pipeline.vault_balance, 0)

        share = vault // 7
        self.assertEqual(report.staker_share, share)
        self.assertEqual(report.usdg_wei + report.spacex_wei, share)
        self.assertGreater(report.usdg_wei, 0)
        self.assertGreater(report.spacex_wei, 0)
        self.assertEqual(report.usdg_wei, share // 2)
        self.assertEqual(pipeline.routed[USDG.lower()], report.usdg_wei)
        self.assertEqual(pipeline.routed[SPCX.lower()], report.spacex_wei)

        holder_sum = sum(report.holder_eth.values())
        self.assertEqual(holder_sum + report.usdg_wei + report.spacex_wei, vault)
        self.assertNotIn(STAKER, report.holder_eth)
        self.assertEqual(len(report.holder_eth), 6)
        self.assertEqual(report.next_distribute_at, 7_776_000)

    def test_unstaked_card_is_not_routed(self) -> None:
        pipeline = Soft7Pipeline()
        pipeline.mint_test_token(STAKER)
        for holder in OTHERS:
            pipeline.mint_test_token(holder)
        pipeline.trigger_dividend_slice(SALE)
        usdg, spacex = pipeline.route_treasury_payout()
        self.assertEqual((usdg, spacex), (0, 0))
        self.assertEqual(sum(pipeline.holder_eth.values()), royalty_split(SALE)[2])

    def test_second_payout_waits_for_the_quarter(self) -> None:
        pipeline = Soft7Pipeline()
        pipeline.run(STAKER, SALE, OTHERS)
        pipeline.trigger_dividend_slice(SALE)
        with self.assertRaises(TooEarly):
            pipeline.route_treasury_payout()
        pipeline.now = pipeline.next_distribute_at
        usdg, spacex = pipeline.route_treasury_payout()
        self.assertGreater(usdg, 0)
        self.assertGreater(spacex, 0)

    def test_empty_vault_and_closed_mint(self) -> None:
        pipeline = Soft7Pipeline()
        token_id = pipeline.mint_test_token(STAKER)
        for holder in OTHERS:
            pipeline.mint_test_token(holder)
        with self.assertRaises(MaxSupply):
            pipeline.mint_test_token(STAKER)
        with self.assertRaises(NothingToDistribute):
            pipeline.route_treasury_payout()
        with self.assertRaises(NotOwner):
            pipeline.stake_card(token_id, OTHERS[0])
        pipeline.stake_card(token_id, STAKER)
        with self.assertRaises(AlreadyStaked):
            pipeline.stake_card(token_id, STAKER)

    def test_duplicate_holder_remainder_matches_live_vectors(self) -> None:
        owners = [
            "0x7c440909184ff4b45d96175ecccde4bd21901ab1",
            "0xd84e69fa5a0975da11edc9a9721cf893f7784bc6",
            "0x49c1408183749be16d3373a001ffb217b8e599d6",
            "0xd8da6bf26964af9d7eed9e03e53415d37aa96045",
            "0x8d00cae604984076a09218b854686549663fb427",
            "0x76443f52feb3561aaa71a01300602eb0b052bd45",
            "0x7c440909184ff4b45d96175ecccde4bd21901ab1",
        ]
        self.assertEqual(
            holder_payouts(owners, 100),
            [
                (owners[0], 28),
                (owners[1], 14),
                (owners[2], 14),
                (owners[3], 14),
                (owners[4], 14),
                (owners[5], 16),
            ],
        )
        self.assertEqual(holder_payouts(owners, 1)[-1], (owners[5], 1))
        one_eth = holder_payouts(owners, 10**18)
        self.assertEqual(one_eth[0][1], 285_714_285_714_285_714)
        self.assertEqual(one_eth[-1][1], 142_857_142_857_142_858)
        self.assertEqual(sum(amount for _holder, amount in one_eth), 10**18)


class LiveVaultTest(unittest.TestCase):
    def test_local_math_matches_mainnet_preview(self) -> None:
        owners = fetch_live_owners()
        self.assertEqual(len(owners), 7)
        for amount in (1, 7, 100, 7_776_000, 10**18):
            live = [(holder.lower(), wei) for holder, wei in fetch_live_distribution(amount)]
            self.assertEqual(holder_payouts(owners, amount), live)

    def test_mainnet_distribute_is_still_blocked(self) -> None:
        # The deployed vault has a zero balance and nextDistributeAt in the future.
        # eth_call must revert. No transaction is sent.
        error = live_distribute_revert()
        self.assertIn("execution reverted", error.lower())


if __name__ == "__main__":
    unittest.main()
