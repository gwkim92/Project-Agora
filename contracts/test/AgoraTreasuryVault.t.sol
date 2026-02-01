// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";

import "../AgoraTreasuryVault.sol";
import "./MockUSDC.sol";

contract AgoraTreasuryVaultTest is Test {
    AgoraTreasuryVault vault;
    MockUSDC usdc;

    address owner = address(0x1111);
    address donor = address(0x2222);
    address recipient = address(0x3333);

    function setUp() public {
        usdc = new MockUSDC();
        vault = new AgoraTreasuryVault(owner, address(usdc));

        vm.deal(donor, 10 ether);
        usdc.mint(donor, 1_000_000e6);
    }

    function testDonateEthUpdatesAccounting() public {
        vm.prank(donor);
        vault.donateEth{value: 1 ether}(7, bytes32(uint256(123)));

        assertEq(vault.totalIn(7, address(0)), 1 ether);
        assertEq(uint256(vault.netFor(7, address(0))), 1 ether);
    }

    function testReceiveEthBucketZero() public {
        vm.prank(donor);
        (bool ok,) = address(vault).call{value: 0.5 ether}("");
        assertTrue(ok);
        assertEq(vault.totalIn(0, address(0)), 0.5 ether);
    }

    function testDonateUsdcUpdatesAccounting() public {
        vm.startPrank(donor);
        usdc.approve(address(vault), 100e6);
        vault.donateUsdc(100e6, 2, bytes32(uint256(456)));
        vm.stopPrank();

        assertEq(vault.totalIn(2, address(usdc)), 100e6);
        assertEq(uint256(vault.netFor(2, address(usdc))), 100e6);
    }

    function testSpendEthOnlyOwner() public {
        // fund vault
        vm.prank(donor);
        vault.donateEth{value: 1 ether}(1, bytes32(0));

        uint256 beforeBal = recipient.balance;
        vm.prank(owner);
        vault.spendEth(payable(recipient), 0.25 ether, 1, bytes32(uint256(999)));

        assertEq(recipient.balance, beforeBal + 0.25 ether);
        assertEq(vault.totalOut(1, address(0)), 0.25 ether);
    }

    function testSpendUsdcOnlyOwner() public {
        vm.startPrank(donor);
        usdc.approve(address(vault), 200e6);
        vault.donateUsdc(200e6, 3, bytes32(0));
        vm.stopPrank();

        uint256 beforeBal = usdc.balanceOf(recipient);
        vm.prank(owner);
        vault.spendUsdc(recipient, 50e6, 3, bytes32(uint256(1)));

        assertEq(usdc.balanceOf(recipient), beforeBal + 50e6);
        assertEq(vault.totalOut(3, address(usdc)), 50e6);
    }

    function testNonOwnerCannotSpend() public {
        vm.prank(donor);
        vault.donateEth{value: 1 ether}(1, bytes32(0));

        vm.prank(donor);
        vm.expectRevert(AgoraTreasuryVault.NotOwner.selector);
        vault.spendEth(payable(recipient), 0.1 ether, 1, bytes32(0));
    }
}

