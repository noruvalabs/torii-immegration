const PADDLE_JS_SRC = "https://cdn.paddle.com/paddle/v2/paddle.js";

interface PaddleCheckoutOpenOptions {
  transactionId: string;
  settings?: {
    successUrl?: string;
    displayMode?: "overlay" | "inline";
    variant?: "one-page";
  };
}

interface PaddleEventData {
  name: string;
  [key: string]: unknown;
}

interface PaddleInitializeOptions {
  token: string;
  pwCustomer?: { id: string };
  eventCallback?: (data: PaddleEventData) => void;
}

interface PaddleGlobal {
  Environment: { set: (environment: "sandbox") => void };
  Initialize: (options: PaddleInitializeOptions) => void;
  Checkout: { open: (options: PaddleCheckoutOpenOptions) => void };
}

declare global {
  interface Window {
    Paddle?: PaddleGlobal;
  }
}

function loadScript(): Promise<void> {
  if (typeof window === "undefined") return Promise.resolve();
  if (window.Paddle) return Promise.resolve();

  const existing = document.querySelector<HTMLScriptElement>(`script[src="${PADDLE_JS_SRC}"]`);
  if (existing) {
    return new Promise((resolve, reject) => {
      existing.addEventListener("load", () => resolve());
      existing.addEventListener("error", () => reject(new Error("Failed to load Paddle.js")));
    });
  }

  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = PADDLE_JS_SRC;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Failed to load Paddle.js"));
    document.head.appendChild(script);
  });
}

let paddleInitialized = false;
let currentEventListener: ((data: PaddleEventData) => void) | null = null;

/**
 * Loads Paddle.js v2 once and initializes it with client token and environment.
 */
export async function getPaddle(clientTokenOverride?: string, envOverride?: string): Promise<PaddleGlobal> {
  const token = clientTokenOverride || process.env.NEXT_PUBLIC_PADDLE_CLIENT_TOKEN;
  const env = envOverride || process.env.NEXT_PUBLIC_PADDLE_ENV || "sandbox";

  if (!token) {
    throw new Error("Paddle is not configured (missing client token)");
  }

  await loadScript();
  if (!window.Paddle) {
    throw new Error("Paddle.js failed to initialize");
  }

  if (!paddleInitialized) {
    if (env === "sandbox") {
      window.Paddle.Environment.set("sandbox");
    }
    window.Paddle.Initialize({
      token,
      eventCallback: (data) => currentEventListener?.(data),
    });
    paddleInitialized = true;
  }

  return window.Paddle;
}

/**
 * Opens Paddle.js checkout overlay for a transaction.
 * Resolves with completed: true when paid, or completed: false when closed.
 */
export async function openPaddleCheckout(
  transactionId: string,
  clientTokenOverride?: string,
  envOverride?: string,
): Promise<{ completed: boolean }> {
  const paddle = await getPaddle(clientTokenOverride, envOverride);
  return new Promise((resolve) => {
    currentEventListener = (data) => {
      if (data.name === "checkout.completed") {
        currentEventListener = null;
        resolve({ completed: true });
      } else if (data.name === "checkout.closed") {
        currentEventListener = null;
        resolve({ completed: false });
      }
    };
    paddle.Checkout.open({
      transactionId,
      settings: { displayMode: "overlay", variant: "one-page" },
    });
  });
}
