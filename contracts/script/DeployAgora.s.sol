// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";

import {AgoraStakeVaultV2} from "../AgoraStakeVaultV2.sol";
import {AgoraTreasuryVault} from "../AgoraTreasuryVault.sol";
import {AgoraAnchorRegistry} from "../AgoraAnchorRegistry.sol";
import {MockUSDC} from "../test/MockUSDC.sol";

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
        address deployer = vm.addr(pk);

        // For production you should pass explicit addresses (Safe recommended).
        address owner = vm.envOr("AGORA_OWNER", deployer);
        address slasher = vm.envOr("AGORA_SLASHER", deployer);

        // For local/dev, you can omit AGORA_USDC and deploy a MockUSDC instead.
        address usdc = vm.envOr("AGORA_USDC", address(0));
        bool deployMockUsdc = vm.envOr("AGORA_DEPLOY_MOCK_USDC", false);

        bool deployAnchor = true;
        try vm.envString("AGORA_DEPLOY_ANCHOR_REGISTRY") returns (string memory v) {
            if (keccak256(bytes(v)) == keccak256(bytes("0"))) deployAnchor = false;
        } catch {
            // default true
        }

        vm.startBroadcast(pk);

        MockUSDC mock;
        if (usdc == address(0)) {
            if (!deployMockUsdc) revert("AGORA_USDC missing (set it or set AGORA_DEPLOY_MOCK_USDC=1)");
            mock = new MockUSDC();
            usdc = address(mock);
            // Mint some test funds to deployer for local flows (optional).
            // 1,000,000 USDC (6 decimals)
            mock.mint(deployer, 1_000_000 * 1e6);
        }

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
        if (address(mock) != address(0)) console2.log("MockUSDC:", address(mock));

        // ---- Write deployment set JSON (contracts/deployments/<set>.json) ----
        // Keep locals minimal to avoid "stack too deep" in older solc pipelines.
        {
            string memory setName = vm.envOr("AGORA_DEPLOYMENT_SET", vm.toString(block.chainid));
            string memory dir = string.concat(vm.projectRoot(), "/contracts/deployments");
            vm.createDir(dir, true);
            string memory outPath = string.concat(dir, "/", setName, ".json");

            string memory root = "deploy";
            string memory obj = vm.serializeString(root, "deployment_set", setName);
            obj = vm.serializeUint(root, "chain_id", uint256(block.chainid));
            obj = vm.serializeAddress(root, "deployer", deployer);
            obj = vm.serializeAddress(root, "owner", owner);
            obj = vm.serializeAddress(root, "slasher", slasher);
            obj = vm.serializeAddress(root, "usdc", usdc);
            obj = vm.serializeAddress(root, "stake_vault_v2", address(stakeVault));
            obj = vm.serializeAddress(root, "treasury_vault", address(treasuryVault));
            obj = vm.serializeAddress(root, "anchor_registry", deployAnchor ? address(anchorRegistry) : address(0));
            obj = vm.serializeAddress(root, "mock_usdc", address(mock));
            vm.writeJson(obj, outPath);
            console2.log("Wrote deployments file:", outPath);
        }

        console2.log("");
        console2.log("Server env suggestions:");
        console2.log("AGORA_CHAIN_ID=%s", block.chainid);
        console2.log("AGORA_USDC_ADDRESS=%s", usdc);
        console2.log("AGORA_STAKE_CONTRACT_ADDRESS=%s", address(stakeVault));
        console2.log("AGORA_TREASURY_CONTRACT_ADDRESS=%s", address(treasuryVault));
        console2.log("AGORA_ANCHOR_REGISTRY_CONTRACT_ADDRESS=%s", deployAnchor ? address(anchorRegistry) : address(0));
        console2.log("AGORA_ONCHAIN_STAKE_ENABLED=1");
        console2.log("AGORA_ONCHAIN_SYNC_ENABLED=1");
        console2.log("AGORA_RPC_URL=<YOUR_RPC_URL>");
    }
}

