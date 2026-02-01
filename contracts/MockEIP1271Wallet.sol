// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @notice Minimal EIP-1271 wallet for local testing.
/// It accepts a signature if it is a valid ECDSA signature from `owner` over the given hash.
contract MockEIP1271Wallet {
    // EIP-1271 magic value
    bytes4 internal constant MAGICVALUE = 0x1626ba7e;

    address public immutable owner;

    constructor(address owner_) {
        owner = owner_;
    }

    /// @notice EIP-1271 validation method
    /// @dev isValidSignature(bytes32,bytes) => bytes4 magicValue
    function isValidSignature(bytes32 hash, bytes calldata signature) external view returns (bytes4) {
        address recovered = _recover(hash, signature);
        if (recovered == owner) return MAGICVALUE;
        return 0xffffffff;
    }

    function _recover(bytes32 hash, bytes calldata sig) internal pure returns (address) {
        if (sig.length != 65) return address(0);
        bytes32 r;
        bytes32 s;
        uint8 v;
        // solhint-disable-next-line no-inline-assembly
        assembly {
            r := calldataload(sig.offset)
            s := calldataload(add(sig.offset, 32))
            v := byte(0, calldataload(add(sig.offset, 64)))
        }
        if (v < 27) v += 27;
        if (v != 27 && v != 28) return address(0);
        return ecrecover(hash, v, r, s);
    }
}

