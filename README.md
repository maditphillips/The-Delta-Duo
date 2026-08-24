# The Delta Duo — Fantasy Football Lab

A green-chalkboard data dashboard for The Delta Duo's fantasy football research:

- **Wide Receiver** — *The Two Doors of Fantasy Relevance*
- **Quarterback** — *The Quarterback Cliff*
- **Running Back** — *The Running Back Cliff* + the third-down study
- **Rankings** — positional and overall boards, updated by CSV upload (stored in Supabase)

Built with Next.js (App Router) + Recharts, deployed to **Cloudflare Workers** via
[`@opennextjs/cloudflare`](https://opennext.js.org/cloudflare).

## Local development

```bash
npm install
npm run dev          # http://localhost:3000
npm run build        # production build (also runs type checks)
npm run preview      # build + run the actual Cloudflare worker locally
```

## Deploying to Cloudflare

1. Push this repo to GitHub.
2. In the Cloudflare dashboard: **Workers & Pages → Create → Import a repository**, pick this repo.
   - Build command: `npx opennextjs-cloudflare build`
   - Deploy command: `npx opennextjs-cloudflare deploy`
3. Add the environment variables below under the Worker's **Settings → Variables and Secrets**.

Or deploy from your machine: `npm run deploy` (requires `wrangler login`).

## Supabase (rankings storage)

Rankings live in Supabase so the boards update instantly without a redeploy:

1. Create a project at [supabase.com](https://supabase.com).
2. Run `supabase/migrations/0001_rankings.sql` in the SQL editor.
3. Set these variables (see `.env.example`; locally put them in `.env.local`):
   - `NEXT_PUBLIC_SUPABASE_URL`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   - `SUPABASE_SERVICE_ROLE_KEY` *(server-only — never expose to the browser)*
   - `RANKINGS_UPLOAD_KEY` — any passphrase; typing it on the `/rankings` page authorizes an upload.

Uploads go through `POST /api/rankings` on the server using the service role; the browser never
holds a write credential. Reads are public (RLS `select` policies only). Each upload creates a new
ranking *set*, so history is preserved and the newest set is what the board shows.

**CSV format:** headers are matched loosely — `rank, player, team, position, note` (only
`player`/`name` is required; row order stands in for a missing rank column).

## Where the data lives

The study numbers are typed TypeScript modules in `src/data/`:

- `qb.ts` — the Quarterback Cliff tables
- `rb.ts` — the RB third-down study tables
- `wr.ts` — WR findings (currently the numbers cited across the series; expands when the full
  Two Doors dataset is imported)
- `crossStudy.ts` — the cross-study callbacks table

To update a number, edit the module and redeploy — every chart and table reads from these files.

## Adding the Stripe paywall later

The pieces are already shaped for it:

1. **Auth** — add Supabase Auth (email or OAuth). The Supabase project is already wired.
2. **Subscriptions** — add a `subscriptions` table keyed by Supabase `user_id`, written by a
   Stripe webhook (`checkout.session.completed`, `customer.subscription.updated/deleted`) at
   `src/app/api/stripe/webhook/route.ts`.
3. **Checkout** — a route handler that creates a Stripe Checkout Session for a price ID.
4. **Gate** — a Next.js `middleware.ts` (or a check in each page layout) that reads the Supabase
   session and the subscription row, and redirects non-subscribers from the position pages to a
   preview/upgrade page.
5. Secrets: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY`.

Because the site renders on Cloudflare Workers (not static export), server-side gating like this
is a drop-in addition — no re-architecture needed.
