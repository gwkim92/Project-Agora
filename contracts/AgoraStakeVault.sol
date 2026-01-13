// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * AgoraStakeVault (Reference Draft)
 *
 * - Purpose: Sybil resistance via minimum stake + future slashing.
 * - Asset: USDC (6 decimals) on Base (mainnet/testnet).
 *
 * NOTE: This is a reference draft to pin interface expectations.
 *       Production should add: events, role management, pausing, timelocks,
 *       per-job escrow, and audit hardening.
 */

interface IERC20 {
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function transfer(address to, uint256 amount) external returns (bool);
}

contract AgoraStakeVault {
    IERC20 public immutable usdc;
    address public slasher; // governance/ops (Phase 2+: decentralized)

    mapping(address => uint256) private _stake; // USDC units (6 decimals)

    error NotSlasher();
    error InsufficientStake();

    constructor(address usdcAddress, address slasherAddress) {
        usdc = IERC20(usdcAddress);
        slasher = slasherAddress;
    }

    function setSlasher(address newSlasher) external {
        if (msg.sender != slasher) revert NotSlasher();
        slasher = newSlasher;
    }

    function stakeOf(address agent) external view returns (uint256) {
        return _stake[agent];
    }

    function deposit(uint256 amount) external {
        // agent deposits for itself (operator can also deposit by using agent key)
        bool ok = usdc.transferFrom(msg.sender, address(this), amount);
        require(ok, "transferFrom failed");
        _stake[msg.sender] += amount;
    }

    function withdraw(uint256 amount) external {
        if (_stake[msg.sender] < amount) revert InsufficientStake();
        _stake[msg.sender] -= amount;
        bool ok = usdc.transfer(msg.sender, amount);
        require(ok, "transfer failed");
    }

    function slash(address agent, uint256 amount, address recipient) external {
        if (msg.sender != slasher) revert NotSlasher();
        uint256 s = _stake[agent];
        if (s < amount) amount = s;
        _stake[agent] = s - amount;
        bool ok = usdc.transfer(recipient, amount);
        require(ok, "transfer failed");
    }
}

