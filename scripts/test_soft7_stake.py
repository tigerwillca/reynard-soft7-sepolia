#!/usr/bin/env python3
"""Rules for in-house Soft7 staking, and the landing that states them."""
from __future__ import annotations

import unittest
from pathlib import Path

from soft7_stake import (
    BPS,
    LOOP,
    SUPPLY,
    TREASURY,
    StakeBook,
    TreasuryLoop,
    slice_sale,
)

ROOT = Path(__file__).resolve().parent.parent
QUARTER = 1_000


def book_at(now: int, holder: str = "alice") -> StakeBook:
    return StakeBook(now, {token_id: holder for token_id in range(1, SUPPLY + 1)}, quarter=QUARTER)


class SliceTests(unittest.TestCase):
    def test_even_sale_is_seven_and_a_half_then_twenty_percent(self) -> None:
        # 1 ETH. Fee 0.075. Creator 80% = 0.06. Treasury 0.015.
        parts = slice_sale(10**18)
        self.assertEqual(parts["fee"], 75 * 10**15)
        self.assertEqual(parts["creator"], 60 * 10**15)
        self.assertEqual(parts["treasury"], 15 * 10**15)

    def test_dust_stays_with_the_treasury(self) -> None:
        parts = slice_sale(1)
        self.assertEqual(parts["fee"], 0)
        parts = slice_sale(10_000)
        self.assertEqual(parts["fee"], 750)
        self.assertEqual(parts["creator"], 600)
        self.assertEqual(parts["treasury"], 150)
        parts = slice_sale(10_001)
        self.assertEqual(parts["fee"], 750)
        self.assertEqual(parts["creator"] + parts["treasury"], parts["fee"])
        self.assertGreaterEqual(parts["treasury"], parts["fee"] - parts["fee"] * 8_000 // BPS)


class StakeTests(unittest.TestCase):
    def test_longer_hold_earns_more(self) -> None:
        book = StakeBook(
            0,
            {1: "alice", 2: "bob", 3: "c", 4: "d", 5: "e", 6: "f", 7: "g"},
            quarter=QUARTER,
        )
        # Cards 3–7 are acquired at the funding instant, so their weight is 0.
        for token_id in range(3, 8):
            book.tokens[token_id].held_since = 400
        book.tokens[1].held_since = 100
        book.tokens[2].held_since = 300
        credited = book.fund(400, 400)
        self.assertEqual(credited[1], 300)
        self.assertEqual(credited[2], 100)
        self.assertEqual(sum(credited[token_id] for token_id in range(3, 8)), 0)
        self.assertTrue(book.conserved())

    def test_zero_weight_leaves_the_slice_in_the_treasury(self) -> None:
        book = book_at(0)
        credited = book.fund(700, 0)
        self.assertEqual(sum(credited.values()), 0)
        self.assertEqual(book.treasury, 700)
        self.assertTrue(book.conserved())

    def test_equal_holds_split_the_slice_and_keep_dust(self) -> None:
        book = book_at(0)
        credited = book.fund(10, 100)
        self.assertEqual(set(credited.values()), {1})
        self.assertEqual(sum(credited.values()), 7)
        self.assertEqual(book.treasury, 3)
        self.assertTrue(book.conserved())

    def test_sale_cracks_the_mask_and_returns_pending(self) -> None:
        book = book_at(0)
        book.fund(700, 100)
        self.assertEqual(book.tokens[1].pending, 100)
        forfeited = book.sell(1, "carol", 100)
        self.assertEqual(forfeited, 100)
        token = book.tokens[1]
        self.assertEqual(token.holder, "carol")
        self.assertEqual(token.mask, "cracked")
        self.assertEqual(token.held_since, 100)
        self.assertEqual(token.pending, 0)
        self.assertGreaterEqual(book.treasury, 100)
        self.assertEqual(book.weight(1, 100), 0)
        self.assertTrue(book.conserved())

    def test_cracked_mask_earns_less_than_a_whole_mask(self) -> None:
        book = book_at(0)
        book.sell(1, "carol", 0)
        whole = book.weight(2, QUARTER // 2)
        cracked = book.weight(1, QUARTER // 2)
        self.assertEqual(whole, QUARTER // 2)
        self.assertEqual(cracked, whole // 2)
        self.assertLess(cracked, whole)

    def test_a_quarter_of_holding_heals_the_mask(self) -> None:
        book = book_at(0)
        book.sell(1, "carol", 0)
        self.assertEqual(book.tokens[1].mask, "cracked")
        healed = book.weight(1, QUARTER)
        self.assertEqual(book.tokens[1].mask, "whole")
        self.assertEqual(healed, QUARTER)

    def test_claim_pays_the_holder_and_keeps_the_books(self) -> None:
        book = book_at(0, holder="alice")
        book.fund(700, 70)
        paid = book.claim("alice", 70)
        self.assertEqual(paid, 700)
        self.assertEqual(book.claim("alice", 80), 0)
        self.assertEqual(book.paid["alice"], 700)
        self.assertTrue(all(token.pending == 0 for token in book.tokens.values()))
        self.assertTrue(book.conserved())

    def test_sale_after_a_heal_still_cracks(self) -> None:
        book = book_at(0)
        book.fund(700, QUARTER)
        book.sell(4, "dave", QUARTER)
        self.assertEqual(book.tokens[4].mask, "cracked")
        self.assertEqual(book.tokens[4].pending, 0)
        self.assertTrue(book.conserved())


class LoopTests(unittest.TestCase):
    def test_three_projects_one_treasury(self) -> None:
        loop = TreasuryLoop()
        self.assertEqual(loop.address, TREASURY)
        self.assertEqual(loop.feed("pulse", 10), "project-x")
        self.assertEqual(loop.feed("project-x", 20), "soft7")
        self.assertEqual(loop.feed("soft7", 30), "pulse")
        self.assertEqual(loop.legs, [
            ("pulse", "project-x", 10),
            ("project-x", "soft7", 20),
            ("soft7", "pulse", 30),
        ])
        self.assertEqual(loop.balance, 60)
        self.assertEqual(LOOP, ("pulse", "project-x", "soft7"))

    def test_a_full_cycle_funds_the_stake(self) -> None:
        loop = TreasuryLoop()
        loop.feed("pulse", 300)
        loop.feed("project-x", 200)
        loop.feed("soft7", 200)
        book = book_at(0)
        credited = book.fund(loop.draw(), 100)
        self.assertEqual(loop.balance, 0)
        self.assertEqual(sum(credited.values()), 700)
        self.assertTrue(book.conserved())

    def test_unknown_project_and_empty_feed_fail(self) -> None:
        loop = TreasuryLoop()
        with self.assertRaises(ValueError):
            loop.feed("anvil", 1)
        with self.assertRaises(ValueError):
            loop.feed("pulse", 0)


class LandingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.page = (ROOT / "index.html").read_text()
        cls.brief = (ROOT / "docs" / "BRIEF.md").read_text()

    def test_brief_records_the_stake_and_the_loop(self) -> None:
        text = self.brief.lower()
        self.assertIn("no anvil", text)
        self.assertIn("no third-party", text)
        self.assertIn("treasury slice", text)
        self.assertIn("longer", text)
        self.assertIn("mask cracks", text)
        self.assertIn("pulse", text)
        self.assertIn("project x", text)
        self.assertIn("soft7", text)
        self.assertIn("one treasury", text)

    def test_landing_has_motion_behind_the_hero(self) -> None:
        page = self.page
        self.assertIn('class="banner"', page)
        self.assertIn("phoenix-banner.gif", page)
        self.assertIn("soft7-bg-loop.webm", page)
        self.assertIn("soft7-bg-loop.mp4", page)
        self.assertIn("mask-depth-reynard/hero.webp", page)
        self.assertIn("#07050f", page)
        self.assertTrue((ROOT / "phoenix-banner.gif").is_file())
        self.assertTrue((ROOT / "mask-depth-reynard" / "hero.webp").is_file())
        self.assertTrue((ROOT / "soft7-bg-loop.mp4").is_file())

    def test_landing_shows_cards_mint_staking_and_dividend(self) -> None:
        page = self.page
        for art in ("033.jpg", "034.jpg", "035.jpg", "036.jpg", "037.jpg", "038.jpg", "039.jpg"):
            self.assertIn(art, page)
        self.assertIn(">Mint<", page)
        self.assertIn("https://opensea.io/collection/reynard-soft7", page)
        self.assertIn('id="staking"', page)
        self.assertIn('id="dividend"', page)
        self.assertIn('id="the-seven"', page)
        self.assertIn('id="loop"', page)
        self.assertIn("1.5%", page)
        self.assertIn("Quarterly", page)
        self.assertIn(TREASURY, page)
        lowered = page.lower()
        self.assertIn("mask cracks", lowered)
        self.assertIn("pulse", lowered)
        self.assertIn("project x", lowered)
        self.assertIn("one treasury", lowered)


if __name__ == "__main__":
    unittest.main()
