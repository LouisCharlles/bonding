# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Repositories

This project has two separate repositories side by side:

| Repo | Path | Stack |
|---|---|---|
| Backend (Django) | `/home/luis/Documentos/bonding/` | Python 3.12, Django 5.2, DRF, Channels, PostgreSQL, Redis |
| Frontend (React) | `/home/luis/Documentos/soul-match-glide/` | React 18, TypeScript, Vite, Tailwind, shadcn/ui |

---

## Backend — Commands

```bash
# Run development server (ASGI via Daphne for WebSocket support)
python manage.py runserver

# Run migrations
python manage.py migrate

# Create a new migration
python manage.py makemigrations

# Apply a specific migration
python manage.py migrate bonding 0012

# Django shell
python manage.py shell

# Run tests
python manage.py test bonding
```

Config is via `.env` (python-decouple). Required vars: `SECRET_KEY`, `DATABASE_URL`, `ALLOWED_HOSTS`, `REDIS_URL`. Optional: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `GOOGLE_MAPS_API_KEY`, `FOURSQUARE_API_KEY`, `AWS_REKOGNITION_ENABLED`, `VERIFICATION_PROVIDER`, `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `SUPABASE_*`, `EMAIL_*`, `FRONTEND_URL`.

---

## Frontend — Commands

```bash
# Dev server (http://localhost:5173)
npm run dev

# Build
npm run build

# Lint
npm run lint

# Run tests (Vitest)
npm run test

# Watch mode
npm run test:watch
```

Config via `.env`: `VITE_API_BASE_URL` (defaults to `http://127.0.0.1:8000`), `VITE_STRIPE_PUBLISHABLE_KEY`.

---

## Backend Architecture

### Project Layout

```
setup/          Django project config (settings, urls, asgi, wsgi)
bonding/
  models/       One file per model, re-exported from __init__.py
  views/        One file per resource group (connections.py, payments.py, etc.)
  services/     Business logic extracted from views
    wallet.py             ribbon/heart/rewind ledger operations
    external_integrations.py  Stripe, Google Maps, Foursquare, Spotify (urllib only, no requests)
    realtime.py           publish_group_event / publish_to_users helpers
    verification.py       AWS Rekognition face comparison
    presence.py           online/offline tracking via Redis
    blocks.py             blocked user ID lookups
  serializers.py  All DRF serializers in one file
  consumers.py    Django Channels WebSocket consumers
  signals.py      post_save signals for notifications and wallet bootstrap
  routing.py      WebSocket URL patterns
```

### Key Models

- **User** — custom `AUTH_USER_MODEL = 'bonding.User'`
- **Profile** — 1:1 with User; `premium_tier` field: `free | plus | gold | platinum`; `is_verified` → `ProfileVerificationAttempt.status == APPROVED`
- **Connection** — `from_user → to_user` with `status: like | pass | superlike`; mutual like → Match is auto-created in `ConnectionViewSet.create()` inside a `@transaction.atomic`
- **Match** — `user1` / `user2` (ordered by `user.id`); has a 1:1 `Conversation`
- **Wallet** — 1:1 with User; balances: `ribbons_balance`, `hearts_balance`, `rewinds_balance`; every change must also write a `WalletLedger` entry; 100 ribbons auto-converts to 1 heart via `_normalize_balances()`
- **Message** — belongs to Conversation; `message_type: text | image | video | story_reply | date_suggestion`; `provider_payload` JSONField for typed message metadata

### Wallet / Currency Rules

- Ribbons (laços): earned by daily like (+1), watching videos (+2, max 3/day)
- 100 ribbons → 1 heart (auto-converted via `_normalize_balances`)
- Hearts: spent via `consumeRewind` (1 heart → 2 rewinds) or to unlock Likes visibility (50 ribbons for 2h session)
- Wallet service functions live in `bonding/services/wallet.py` — always use them, never modify `Wallet` fields directly

### Real-time (Django Channels + Redis)

WebSocket paths (defined in `bonding/routing.py`):
- `ws/presence/` → `PresenceConsumer` (global group `presence_global`)
- `ws/stories/` → `StoriesConsumer` (per-user group `stories_{user_id}`)
- `ws/conversations/<id>/` → `ConversationConsumer` (group `conversation_{id}`)

Authentication: JWT token passed as `?token=` query param. Consumers close with code `4401` if unauthenticated.

To push an event from a view/signal: call `realtime.publish_group_event(group_name, event_dict)`. The consumer broadcasts it to the WebSocket via `broadcast_event`.

### Stripe Payments

- `POST /payments/intents/` → creates `PaymentIntent` via `create_stripe_payment_intent()` in `external_integrations.py` (raw urllib, no stripe SDK)
- `POST /payments/webhooks/stripe/` → verifies signature, handles `payment_intent.succeeded` → creates `Subscription` + updates `Profile.premium_tier`
- Webhook secret verified via HMAC-SHA256 in `verify_stripe_signature()`

### Migrations

Data migrations are placed sequentially in `bonding/migrations/`. Seed migrations use `RunPython` with both forward and reverse functions. Current highest: `0012_message_date_suggestion.py`.

---

## Frontend Architecture

### State Management

Two React Contexts wrap the app:

1. **`AuthContext`** (`src/lib/auth.tsx`) — `user: UserSummary | null`, `login`, `logout`, `signUp`. Bootstraps from `GET /auth/me/` on load.
2. **`AppExperienceContext`** (`src/contexts/AppExperienceContext.tsx`) — ribbons, hearts, rewinds, isPremium, discovery filters, swipe count, customization. Persisted to `localStorage` under key `bonding_app_experience`. Backend is authoritative — call `refreshWallet()` after any server-side currency change (like, video watch, payment).

### Routing / Guards

```
/                       → Login (unauthenticated)
/signup, /forgot-password, etc.
/app/profile-setup      → ProtectedRoute only
/app/verify             → ProtectedRoute only
/app/**                 → ProtectedRoute → ProfileCompletionRoute → MainLayout
```

`ProfileCompletionRoute` fetches `/profiles/me/` and redirects to `/app/profile-setup` if incomplete, or to `/app/verify` if `!profile.verified`.

### API Layer

All server calls go through `src/lib/api.ts`. The `request()` helper:
- Auto-attaches `Authorization: Bearer <token>`
- Retries once with token refresh on 401 using `POST /api/token/refresh/`
- Throws `ApiError` with `.status` on non-2xx

Key naming convention: `ApiXxx` = raw API shape (snake_case), `AppXxx` = mapped frontend type (camelCase). Every `ApiMessage` → `AppMessage` mapping goes through `mapApiMessageToAppMessage()`.

### Real-time (Frontend)

`RealtimeContext` (`src/contexts/RealtimeContext.tsx`) manages WebSocket connections. URL builder: `buildWebSocketUrl(path)` in `src/lib/realtime.ts` — converts http→ws base URL and appends `?token=`.

### UI Components

- All shadcn/ui components are in `src/components/ui/`
- `ProfileCard` — supports `viewMode: "discover" | "likes"` and `onLikeBack` prop
- `PaymentModal` — lazy-loads Stripe.js, mounts Payment Element; tabs: credit / debit / pix
- `AppExperienceContext.consumeRewind()` — premium: free; non-premium: costs 1 heart, grants 2 rewinds

### Key Frontend/Backend Contracts

- `Connection.status` values: `"like" | "pass" | "superlike"`
- Match fields: `user1` / `user2` (not `user_1` / `user_2`)
- `Message.provider_payload` (JSON) — required for `date_suggestion` type; must contain `name` and `maps_url`
- `sendMessage()` in api.ts uses FormData; `provider_payload` is JSON-stringified before appending
- `fetchDateSuggestions(matchId, radiusKm)` — backend accepts `?radius=` (1–100 km)
