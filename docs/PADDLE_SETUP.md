# Paddle Billing Setup Guide for Torii

This guide details everything you need to set up in the **Paddle Dashboard** (both Sandbox and Production) to enable online payments and credit pass purchasing in Torii.

---

## 1. Get Your Paddle Sandbox Credentials

1. Create or log in to your Paddle Sandbox account at [https://sandbox-vendors.paddle.com](https://sandbox-vendors.paddle.com) (use [https://vendors.paddle.com](https://vendors.paddle.com) for production).
2. **API Key**:
   - Go to **Developer Tools** > **Authentication** > **API keys**.
   - Click **"+ New API key"**.
   - Grant the following permissions:
     - `product.read`, `product.write`
     - `price.read`, `price.write`
     - `customer.read`, `customer.write`
     - `transaction.read`, `transaction.write`
   - Copy the generated key (starts with `pdl_sdbx_...` in sandbox) → `TORII_PADDLE_API_KEY`.
3. **Client-side Token**:
   - Go to **Developer Tools** > **Authentication** > **Client-side tokens**.
   - Click **"+ Generate client-side token"**.
   - Copy the token (starts with `test_...` in sandbox) → `TORII_PADDLE_CLIENT_TOKEN` (backend) and `NEXT_PUBLIC_PADDLE_CLIENT_TOKEN` (frontend).

---

## 2. Approve Your Checkout Domain (Mandatory Step)

Paddle only opens checkout sessions on pre-approved domains to protect customers against phishing and unauthorized iframe overlays.

1. Go to **Checkout** > **Checkout settings** > **Checkout domains**.
2. Click **"Add domain"**.
3. Add your application domain:
   - For local development: Your ngrok or Cloudflare tunnel domain (e.g., `https://xxxx.ngrok-free.app`) or `localhost:3000`.
   - For staging/production: Your actual domain (e.g., `torii.visa` or `torii.app`).
4. Set `TORII_PADDLE_DEFAULT_CHECKOUT_URL` in `.env` if you want a fallback hosted checkout link, or leave it blank to default to Torii's on-page Paddle.js overlay.

---

## 3. Configure Webhook Destination & Secret

Paddle pushes notifications to Torii when payments are completed, refunded, or failed.

1. Go to **Developer Tools** > **Notifications** > **"+ New destination"**.
2. Set **Destination Type** to `Webhook`.
3. Set **URL** to:
   ```
   https://<your-api-domain>/backend/v1/payments/webhooks/paddle
   ```
   *(For local testing with a tunnel, e.g.: `https://xxxx.ngrok-free.app/backend/v1/payments/webhooks/paddle`)*.
4. **Events to Select** (select these 4 events):
   - `transaction.completed` *(triggers automatic credit pass grant)*
   - `transaction.paid` *(triggers automatic credit pass grant)*
   - `transaction.canceled` *(marks checkout cancelled)*
   - `transaction.payment_failed` *(marks checkout failed)*
5. Click **"Save destination"**.
6. Open the newly created destination, copy the **Webhook Secret** (starts with `pdl_ntfset_...`) → `TORII_PADDLE_WEBHOOK_SECRET`.

---

## 4. Environment Variables Reference

Add the following keys to your root `.env` file (copied from `.env.example`):

```bash
# ── Payments (Paddle Billing) ──────────────────────────────────────────────────
# Global enable/disable default (can be toggled in Admin settings anytime)
TORII_PAYMENTS_ENABLED=true

# Paddle environment: "sandbox" or "production"
TORII_PADDLE_ENV=sandbox

# Secret API Key from Developer Tools > Authentication > API keys
TORII_PADDLE_API_KEY=pdl_sdbx_...

# Client-side Token from Developer Tools > Authentication > Client-side tokens
TORII_PADDLE_CLIENT_TOKEN=test_...
NEXT_PUBLIC_PADDLE_CLIENT_TOKEN=test_...
NEXT_PUBLIC_PADDLE_ENV=sandbox

# Webhook Secret from Developer Tools > Notifications
TORII_PADDLE_WEBHOOK_SECRET=pdl_ntfset_...

# Optional: Pre-configured live catalog price mapping (required in production)
TORII_PADDLE_PRICE_IDS={}

# Optional: Default checkout URL redirect
TORII_PADDLE_DEFAULT_CHECKOUT_URL=
```

---

## 5. Admin Payment Enable / Disable Switch

Torii allows administrators to turn online payments on or off in real-time without restarting any services:

### How to Toggle:
1. Log in to the Torii web application as an administrator (`admin@example.com`).
2. Navigate to **Admin** > **Settings** (`/admin/settings`).
3. Scroll to the **"Online Payments & Billing (Paddle)"** card.
4. Toggle the **"Enable Paddle Online Payments"** switch.

### Behavior When Disabled:
- **For Applicants**:
  - The **Top Up Modal** (`TopUpModal.tsx`) displays an alert: *"Online Payments Temporarily Disabled — scheduled maintenance"*.
  - The **Purchase Credits** button is disabled.
  - Any direct API calls to `POST /v1/payments/checkout` return `403 Forbidden` (`"Online payments and credit purchases are temporarily disabled by the administrator."`).
  - **Existing Credits**: Applicants can continue to use all platform features with their existing credit balance; existing balances are never frozen.
- **For Admins**:
  - The Admin portal clearly shows `⚠ Payments Disabled (Maintenance Mode)` in amber.
  - Admins can re-enable payments at any time with a single click.

---

## 6. Testing End-to-End in Sandbox

1. Ensure `TORII_PADDLE_ENV=sandbox` and `NEXT_PUBLIC_PADDLE_ENV=sandbox`.
2. Open Torii web application, log in as an applicant, and open the credit top-up modal (or visit `/credits`).
3. Select any credit pack:
   - **Starter**: 1 Pass ($19.00 / ¥2,800)
   - **Standard**: 3 Passes ($39.00 / ¥5,800)
   - **Family**: 5 Passes ($59.00 / ¥8,900)
4. Click **"Purchase Credits"**.
5. The Paddle.js overlay will appear.
6. Enter a [Paddle Sandbox Test Card](https://developer.paddle.com/concepts/payment-methods/credit-debit-card#sandbox-testing-card-numbers):
   - **Card number**: `4242 4242 4242 4242`
   - **Expiry**: Any future date (e.g. `12/28`)
   - **CVC**: Any 3 digits (e.g. `123`)
   - **Postal code**: Any postal code (e.g. `100-0001` or `90210`)
7. Complete checkout.
8. Paddle will send a `transaction.completed` webhook to Torii, and Torii will atomically credit the passes to the user's account and record the transaction in the ledger.

---

## 7. Production Migration Checklist

When switching to live Paddle production:

1. [ ] Complete company verification in the Live Paddle Dashboard ([https://vendors.paddle.com](https://vendors.paddle.com)).
2. [ ] Submit your domain (`torii.visa` / `torii.app`) under **Checkout domains** for live approval.
3. [ ] In Paddle Live Dashboard > **Catalog** > **Products & Prices**, create the 3 credit pack products with their USD and JPY prices.
4. [ ] Record the price IDs (`pri_...`) into `TORII_PADDLE_PRICE_IDS`:
   ```json
   {
     "starter": { "USD": "pri_01...", "JPY": "pri_02..." },
     "standard": { "USD": "pri_03...", "JPY": "pri_04..." },
     "family": { "USD": "pri_05...", "JPY": "pri_06..." }
   }
   ```
5. [ ] Generate live API key (`pdl_live_...`), client-side token (`live_...`), and live notification destination webhook secret.
6. [ ] Set `TORII_PADDLE_ENV=production` and `NEXT_PUBLIC_PADDLE_ENV=production`.
