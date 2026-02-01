// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";

import {AgoraStakeVaultV2} from "../AgoraStakeVaultV2.sol";
import {MockUSDC} from "./MockUSDC.sol";

contract AgoraStakeVaultV2Test is Test {
    MockUSDC usdc;
    AgoraStakeVaultV2 vault;

    // Mirror events from AgoraStakeVaultV2 for expectEmit checks
    event Deposited(address indexed payer, address indexed agent, uint256 amount);
    event Withdrawn(address indexed agent, uint256 amount);
    event Slashed(address indexed agent, address indexed recipient, uint256 requestedAmount, uint256 actualAmount);

    address owner;
    address slasher;
    address agent;
    address payer;
    address recipient;

    function setUp() public {
        owner = makeAddr("owner");
        slasher = makeAddr("slasher");
        agent = makeAddr("agent");
        payer = makeAddr("payer");
        recipient = makeAddr("recipient");

        usdc = new MockUSDC();
        vault = new AgoraStakeVaultV2(address(usdc), owner, slasher);

        // mint 1000 USDC to payer/agent (6 decimals)
        usdc.mint(payer, 1_000 * 1e6);
        usdc.mint(agent, 1_000 * 1e6);

        // approvals
        vm.prank(payer);
        usdc.approve(address(vault), type(uint256).max);
        vm.prank(agent);
        usdc.approve(address(vault), type(uint256).max);
    }

    function testDepositIncreasesStakeAndEmits() public {
        vm.prank(agent);
        vm.expectEmit(true, true, false, true);
        emit Deposited(agent, agent, 10 * 1e6);
        vault.deposit(10 * 1e6);
        assertEq(vault.stakeOf(agent), 10 * 1e6);
    }

    function testDepositForCreditsAgent() public {
        vm.prank(payer);
        vault.depositFor(agent, 25 * 1e6);
        assertEq(vault.stakeOf(agent), 25 * 1e6);
    }

    function testWithdrawReducesStakeAndEmits() public {
        vm.prank(agent);
        vault.deposit(50 * 1e6);

        uint256 beforeBal = usdc.balanceOf(agent);
        vm.prank(agent);
        vm.expectEmit(true, false, false, true);
        emit Withdrawn(agent, 20 * 1e6);
        vault.withdraw(20 * 1e6);

        assertEq(vault.stakeOf(agent), 30 * 1e6);
        assertEq(usdc.balanceOf(agent), beforeBal + 20 * 1e6);
    }

    function testWithdrawRevertsWhenInsufficient() public {
        vm.prank(agent);
        vault.deposit(1 * 1e6);
        vm.prank(agent);
        vm.expectRevert(AgoraStakeVaultV2.InsufficientStake.selector);
        vault.withdraw(2 * 1e6);
    }

    function testSlashOnlySlasher() public {
        vm.prank(agent);
        vault.deposit(10 * 1e6);

        vm.prank(address(0xBAD));
        vm.expectRevert(AgoraStakeVaultV2.NotSlasher.selector);
        vault.slash(agent, 1 * 1e6, recipient);
    }

    function testSlashCapsToStakeAndEmits() public {
        vm.prank(agent);
        vault.deposit(10 * 1e6);

        uint256 beforeRecipient = usdc.balanceOf(recipient);
        vm.prank(slasher);
        vm.expectEmit(true, true, false, true);
        emit Slashed(agent, recipient, 50 * 1e6, 10 * 1e6);
        vault.slash(agent, 50 * 1e6, recipient);

        assertEq(vault.stakeOf(agent), 0);
        assertEq(usdc.balanceOf(recipient), beforeRecipient + 10 * 1e6);
    }

    function testPauseBlocksStateChangingOps() public {
        vm.prank(owner);
        vault.pause();

        vm.prank(agent);
        vm.expectRevert(AgoraStakeVaultV2.PausedErr.selector);
        vault.deposit(1 * 1e6);

        vm.prank(slasher);
        vm.expectRevert(AgoraStakeVaultV2.PausedErr.selector);
        vault.slash(agent, 1 * 1e6, recipient);

        vm.prank(owner);
        vault.unpause();

        vm.prank(agent);
        vault.deposit(1 * 1e6);
        assertEq(vault.stakeOf(agent), 1 * 1e6);
    }

    function testSlasherTwoStep() public {
        address newSlasher = address(0x1234);
        vm.prank(slasher);
        vault.proposeSlasher(newSlasher);
        assertEq(vault.pendingSlasher(), newSlasher);

        vm.prank(address(0xBAD));
        vm.expectRevert(AgoraStakeVaultV2.NotPendingSlasher.selector);
        vault.acceptSlasher();

        vm.prank(newSlasher);
        vault.acceptSlasher();
        assertEq(vault.slasher(), newSlasher);
        assertEq(vault.pendingSlasher(), address(0));
    }
}

