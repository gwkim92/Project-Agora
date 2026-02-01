// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * AgoraAnchorRegistry (Draft, Safe-only owner)
 *
 * Purpose:
 * - Post an immutable onchain pointer to an offchain "canonical snapshot" (root + uri).
 * - Keep the protocol's source of truth offchain (DB), while making history auditable/verifiable.
 *
 * Notes:
 * - Owner should be an Operator Safe (multisig). No gas sponsorship.
 * - root is typically a bytes32 hash of a canonical JSON snapshot (optionally salted).
 * - uri can be an IPFS URI or HTTPS URL.
 */
contract AgoraAnchorRegistry {
    event AnchorPosted(bytes32 indexed root, string uri, uint32 indexed schemaVersion, bytes32 indexed salt);
    event OwnerChanged(address indexed oldOwner, address indexed newOwner);

    error NotOwner();
    error ZeroAddress();
    error EmptyURI();

    address public owner;

    modifier onlyOwner() {
        if (msg.sender != owner) revert NotOwner();
        _;
    }

    constructor(address ownerAddress) {
        if (ownerAddress == address(0)) revert ZeroAddress();
        owner = ownerAddress;
    }

    function transferOwnership(address newOwner) external onlyOwner {
        if (newOwner == address(0)) revert ZeroAddress();
        address old = owner;
        owner = newOwner;
        emit OwnerChanged(old, newOwner);
    }

    function postAnchor(bytes32 root, string calldata uri, uint32 schemaVersion, bytes32 salt) external onlyOwner {
        if (bytes(uri).length == 0) revert EmptyURI();
        emit AnchorPosted(root, uri, schemaVersion, salt);
    }
}

