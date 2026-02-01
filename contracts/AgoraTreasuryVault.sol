// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * AgoraTreasuryVault (Draft, Safe-only owner)
 *
 * Goals:
 * - Accept donations in ETH and USDC (Base).
 * - Enforce full transparency: every inflow/outflow emits events and updates public accounting.
 * - Keep governance simple: owner is a Safe (multisig). No onchain timelock in this variant.
 *
 * Notes:
 * - "purposeId" is an application-level bucket id (e.g., 1=ops, 2=rewards, 3=audits, ...).
 * - "memoHash" is a bytes32 hash of optional offchain memo/metadata (keeps gas low but still linkable).
 * - Asset address: address(0) denotes native ETH.
 */
interface IERC20Like {
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function transfer(address to, uint256 amount) external returns (bool);
}

contract AgoraTreasuryVault {
    // ---- Events ----
    event DonationReceived(address indexed donor, address indexed asset, uint256 amount, uint32 indexed purposeId, bytes32 memoHash);
    event TreasurySpent(address indexed executor, address indexed to, address indexed asset, uint256 amount, uint32 purposeId, bytes32 memoHash);
    event OwnerChanged(address indexed oldOwner, address indexed newOwner);
    event AllowedTokenSet(address indexed token, bool allowed);

    // ---- Errors ----
    error NotOwner();
    error ZeroAddress();
    error ZeroAmount();
    error TokenNotAllowed();
    error TransferFailed();

    // ---- Config ----
    address public owner; // should be a Safe
    address public immutable usdc;

    // allowlist for ERC20 donations/spends (USDC enabled by default)
    mapping(address => bool) public allowedToken;

    // Accounting:
    // purposeId -> asset -> totalIn/totalOut (asset=address(0) for ETH)
    mapping(uint32 => mapping(address => uint256)) public totalIn;
    mapping(uint32 => mapping(address => uint256)) public totalOut;

    modifier onlyOwner() {
        if (msg.sender != owner) revert NotOwner();
        _;
    }

    constructor(address ownerAddress, address usdcAddress) {
        if (ownerAddress == address(0) || usdcAddress == address(0)) revert ZeroAddress();
        owner = ownerAddress;
        usdc = usdcAddress;
        allowedToken[usdcAddress] = true;
        emit AllowedTokenSet(usdcAddress, true);
    }

    // ---- Owner management ----
    function transferOwnership(address newOwner) external onlyOwner {
        if (newOwner == address(0)) revert ZeroAddress();
        address old = owner;
        owner = newOwner;
        emit OwnerChanged(old, newOwner);
    }

    function setAllowedToken(address token, bool allowed) external onlyOwner {
        if (token == address(0)) revert ZeroAddress();
        allowedToken[token] = allowed;
        emit AllowedTokenSet(token, allowed);
    }

    // ---- Donations ----
    receive() external payable {
        // allow direct ETH transfers, but without purpose/memo (bucket 0)
        if (msg.value == 0) revert ZeroAmount();
        totalIn[0][address(0)] += msg.value;
        emit DonationReceived(msg.sender, address(0), msg.value, 0, bytes32(0));
    }

    function donateEth(uint32 purposeId, bytes32 memoHash) external payable {
        if (msg.value == 0) revert ZeroAmount();
        totalIn[purposeId][address(0)] += msg.value;
        emit DonationReceived(msg.sender, address(0), msg.value, purposeId, memoHash);
    }

    function donateToken(address token, uint256 amount, uint32 purposeId, bytes32 memoHash) public {
        if (!allowedToken[token]) revert TokenNotAllowed();
        if (amount == 0) revert ZeroAmount();
        _safeTransferFrom(token, msg.sender, address(this), amount);
        totalIn[purposeId][token] += amount;
        emit DonationReceived(msg.sender, token, amount, purposeId, memoHash);
    }

    function donateUsdc(uint256 amount, uint32 purposeId, bytes32 memoHash) external {
        donateToken(usdc, amount, purposeId, memoHash);
    }

    // ---- Spending (only owner/Safe) ----
    function spendEth(address payable to, uint256 amount, uint32 purposeId, bytes32 memoHash) external onlyOwner {
        if (to == address(0)) revert ZeroAddress();
        if (amount == 0) revert ZeroAmount();
        totalOut[purposeId][address(0)] += amount;
        (bool ok,) = to.call{value: amount}("");
        if (!ok) revert TransferFailed();
        emit TreasurySpent(msg.sender, to, address(0), amount, purposeId, memoHash);
    }

    function spendToken(address token, address to, uint256 amount, uint32 purposeId, bytes32 memoHash) public onlyOwner {
        if (!allowedToken[token]) revert TokenNotAllowed();
        if (to == address(0)) revert ZeroAddress();
        if (amount == 0) revert ZeroAmount();
        totalOut[purposeId][token] += amount;
        _safeTransfer(token, to, amount);
        emit TreasurySpent(msg.sender, to, token, amount, purposeId, memoHash);
    }

    function spendUsdc(address to, uint256 amount, uint32 purposeId, bytes32 memoHash) external onlyOwner {
        spendToken(usdc, to, amount, purposeId, memoHash);
    }

    // ---- Views ----
    function netFor(uint32 purposeId, address asset) external view returns (int256) {
        return int256(totalIn[purposeId][asset]) - int256(totalOut[purposeId][asset]);
    }

    // ---- Internals (SafeERC20-lite) ----
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

