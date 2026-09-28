// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

/// @title Soft7MascotCards
/// @notice Proof contract for Reynard Soft7 mascot cards. Nothing in this file
///         has been deployed or minted. Mint stays closed until the owner
///         marks the art proofs approved and then opens the waves.
/// @dev Robinhood Chain 4663. Supply 777. First wave is 7 tokens. Each week
///      after that adds 77, until 777. Ten percent of every mint accrues to
///      staked holders in proportion to how many cards they have staked. If
///      nobody is staked, that ten percent is paid to the Robinhood wallet
///      ending in 77a. The other ninety percent always goes to that wallet.
///      Secondary sales pay a 7.5% royalty to the same wallet.
///      This is not the bytecode at 0x73D7b2611509C14078e16f572bE5aC7D91879DC2.
///      That contract is unverified, solc 0.8.24, metadata
///      QmXzj3Udp5RXzPES8xuX11CUpZKauk4bkw2hkCdcvLpkRj, and its MAX_SUPPLY is 7.
contract Soft7MascotCards {
    string public constant name = "Reynard Soft7";
    string public constant symbol = "SOFT7";
    uint256 public constant MAX_SUPPLY = 777;
    uint256 public constant FIRST_WAVE = 7;
    uint256 public constant WEEKLY_WAVE = 77;
    uint256 public constant WAVE_PERIOD = 7 days;
    uint96 public constant ROYALTY_BPS = 750;
    uint256 private constant _SCALE = 1e18;

    /// @dev Robinhood wallet ending 77a. Creator share and unstaked dividends.
    address public constant PAYOUT = 0xe53bdb2118585d5B2cD06a117d3A036AFA70677a;

    address public owner;
    string private _base;
    uint256 public totalSupply;
    uint256 public mintPrice;
    bool public proofsApproved;
    uint64 public opening;
    uint256 public totalStaked;
    uint256 public accPerStake;

    mapping(uint256 => address) private _owners;
    mapping(address => uint256) private _balances;
    mapping(uint256 => address) private _approvals;
    mapping(address => mapping(address => bool)) private _operatorApprovals;
    mapping(uint256 => address) public stakedBy;
    mapping(address => uint256) public stakedCount;
    mapping(address => uint256) public rewardDebt;
    mapping(address => uint256) public accrued;

    error NotOwner();
    error ProofsPending();
    error AlreadyOpen();
    error WaveFull();
    error WrongPrice();
    error WrongChain();
    error BadBase();
    error ZeroAddress();
    error NotTokenOwner();
    error AlreadyStaked();
    error NotStaked();
    error Nonexistent();
    error Unauthorized();
    error UnsafeReceiver();
    error PayFailed();

    event Transfer(address indexed from, address indexed to, uint256 indexed tokenId);
    event Approval(address indexed owner, address indexed approved, uint256 indexed tokenId);
    event ApprovalForAll(address indexed owner, address indexed operator, bool approved);
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);
    event ProofsApproved();
    event WavesOpened(uint64 opening);
    event MintPriceSet(uint256 price);
    event BaseURISet(string baseURI);
    event Staked(address indexed holder, uint256 indexed tokenId);
    event Unstaked(address indexed holder, uint256 indexed tokenId);
    event Pulled(address indexed holder, uint256 amount);
    event MetadataUpdate(uint256 tokenId);
    event BatchMetadataUpdate(uint256 fromTokenId, uint256 toTokenId);

    modifier onlyOwner() {
        if (msg.sender != owner) revert NotOwner();
        _;
    }

    constructor(string memory baseURI_) {
        owner = msg.sender;
        _setBase(baseURI_);
        emit OwnershipTransferred(address(0), msg.sender);
    }

    function approveProofs() external onlyOwner {
        proofsApproved = true;
        emit ProofsApproved();
    }

    function openWaves() external onlyOwner {
        if (!proofsApproved) revert ProofsPending();
        if (opening != 0) revert AlreadyOpen();
        opening = uint64(block.timestamp);
        emit WavesOpened(opening);
    }

    function setMintPrice(uint256 price) external onlyOwner {
        mintPrice = price;
        emit MintPriceSet(price);
    }

    function setBaseURI(string calldata baseURI_) external onlyOwner {
        _setBase(baseURI_);
        emit BatchMetadataUpdate(1, MAX_SUPPLY);
    }

    function transferOwnership(address nextOwner) external onlyOwner {
        if (nextOwner == address(0)) revert ZeroAddress();
        address previous = owner;
        owner = nextOwner;
        emit OwnershipTransferred(previous, nextOwner);
    }

    /// @notice Tokens that may exist at this moment. Week 0 is 7. Each later week adds 77.
    function waveCap() public view returns (uint256) {
        if (opening == 0) return 0;
        uint256 weeksElapsed = (block.timestamp - opening) / WAVE_PERIOD;
        uint256 cap = FIRST_WAVE + (weeksElapsed * WEEKLY_WAVE);
        if (cap > MAX_SUPPLY) return MAX_SUPPLY;
        return cap;
    }

    function mint() external payable returns (uint256 tokenId) {
        if (block.chainid != 4663) revert WrongChain();
        if (!proofsApproved || opening == 0) revert ProofsPending();
        if (msg.value != mintPrice) revert WrongPrice();
        if (totalSupply >= waveCap()) revert WaveFull();

        tokenId = totalSupply + 1;
        totalSupply = tokenId;
        _mint(msg.sender, tokenId);

        uint256 dividend = msg.value / 10;
        _routeDividend(dividend);
        _pay(PAYOUT, msg.value - dividend);
    }

    /// @notice Keep the card in the holder's wallet. Stake is a claim weight, not custody.
    function stake(uint256 tokenId) external {
        if (_owners[tokenId] != msg.sender) revert NotTokenOwner();
        if (stakedBy[tokenId] != address(0)) revert AlreadyStaked();
        _settle(msg.sender);
        stakedBy[tokenId] = msg.sender;
        stakedCount[msg.sender] += 1;
        totalStaked += 1;
        rewardDebt[msg.sender] = (stakedCount[msg.sender] * accPerStake) / _SCALE;
        emit Staked(msg.sender, tokenId);
    }

    function unstake(uint256 tokenId) external {
        if (stakedBy[tokenId] != msg.sender) revert NotStaked();
        _clearStake(msg.sender, tokenId);
    }

    /// @notice Pull the caller's accrued dividend.
    function pull() external {
        _settle(msg.sender);
        uint256 amount = accrued[msg.sender];
        accrued[msg.sender] = 0;
        _pay(msg.sender, amount);
        emit Pulled(msg.sender, amount);
    }

    function pending(address holder) external view returns (uint256) {
        uint256 extra = (stakedCount[holder] * accPerStake) / _SCALE;
        uint256 debt = rewardDebt[holder];
        uint256 gained = extra > debt ? extra - debt : 0;
        return accrued[holder] + gained;
    }

    function balanceOf(address account) external view returns (uint256) {
        if (account == address(0)) revert ZeroAddress();
        return _balances[account];
    }

    function ownerOf(uint256 tokenId) external view returns (address) {
        address tokenOwner = _owners[tokenId];
        if (tokenOwner == address(0)) revert Nonexistent();
        return tokenOwner;
    }

    function tokenURI(uint256 tokenId) external view returns (string memory) {
        if (_owners[tokenId] == address(0)) revert Nonexistent();
        return string.concat(_base, _toString(tokenId), ".json");
    }

    function approve(address to, uint256 tokenId) external {
        address tokenOwner = _owners[tokenId];
        if (tokenOwner == address(0)) revert Nonexistent();
        if (msg.sender != tokenOwner && !_operatorApprovals[tokenOwner][msg.sender]) revert Unauthorized();
        _approvals[tokenId] = to;
        emit Approval(tokenOwner, to, tokenId);
    }

    function getApproved(uint256 tokenId) external view returns (address) {
        if (_owners[tokenId] == address(0)) revert Nonexistent();
        return _approvals[tokenId];
    }

    function setApprovalForAll(address operator, bool approved) external {
        if (operator == address(0)) revert ZeroAddress();
        _operatorApprovals[msg.sender][operator] = approved;
        emit ApprovalForAll(msg.sender, operator, approved);
    }

    function isApprovedForAll(address tokenOwner, address operator) external view returns (bool) {
        return _operatorApprovals[tokenOwner][operator];
    }

    function transferFrom(address from, address to, uint256 tokenId) public {
        _transfer(from, to, tokenId);
    }

    function safeTransferFrom(address from, address to, uint256 tokenId) external {
        _transfer(from, to, tokenId);
        _checkReceiver(from, to, tokenId, "");
    }

    function safeTransferFrom(address from, address to, uint256 tokenId, bytes calldata data) external {
        _transfer(from, to, tokenId);
        _checkReceiver(from, to, tokenId, data);
    }

    function royaltyInfo(uint256, uint256 salePrice) external pure returns (address receiver, uint256 royaltyAmount) {
        receiver = PAYOUT;
        royaltyAmount = (salePrice * ROYALTY_BPS) / 10000;
    }

    function supportsInterface(bytes4 interfaceId) external pure returns (bool) {
        return interfaceId == 0x01ffc9a7
            || interfaceId == 0x80ac58cd
            || interfaceId == 0x5b5e139f
            || interfaceId == 0x2a55205a
            || interfaceId == 0x49064906;
    }

    function _setBase(string memory baseURI_) internal {
        bytes memory raw = bytes(baseURI_);
        if (raw.length == 0 || raw[raw.length - 1] != bytes1("/")) revert BadBase();
        _base = baseURI_;
        emit BaseURISet(baseURI_);
    }

    function _routeDividend(uint256 dividend) internal {
        if (dividend == 0) return;
        if (totalStaked == 0) {
            _pay(PAYOUT, dividend);
            return;
        }
        accPerStake += (dividend * _SCALE) / totalStaked;
    }

    function _settle(address holder) internal {
        uint256 extra = (stakedCount[holder] * accPerStake) / _SCALE;
        if (extra > rewardDebt[holder]) {
            accrued[holder] += extra - rewardDebt[holder];
        }
        rewardDebt[holder] = (stakedCount[holder] * accPerStake) / _SCALE;
    }

    function _clearStake(address holder, uint256 tokenId) internal {
        _settle(holder);
        stakedBy[tokenId] = address(0);
        stakedCount[holder] -= 1;
        totalStaked -= 1;
        rewardDebt[holder] = (stakedCount[holder] * accPerStake) / _SCALE;
        emit Unstaked(holder, tokenId);
    }

    function _pay(address to, uint256 amount) internal {
        if (amount == 0) return;
        (bool ok,) = to.call{value: amount}("");
        if (!ok) revert PayFailed();
    }

    function _mint(address to, uint256 tokenId) internal {
        if (to == address(0)) revert ZeroAddress();
        _owners[tokenId] = to;
        _balances[to] += 1;
        emit Transfer(address(0), to, tokenId);
    }

    function _transfer(address from, address to, uint256 tokenId) internal {
        address tokenOwner = _owners[tokenId];
        if (tokenOwner == address(0)) revert Nonexistent();
        if (tokenOwner != from) revert NotTokenOwner();
        if (to == address(0)) revert ZeroAddress();
        if (
            msg.sender != from && msg.sender != _approvals[tokenId]
                && !_operatorApprovals[from][msg.sender]
        ) revert Unauthorized();
        if (stakedBy[tokenId] != address(0)) _clearStake(from, tokenId);
        delete _approvals[tokenId];
        _balances[from] -= 1;
        _balances[to] += 1;
        _owners[tokenId] = to;
        emit Transfer(from, to, tokenId);
    }

    function _checkReceiver(address from, address to, uint256 tokenId, bytes memory data) internal {
        if (to.code.length == 0) return;
        try IERC721Receiver(to).onERC721Received(msg.sender, from, tokenId, data) returns (bytes4 retval) {
            if (retval != IERC721Receiver.onERC721Received.selector) revert UnsafeReceiver();
        } catch {
            revert UnsafeReceiver();
        }
    }

    function _toString(uint256 value) internal pure returns (string memory) {
        if (value == 0) return "0";
        uint256 temp = value;
        uint256 digits;
        while (temp != 0) {
            digits++;
            temp /= 10;
        }
        bytes memory buffer = new bytes(digits);
        while (value != 0) {
            digits -= 1;
            buffer[digits] = bytes1(uint8(48 + uint256(value % 10)));
            value /= 10;
        }
        return string(buffer);
    }
}

interface IERC721Receiver {
    function onERC721Received(address operator, address from, uint256 tokenId, bytes calldata data)
        external
        returns (bytes4);
}
