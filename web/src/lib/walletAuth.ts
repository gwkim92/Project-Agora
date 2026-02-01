export type WalletAuthState = {
  address: string | null;
  connector?: "injected" | "walletconnect";
};

const STORAGE_KEY = "agora_wallet_address_v1";

function safeJsonParse<T>(raw: string | null): T | null {
  if (!raw) return null;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

export function loadWalletAuth(): WalletAuthState {
  if (typeof window === "undefined") return { address: null };
  const parsed = safeJsonParse<WalletAuthState>(window.localStorage.getItem(STORAGE_KEY));
  return {
    address: parsed?.address ?? null,
    connector: parsed?.connector ?? "injected",
  };
}

export function saveWalletAuth(next: WalletAuthState) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
}

export function clearWalletAuth() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(STORAGE_KEY);
}

type Eip1193Provider = {
  request: (args: { method: string; params?: readonly unknown[] }) => Promise<unknown>;
  on?: (event: string, fn: (...args: unknown[]) => void) => void;
  disconnect?: () => Promise<void> | void;
};

type WindowWithEthereum = Window & typeof globalThis & { ethereum?: Eip1193Provider };

type WalletConnectProvider = Eip1193Provider & { connect?: () => Promise<void> | void };

let activeProvider: Eip1193Provider | null = null;
let activeConnector: "injected" | "walletconnect" | null = null;
let walletConnectProviderPromise: Promise<Eip1193Provider> | null = null;

function toHexChainId(chainId: number): string {
  return "0x" + Number(chainId).toString(16);
}

function chainParams(chainId: number) {
  // Minimal set for MetaMask add/switch chain.
  // We support Base mainnet + Base Sepolia.
  if (chainId === 8453) {
    return {
      chainId: toHexChainId(chainId),
      chainName: "Base",
      nativeCurrency: { name: "Ether", symbol: "ETH", decimals: 18 },
      rpcUrls: ["https://mainnet.base.org"],
      blockExplorerUrls: ["https://basescan.org"],
    };
  }
  if (chainId === 84532) {
    return {
      chainId: toHexChainId(chainId),
      chainName: "Base Sepolia",
      nativeCurrency: { name: "Ether", symbol: "ETH", decimals: 18 },
      rpcUrls: ["https://sepolia.base.org"],
      blockExplorerUrls: ["https://sepolia.basescan.org"],
    };
  }
  return null;
}

export async function ensureInjectedChain(targetChainId: number): Promise<void> {
  const eth = (window as WindowWithEthereum).ethereum;
  if (!eth?.request) throw new Error("No injected wallet found (install MetaMask)");
  const hex = toHexChainId(targetChainId);
  try {
    await eth.request({ method: "wallet_switchEthereumChain", params: [{ chainId: hex }] });
  } catch (e: any) {
    const code = e?.code;
    // 4902: unknown chain
    if (code === 4902) {
      const params = chainParams(targetChainId);
      if (!params) throw new Error(`Unsupported chainId=${targetChainId}`);
      await eth.request({ method: "wallet_addEthereumChain", params: [params] });
      await eth.request({ method: "wallet_switchEthereumChain", params: [{ chainId: hex }] });
      return;
    }
    throw e;
  }
}

export function getActiveConnector() {
  return activeConnector;
}

export function getActiveProvider() {
  return activeProvider;
}

export async function connectInjectedWallet(): Promise<string> {
  const eth = (window as WindowWithEthereum).ethereum;
  if (!eth?.request) throw new Error("No injected wallet found (install MetaMask)");
  const accounts = (await eth.request({ method: "eth_requestAccounts" })) as string[];
  if (!accounts?.[0]) throw new Error("No accounts returned from wallet");
  activeProvider = eth as Eip1193Provider;
  activeConnector = "injected";
  return String(accounts[0]);
}

// Backward-compatible helper: try injected first, then WalletConnect as a fallback.
export async function connectWallet(): Promise<string> {
  try {
    return await connectInjectedWallet();
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    if (msg.toLowerCase().includes("no injected wallet")) {
      return await connectWalletConnect();
    }
    throw e;
  }
}

async function getWalletConnectProvider(): Promise<Eip1193Provider> {
  if (walletConnectProviderPromise) return walletConnectProviderPromise;
  // Lazy import: WalletConnect libs are large; only load when user chooses it.
  walletConnectProviderPromise = (async () => {
    const { default: EthereumProvider } = await import("@walletconnect/ethereum-provider");
    const projectId = process.env.NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID;
    if (!projectId) {
      throw new Error("WalletConnect not configured (missing NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID)");
    }
    const provider = await EthereumProvider.init({
      projectId,
      // Base mainnet + Base Sepolia. (Auth uses signatures; no gas needed.)
      chains: [Number(process.env.NEXT_PUBLIC_AGORA_CHAIN_ID ?? "8453")],
      optionalChains: [8453, 84532].filter((c) => c !== Number(process.env.NEXT_PUBLIC_AGORA_CHAIN_ID ?? "8453")),
      showQrModal: true,
      methods: ["eth_requestAccounts", "personal_sign", "eth_chainId", "eth_sendTransaction"],
      events: ["accountsChanged", "chainChanged", "disconnect"],
    });
    return provider as unknown as Eip1193Provider;
  })();
  return walletConnectProviderPromise;
}

export async function connectWalletConnect(): Promise<string> {
  if (typeof window === "undefined") throw new Error("WalletConnect requires a browser");
  const provider = (await getWalletConnectProvider()) as WalletConnectProvider;
  // Some WalletConnect provider versions require an explicit connect() before request().
  await provider.connect?.();
  let accounts: string[] | undefined;
  try {
    accounts = (await provider.request({ method: "eth_requestAccounts" })) as string[];
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    if (msg.toLowerCase().includes("please call connect() before request")) {
      await provider.connect?.();
      accounts = (await provider.request({ method: "eth_requestAccounts" })) as string[];
    } else {
      throw e;
    }
  }
  if (!accounts?.[0]) throw new Error("No accounts returned from wallet");
  activeProvider = provider;
  activeConnector = "walletconnect";
  return String(accounts[0]);
}

export async function disconnectActiveWallet(): Promise<void> {
  try {
    await activeProvider?.disconnect?.();
  } finally {
    activeProvider = null;
    activeConnector = null;
  }
}

export async function personalSign(address: string, message: string): Promise<string> {
  const provider = activeProvider ?? ((window as WindowWithEthereum).ethereum as Eip1193Provider | undefined);
  if (!provider?.request) throw new Error("No wallet provider available");
  // MetaMask expects params: [message, address]
  const sig = (await provider.request({ method: "personal_sign", params: [message, address] })) as string;
  return sig;
}

