// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * AgoraStakeVaultV2 (Reference Draft)
 *
 * Purpose:
 * - Minimum stake for Sybil resistance
 * - Slashing hook (governance/ops) for Phase 2+
 *
 * Improvements vs v1 draft:
 * - Events for indexability/auditability
 * - Safer ERC20 transfer handling (supports tokens that return no boolean)
 * - Pause switch for emergency response
 * - Two-step slasher transfer
 * - depositFor(agent, amount) for operator/multisig workflows
 *
 * NOTE:
 * - This is still a reference draft. Production should add:
 *   timelock/multisig ownership, per-job escrow, accounting audits, and formal security review.
 */

interface IERC20Like {
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function transfer(address to, uint256 amount) external returns (bool);
}

contract AgoraStakeVaultV2 {
    // ---- Events ----
    event Deposited(address indexed payer, address indexed agent, uint256 amount);
    event Withdrawn(address indexed agent, uint256 amount);
    event Slashed(address indexed agent, address indexed recipient, uint256 requestedAmount, uint256 actualAmount);
    event SlasherProposed(address indexed oldSlasher, address indexed newSlasher);
    event SlasherAccepted(address indexed oldSlasher, address indexed newSlasher);
    event Paused(address indexed by);
    event Unpaused(address indexed by);

    // ---- Config ----
    IERC20Like public immutable usdc;

    address public owner; // should be timelock/multisig in production
    address public slasher;
    address public pendingSlasher;

    bool public paused;

    // USDC units (6 decimals assumed by server/onchain.py conversion)
    mapping(address => uint256) private _stake;

    // ---- Errors ----
    error NotOwner();
    error NotSlasher();
    error NotPendingSlasher();
    error PausedErr();
    error ZeroAddress();
    error ZeroAmount();
    error InsufficientStake();
    error TransferFailed();

    modifier onlyOwner() {
        if (msg.sender != owner) revert NotOwner();
        _;
    }

    modifier onlySlasher() {
        if (msg.sender != slasher) revert NotSlasher();
        _;
    }

    modifier whenNotPaused() {
        if (paused) revert PausedErr();
        _;
    }

    constructor(address usdcAddress, address ownerAddress, address slasherAddress) {
        if (usdcAddress == address(0) || ownerAddress == address(0) || slasherAddress == address(0)) revert ZeroAddress();
        usdc = IERC20Like(usdcAddress);
        owner = ownerAddress;
        slasher = slasherAddress;
    }

    // ---- Ownership ----
    function transferOwnership(address newOwner) external onlyOwner {
        if (newOwner == address(0)) revert ZeroAddress();
        owner = newOwner;
    }

    // ---- Pause ----
    function pause() external onlyOwner {
        if (!paused) {
            paused = true;
            emit Paused(msg.sender);
        }
    }

    function unpause() external onlyOwner {
        if (paused) {
            paused = false;
            emit Unpaused(msg.sender);
        }
    }

    // ---- Slasher role (two-step) ----
    function proposeSlasher(address newSlasher) external onlySlasher {
        if (newSlasher == address(0)) revert ZeroAddress();
        pendingSlasher = newSlasher;
        emit SlasherProposed(slasher, newSlasher);
    }

    function acceptSlasher() external {
        if (msg.sender != pendingSlasher) revert NotPendingSlasher();
        address old = slasher;
        slasher = msg.sender;
        pendingSlasher = address(0);
        emit SlasherAccepted(old, slasher);
    }

    // ---- Views ----
    function stakeOf(address agent) external view returns (uint256) {
        return _stake[agent];
    }

    // ---- Staking ----
    function deposit(uint256 amount) external whenNotPaused {
        _depositFor(msg.sender, msg.sender, amount);
    }

    function depositFor(address agent, uint256 amount) external whenNotPaused {
        if (agent == address(0)) revert ZeroAddress();
        _depositFor(msg.sender, agent, amount);
    }

    function withdraw(uint256 amount) external whenNotPaused {
        if (amount == 0) revert ZeroAmount();
        uint256 s = _stake[msg.sender];
        if (s < amount) revert InsufficientStake();
        _stake[msg.sender] = s - amount;
        _safeTransfer(address(usdc), msg.sender, amount);
        emit Withdrawn(msg.sender, amount);
    }

    // ---- Slashing ----
    function slash(address agent, uint256 amount, address recipient) external onlySlasher whenNotPaused {
        if (agent == address(0) || recipient == address(0)) revert ZeroAddress();
        if (amount == 0) revert ZeroAmount();
        uint256 s = _stake[agent];
        uint256 actual = amount;
        if (s < actual) actual = s;
        _stake[agent] = s - actual;
        _safeTransfer(address(usdc), recipient, actual);
        emit Slashed(agent, recipient, amount, actual);
    }

    // ---- Rescue (non-USDC only) ----
    function rescueToken(address token, address to, uint256 amount) external onlyOwner {
        if (token == address(0) || to == address(0)) revert ZeroAddress();
        // prevent accidentally rescuing the staking asset
        require(token != address(usdc), "cannot rescue usdc");
        _safeTransfer(token, to, amount);
    }

    // ---- Internals ----
    function _depositFor(address payer, address agent, uint256 amount) internal {
        if (amount == 0) revert ZeroAmount();
        _safeTransferFrom(address(usdc), payer, address(this), amount);
        _stake[agent] += amount;
        emit Deposited(payer, agent, amount);
    }

    /// @dev "SafeERC20-lite" to support:
    /// - returns(bool)
    /// - returns nothing (assume success if call didn't revert)
    function _safeTransfer(address token, address to, uint256 amount) internal {
        (bool ok, bytes memory data) = token.call(abi.encodeWithSelector(IERC20Like.transfer.selector, to, amount));
        if (!ok) revert TransferFailed();
        if (data.length > 0 && !abi.decode(data, (bool))) revert TransferFailed();
    }

    function _safeTransferFrom(address token, address from, address to, uint256 amount) internal {
        (bool ok, bytes memory data) =
            token.call(abi.encodeWithSelector(IERC20Like.transferFrom.selector, from, to, amount));
        if (!ok) revert TransferFailed();
        if (data.length > 0 && !abi.decode(data, (bool))) revert TransferFailed();
    }
}

