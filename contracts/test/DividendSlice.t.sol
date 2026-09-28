// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {DividendSlice} from "../src/DividendSlice.sol";
import {MockSoft7} from "../src/MockSoft7.sol";
import {Soft7Desk} from "../src/Soft7Desk.sol";

interface Vm {
    function deal(address account, uint256 newBalance) external;
    function prank(address msgSender) external;
    function startPrank(address msgSender) external;
    function stopPrank() external;
}

/// @notice Small-amount proof that 10% of a claim and of a mint is paid pro-rata.
contract DividendSliceTest {
    Vm internal constant vm = Vm(address(uint160(uint256(keccak256("hevm cheat code")))));

    // Same distribution as Robinhood Chain Soft7 on 2026-09-28: supply 7, one address holds two.
    address internal constant H2 = 0x7c440909184FF4b45d96175ecCCdE4BD21901ab1;
    address internal constant H1A = 0xd84E69Fa5a0975da11eDc9a9721CF893f7784BC6;
    address internal constant H1B = 0x49C1408183749BE16D3373a001FfB217B8e599d6;
    address internal constant H1C = 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045;
    address internal constant H1D = 0x8D00caE604984076a09218B854686549663Fb427;
    address internal constant H1E = 0x76443F52feb3561aaA71A01300602eB0b052bd45;
    address internal constant CLAIMER = address(0xC1A111);
    address internal constant TREASURY = address(0x777EA5);
    address internal constant NEW_HOLDER = address(0xA11CE);

    DividendSlice internal slice;
    Soft7Desk internal desk;

    function setUp() public {
        MockSoft7 collection = new MockSoft7();
        collection.mint(H2);
        collection.mint(H1A);
        collection.mint(H1B);
        collection.mint(H1C);
        collection.mint(H1D);
        collection.mint(H1E);
        collection.mint(H2);
        slice = new DividendSlice(address(collection), TREASURY);
        desk = new Soft7Desk(slice, collection);
        slice.setDesk(address(desk));
    }

    function test_smallClaimPayoutLands() public {
        uint256 reward = 7_000;
        vm.deal(CLAIMER, reward);
        vm.prank(CLAIMER);
        desk.claimReward{value: reward}();

        assertEq(CLAIMER.balance, 6_300, "claimer keeps 90%");
        assertEq(slice.accrued(H2), 200, "two tokens accrue 200 wei");
        assertEq(slice.accrued(H1A), 100, "one token accrues 100 wei");
        assertEq(slice.accrued(H1C), 100, "vitalik seat accrues 100 wei");
        assertEq(slice.retainedDust(), 0, "7000 wei splits cleanly");

        _withdraw(H2, 200);
        _withdraw(H1A, 100);
        _withdraw(H1B, 100);
        _withdraw(H1C, 100);
        _withdraw(H1D, 100);
        _withdraw(H1E, 100);
        assertEq(address(slice).balance, 0, "slice emptied after payouts");
    }

    function test_smallMintRoutesTenPercentIncludingNewToken() public {
        uint256 price = 8_000;
        vm.deal(address(this), price);
        desk.mint{value: price}(NEW_HOLDER);

        assertEq(TREASURY.balance, 7_200, "treasury keeps 90% of mint");
        assertEq(slice.accrued(NEW_HOLDER), 100, "new token shares the slice");
        assertEq(slice.accrued(H2), 200, "two-token holder share of mint slice");
        assertEq(slice.accrued(H1E), 100, "single-token share of mint slice");

        _withdraw(NEW_HOLDER, 100);
    }

    function test_dustStaysWhenSliceDoesNotDivide() public {
        vm.deal(CLAIMER, 1_000);
        vm.prank(CLAIMER);
        desk.claimReward{value: 1_000}();
        // 10% of 1000 = 100; 100 / 7 = 14 wei per token; 2 wei remain.
        assertEq(slice.accrued(H2), 28, "two tokens get 28 wei");
        assertEq(slice.accrued(H1A), 14, "one token gets 14 wei");
        assertEq(slice.retainedDust(), 2, "remainder stays in the slice");
    }

    function _withdraw(address holder, uint256 expected) internal {
        uint256 beforeBalance = holder.balance;
        vm.prank(holder);
        slice.withdraw();
        assertEq(holder.balance - beforeBalance, expected, "payout landed");
        assertEq(slice.accrued(holder), 0, "accrual cleared");
    }

    function assertEq(uint256 left, uint256 right, string memory label) internal pure {
        if (left != right) revert(label);
    }
}
