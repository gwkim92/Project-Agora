// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";

import {AgoraStakeVaultV2} from "../AgoraStakeVaultV2.sol";
import {AgoraTreasuryVault} from "../AgoraTreasuryVault.sol";
import {AgoraAnchorRegistry} from "../AgoraAnchorRegistry.sol";

/// @notice Deploy core Agora contracts.
///
/// Required env:
/// - DEPLOYER_PRIVATE_KEY: deployer EOA private key (for broadcast)
/// - AGORA_OWNER: owner address for owner-gated contracts (Safe recommended)
/// - AGORA_SLASHER: slasher address for StakeVaultV2 (Safe / ops)
/// - AGORA_USDC: USDC address on the target chain (Base mainnet/testnet)
///
/// Optional env:
/// - AGORA_DEPLOY_ANCHOR_REGISTRY: "1" to deploy AnchorRegistry (default: 1)
///
/// Notes:
/// - This script only deploys contracts. It does not wire server env automatically.
contract DeployAgora is Script {
    function run() external {
        uint256 pk = vm.envUint("DEPLOYER_PRIVATE_KEY");
        address owner = vm.envAddress("AGORA_OWNER");
        address slasher = vm.envAddress("AGORA_SLASHER");
        address usdc = vm.envAddress("AGORA_USDC");

        bool deployAnchor = true;
        try vm.envString("AGORA_DEPLOY_ANCHOR_REGISTRY") returns (string memory v) {
            if (keccak256(bytes(v)) == keccak256(bytes("0"))) deployAnchor = false;
        } catch {
            // default true
        }

        vm.startBroadcast(pk);

        AgoraStakeVaultV2 stakeVault = new AgoraStakeVaultV2(usdc, owner, slasher);
        AgoraTreasuryVault treasuryVault = new AgoraTreasuryVault(owner, usdc);

        AgoraAnchorRegistry anchorRegistry;
        if (deployAnchor) {
            anchorRegistry = new AgoraAnchorRegistry(owner);
        }

        vm.stopBroadcast();

        console2.log("=== Project Agora deployments ===");
        console2.log("chainId:", block.chainid);
        console2.log("AGORA_USDC:", usdc);
        console2.log("AGORA_OWNER:", owner);
        console2.log("AGORA_SLASHER:", slasher);
        console2.log("AgoraStakeVaultV2:", address(stakeVault));
        console2.log("AgoraTreasuryVault:", address(treasuryVault));
        console2.log("AgoraAnchorRegistry:", deployAnchor ? address(anchorRegistry) : address(0));

        console2.log("");
        console2.log("Server env suggestions:");
        console2.log("AGORA_CHAIN_ID=%s", block.chainid);
        console2.log("AGORA_USDC_ADDRESS=%s", usdc);
        console2.log("AGORA_STAKE_CONTRACT_ADDRESS=%s", address(stakeVault));
        console2.log("AGORA_TREASURY_CONTRACT_ADDRESS=%s", address(treasuryVault));
        console2.log("AGORA_ONCHAIN_STAKE_ENABLED=1");
        console2.log("AGORA_ONCHAIN_SYNC_ENABLED=1");
        console2.log("AGORA_RPC_URL=<YOUR_RPC_URL>");
    }
}

