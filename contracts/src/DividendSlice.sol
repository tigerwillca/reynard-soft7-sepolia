// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title DividendSlice
/// @notice On each mint payment or reward claim, 10% of that value is owed to
///         current Soft7 holders in proportion to how many tokens they hold.
///         The other 90% is forwarded to the mint treasury or to the claimer.
///         Holder payouts are pull-based so one recipient cannot block the route.
interface ISoft7Holders {
    function totalSupply() external view returns (uint256);
    function ownerOf(uint256 tokenId) external view returns (address);
}

contract DividendSlice {
    uint256 public constant SLICE_BPS = 1_000;
    uint256 public constant BPS_DENOMINATOR = 10_000;
    uint8 public constant KIND_MINT = 1;
    uint8 public constant KIND_CLAIM = 2;

    ISoft7Holders public immutable collection;
    address public immutable treasury;
    address public owner;
    address public desk;

    mapping(address => uint256) public accrued;
    uint256 public retainedDust;
    uint256 private _locked;

    event DeskSet(address indexed desk);
    event DividendAccrued(address indexed holder, uint256 amount, uint8 kind);
    event DividendPaid(address indexed holder, uint256 amount);
    event ProceedsForwarded(address indexed to, uint256 amount, uint8 kind);

    error ZeroAmount();
    error NoSupply();
    error TransferFailed();
    error NotOwner();
    error DeskAlreadySet();
    error NotDesk();
    error Reentered();
    error ZeroAddress();

    modifier nonReentrant() {
        if (_locked != 0) revert Reentered();
        _locked = 1;
        _;
        _locked = 0;
    }

    constructor(address collection_, address treasury_) {
        require(collection_ != address(0) && treasury_ != address(0), "zero address");
        collection = ISoft7Holders(collection_);
        treasury = treasury_;
        owner = msg.sender;
    }

    /// @notice One-time wiring. The desk is the mint/claim contract allowed to route value.
    function setDesk(address desk_) external {
        if (msg.sender != owner) revert NotOwner();
        if (desk != address(0) || desk_ == address(0)) revert DeskAlreadySet();
        desk = desk_;
        emit DeskSet(desk_);
    }

    function onMint() external payable nonReentrant {
        if (msg.sender != desk) revert NotDesk();
        _route(msg.value, treasury, KIND_MINT);
    }

    function onClaim(address claimer) external payable nonReentrant {
        if (msg.sender != desk) revert NotDesk();
        if (claimer == address(0)) revert ZeroAddress();
        _route(msg.value, claimer, KIND_CLAIM);
    }

    /// @notice Send the caller's accrued dividend. This is the payout landing.
    function withdraw() external nonReentrant {
        uint256 amount = accrued[msg.sender];
        if (amount == 0) revert ZeroAmount();
        accrued[msg.sender] = 0;
        (bool ok,) = msg.sender.call{value: amount}("");
        if (!ok) revert TransferFailed();
        emit DividendPaid(msg.sender, amount);
    }

    function _route(uint256 amount, address beneficiary, uint8 kind) internal {
        if (amount == 0) revert ZeroAmount();
        uint256 supply = collection.totalSupply();
        if (supply == 0) revert NoSupply();

        uint256 slice = (amount * SLICE_BPS) / BPS_DENOMINATOR;
        uint256 perToken = slice / supply;
        retainedDust += slice - (perToken * supply);

        for (uint256 tokenId = 1; tokenId <= supply; tokenId++) {
            if (perToken == 0) break;
            address holder = collection.ownerOf(tokenId);
            accrued[holder] += perToken;
            emit DividendAccrued(holder, perToken, kind);
        }

        uint256 rest = amount - slice;
        (bool ok,) = beneficiary.call{value: rest}("");
        if (!ok) revert TransferFailed();
        emit ProceedsForwarded(beneficiary, rest, kind);
    }
}
