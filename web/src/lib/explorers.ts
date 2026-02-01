export function explorerBase(chainId?: number | null): string | null {
  if (!chainId) return null;
  switch (chainId) {
    case 1:
      return "https://etherscan.io";
    case 10:
      return "https://optimistic.etherscan.io";
    case 137:
      return "https://polygonscan.com";
    case 42161:
      return "https://arbiscan.io";
    case 8453:
      return "https://basescan.org";
    case 84532:
      return "https://sepolia.basescan.org";
    default:
      return null;
  }
}

export function txUrl(chainId: number | null | undefined, txHash: string | null | undefined): string | null {
  const base = explorerBase(chainId);
  if (!base || !txHash) return null;
  return `${base}/tx/${txHash}`;
}

export function addressUrl(chainId: number | null | undefined, address: string | null | undefined): string | null {
  const base = explorerBase(chainId);
  if (!base || !address) return null;
  return `${base}/address/${address}`;
}

