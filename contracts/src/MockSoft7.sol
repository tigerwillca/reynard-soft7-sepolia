// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @notice Minimal enumerable ERC-721 stand-in so DividendSlice can read holders.
contract MockSoft7 {
    uint256 public totalSupply;
    mapping(uint256 => address) private _owners;

    error NotMinted(uint256 tokenId);

    function ownerOf(uint256 tokenId) external view returns (address) {
        address owner = _owners[tokenId];
        if (owner == address(0)) revert NotMinted(tokenId);
        return owner;
    }

    function mint(address to) external returns (uint256 tokenId) {
        require(to != address(0), "mint to zero");
        totalSupply += 1;
        tokenId = totalSupply;
        _owners[tokenId] = to;
    }
}
