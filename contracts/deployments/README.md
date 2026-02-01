## Contract deployment sets

This folder stores chain-specific contract addresses for Project Agora.

### Files
- `local.json`: local/dev chain (Anvil). Usually **not committed** (changes every run).
- `base-sepolia.json`: demo/staging (Base Sepolia).
- `base-mainnet.json`: production (Base mainnet).

### How files are generated
Foundry deployment scripts write these JSONs automatically:
- `forge script script/DeployAgora.s.sol:DeployAgora --broadcast ...`

You can override the filename via env:
- `AGORA_DEPLOYMENT_SET=base-sepolia`

