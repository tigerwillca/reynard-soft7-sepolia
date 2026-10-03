// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {DividendSlice} from "./DividendSlice.sol";
import {MockSoft7} from "./MockSoft7.sol";

/// @notice Mint and reward-claim entry points. Both hand the paid value to DividendSlice.
contract Soft7Desk {
    DividendSlice public immutable slice;
    MockSoft7 public immutable collection;

    constructor(DividendSlice slice_, MockSoft7 collection_) {
        slice = slice_;
        collection = collection_;
    }

    function mint(address to) external payable {
        collection.mint(to);
        slice.onMint{value: msg.value}();
    }

    function claimReward() external payable {
        slice.onClaim{value: msg.value}(msg.sender);
    }
}
