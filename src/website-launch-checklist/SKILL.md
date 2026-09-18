---
name: website-launch-checklist
description: "Comprehensive pre-launch checklist for shipping a website to production. TRIGGER when the user says 'launch checklist', 'pre-launch', 'ready to publish', 'מוכן להשקה', or asks to prepare a website for production/public launch. Covers infrastructure, auth/security, SEO, analytics, performance, accessibility, legal, content/UX, and a final pre-publish sweep, organized in execution order."
---

# Website Launch Checklist

## Trigger
When the user says "launch checklist", "pre-launch", "ready to publish", "מוכן להשקה", or asks to prepare a website for production/public launch.

## Overview
Comprehensive checklist distilled from real-world experience launching a production Next.js site (a multi-hundred-page directory site). Covers everything from infrastructure to SEO to legal compliance. Organized in execution order — each phase must be verified before moving to the next.

---

## Phase 1: Infrastructure & Deployment

### Hosting & Domain
- [ ] Domain purchased and DNS configured (A record + CNAME for www)
- [ ] SSL/HTTPS working (check padlock icon)
- [ ] www → non-www redirect (or vice versa) — pick one canonical URL
- [ ] Environment variables set in hosting platform (Vercel/Railway/etc.)
- [ ] Production database accessible from hosting (check connection string, SSL)
- [ ] `.env.example` exists with all required var names (no values)

### Database
- [ ] Production database provisioned (not dev/local)
- [ ] Migrations applied to production
- [ ] Indexes on all filtered/sorted columns
- [ ] Connection pooling configured (PgBouncer for Supabase)
- [ ] Direct URL configured for migrations (separate from pooled URL)

### Build & Deploy
- [ ] `npm run build` passes with zero errors
- [ ] `npm run lint` passes
- [ ] No TypeScript errors
- [ ] Auto-deploy on push to main branch working
- [ ] Environment variables include all secrets (DB, auth, API keys, etc.)

#### Lesson Learned — Supabase + Prisma on Vercel
- Prisma needs `ssl: { rejectUnauthorized: false }` for Supabase on serverless
- Use port 6543 (pooled) for app, port 5432 (direct) for migrations
- PrismaAdapter for NextAuth requires `emailVerified DateTime?` on User model — silent failure without it (only visible in Vercel Runtime Logs as `adapter_error_createUser`)

---

## Phase 2: Authentication & Security

### Auth
- [ ] Login flow works end-to-end (test with real account)
- [ ] Logout works and clears session
- [ ] Protected routes redirect to login
- [ ] Admin routes check role (not just auth)
- [ ] OAuth redirect URIs include production domain
- [ ] JWT strategy (not database sessions) for serverless environments

### Security Headers
- [ ] `X-Content-Type-Options: nosniff`
- [ ] `X-Frame-Options: DENY`
- [ ] `X-XSS-Protection: 1; mode=block`
- [ ] `Referrer-Policy: strict-origin-when-cross-origin`
- [ ] `Permissions-Policy` restricting camera/mic/geo
- [ ] `Strict-Transport-Security` (HSTS)
- [ ] `poweredByHeader: false` in next.config

### Input & API Security
- [ ] Rate limiting on write endpoints (contact, signup, forms)
- [ ] Input validation on all API routes (length, format, required fields)
- [ ] No hardcoded secrets in code (grep for API keys, passwords)
- [ ] CORS configured correctly
- [ ] File upload validation (type, size limits)
- [ ] SQL injection prevented (ORM parameterized queries)
- [ ] XSS prevented (no dangerouslySetInnerHTML with user input)

#### Lesson Learned — Security Audit
- Always use a field whitelist for PUT/PATCH (not spread operator)
- Never expose internal IDs or stack traces in error responses
- Rate limit format: per IP + per endpoint + sliding window
- Remove all hardcoded fallback secrets (even for webhooks)

---

## Phase 3: SEO & Discoverability

### Essential Meta Tags (verify in page source)
- [ ] `<title>` unique per page
- [ ] `<meta name="description">` unique per page
- [ ] `<meta name="viewport">` with device-width
- [ ] `<link rel="canonical">` on all pages
- [ ] `<html lang="xx">` set correctly

### Open Graph & Social
- [ ] `og:title`, `og:description`, `og:image` on all pages
- [ ] `og:image` is at least 1200x630px for best display
- [ ] Twitter card meta tags
- [ ] Test share preview: paste URL in WhatsApp/Telegram/Facebook
- [ ] OG image has visible text (not just a logo)

### Technical SEO
- [ ] `robots.txt` exists — blocks /admin, /api, /auth, /dashboard
- [ ] `sitemap.xml` exists — dynamic, includes all public pages
- [ ] Sitemap submitted to Google Search Console
- [ ] JSON-LD structured data on key pages (Organization, Person, Product, etc.)
- [ ] Proper heading hierarchy (H1 → H2 → H3, one H1 per page)
- [ ] Alt text on all images
- [ ] Clean URLs (slugs, no query params for main content)
- [ ] 404 page returns HTTP 404 status (not 200)

### Google Search Console Setup
- [ ] Property added (domain or URL prefix)
- [ ] Ownership verified (via GA, DNS TXT, or HTML tag)
- [ ] Sitemap submitted
- [ ] No critical errors in Coverage report

#### Lesson Learned — GSC Verification
- Domain verification via GoDaddy auto-DNS can fail — URL prefix + Google Analytics verification is more reliable
- If GA is already installed, GSC detects it automatically
- Sitemap format: `https://www.domain.com/sitemap.xml`

---

## Phase 4: Analytics & Monitoring

### Analytics
- [ ] Google Analytics 4 installed (or Plausible/Umami)
- [ ] GA tracking ID in environment variable (NEXT_PUBLIC_GA_ID)
- [ ] Verify real-time data flowing in GA dashboard
- [ ] Key events tracked (page views at minimum)

### Error Monitoring (optional but recommended)
- [ ] Global error boundary (error.tsx in Next.js)
- [ ] Loading states (loading.tsx)
- [ ] Console.error for server-side errors (visible in hosting logs)
- [ ] Zero console.log in production code (only console.error/warn)

#### Lesson Learned — GA4 Setup
- `NEXT_PUBLIC_` prefix required for client-side env vars in Next.js
- GA shows "data collection not active" until code is deployed AND env var is set
- Takes 24-48 hours for first data to appear
- Add env var to Vercel BEFORE deploy, or redeploy after adding

---

## Phase 5: Performance

### Core Web Vitals (run Lighthouse)
- [ ] Performance score ≥ 80
- [ ] LCP (Largest Contentful Paint) < 2.5s
- [ ] FID/INP (Interaction to Next Paint) < 200ms
- [ ] CLS (Cumulative Layout Shift) < 0.1
- [ ] TBT (Total Blocking Time) < 300ms

### Image Optimization
- [ ] All images served through optimizer (next/image or CDN)
- [ ] Lazy loading on below-fold images (`loading="lazy"`)
- [ ] Explicit width/height on images (prevents CLS)
- [ ] WebP/AVIF format configured
- [ ] Remote image domains configured in next.config

### JavaScript & Loading
- [ ] Heavy components dynamically imported (`next/dynamic`, `ssr: false` for maps)
- [ ] No render-blocking scripts
- [ ] Bundle size reasonable (check with `@next/bundle-analyzer`)
- [ ] Lists with 50+ items virtualized or paginated (infinite scroll)

### Caching
- [ ] Static pages use ISR with appropriate revalidate intervals
- [ ] API responses have Cache-Control headers for public data
- [ ] Assets cached by CDN (Vercel handles automatically)

#### Lesson Learned — Performance
- react-virtuoso caused SSR hydration issues — IntersectionObserver infinite scroll was simpler and more reliable
- React.memo() on list cards prevents unnecessary re-renders
- Sort results to show items with images first (better visual impression)
- Debounce search inputs and map viewport changes (300ms)

---

## Phase 6: Accessibility

### WCAG Basics
- [ ] Accessibility score ≥ 90 (Lighthouse)
- [ ] Color contrast ratio ≥ 4.5:1 for normal text
- [ ] All interactive elements have min 44x44px touch target
- [ ] All images have alt text
- [ ] Form inputs have labels
- [ ] Focus indicators visible on keyboard navigation
- [ ] Skip-to-content link (nice to have)

#### Lesson Learned — Contrast
- Semi-transparent text (text-white/70) on colored backgrounds often fails contrast
- Test with Lighthouse or axe DevTools, not by eye

---

## Phase 7: Legal & Compliance

### Required Pages
- [ ] Privacy Policy — what data collected, how used, third parties, cookies, user rights
- [ ] Terms of Service — usage terms, liability, IP, content rules
- [ ] Both pages linked from footer
- [ ] Last updated date on both pages
- [ ] Contact method provided in both

### Privacy Specifics
- [ ] List all third-party services that receive data (Analytics, CDN, email provider, etc.)
- [ ] Cookie usage disclosed
- [ ] User rights described (access, correction, deletion)
- [ ] Compliant with local law (Israeli Privacy Protection Law, GDPR if relevant)

### Cookie Consent (if applicable)
- [ ] Cookie banner shown on first visit (required by GDPR for EU users)
- [ ] Option to decline non-essential cookies

---

## Phase 8: Content & UX

### Content Quality
- [ ] No placeholder text (Lorem ipsum, TODO, TBD)
- [ ] No broken links (check with crawler or manual)
- [ ] Consistent language and terminology throughout
- [ ] Contact information correct and working
- [ ] About page tells a compelling story

### Responsive Design
- [ ] Test on mobile (375px width)
- [ ] Test on tablet (768px width)
- [ ] Test on desktop (1280px width)
- [ ] No horizontal scroll on any viewport
- [ ] Touch targets ≥ 44px on mobile
- [ ] Forms usable on mobile keyboard

### Key Flows (test manually)
- [ ] Homepage loads and displays content
- [ ] Search/filter works
- [ ] Detail pages load correctly
- [ ] Contact form submits successfully
- [ ] Email notifications arrive
- [ ] Login/logout flow works
- [ ] Admin panel accessible to admins only
- [ ] 404 page shows for invalid URLs

#### Lesson Learned — Testing
- AI reviewers (Grok, ChatGPT) can't render JS-heavy sites — they report missing meta tags that actually exist via Next.js metadata API
- Always test forms on production (not just dev) — API keys, email services, and auth may behave differently
- Test WhatsApp/Telegram share preview — paste the URL and check the card

---

## Phase 9: Pre-Publish Final Checks

### The 10-Minute Final Sweep
1. Open production URL in incognito browser
2. Check homepage loads fast with content
3. Click through: home → detail page → contact → about → legal pages
4. Test on phone (real device, not just DevTools)
5. Submit contact form — verify email arrives
6. Share URL on WhatsApp — check preview card
7. Check Google Search Console — no critical errors
8. Check GA real-time — verify tracking works
9. Run Lighthouse one final time
10. Check Vercel/hosting dashboard — no failed deploys

### Post-Launch (first 48 hours)
- [ ] Monitor error logs in hosting platform
- [ ] Check GA for real traffic data
- [ ] Verify Google is indexing pages (Search Console → Coverage)
- [ ] Monitor email deliverability (check spam folders)
- [ ] Get feedback from 3-5 real users
- [ ] Fix any issues found immediately

---

## Quick Reference: Essential Files for Next.js Launch

```
src/app/
  layout.tsx          — metadata, viewport, OG tags, GA script, fonts
  page.tsx            — homepage with JSON-LD Organization
  not-found.tsx       — custom 404 page (Hebrew)
  error.tsx           — global error boundary
  loading.tsx         — loading spinner
  robots.ts           — search engine crawl rules
  sitemap.ts          — dynamic sitemap
  terms/page.tsx      — terms of service
  privacy/page.tsx    — privacy policy

next.config.ts        — security headers, image domains, redirects
.env.example          — documented env var names
```

## Stack Recommendations (from experience)

| Need | Recommended | Why |
|------|------------|-----|
| Hosting | Vercel | Zero-config Next.js, auto-SSL, preview deploys |
| Database | Supabase (PostgreSQL) | Free tier, managed, connection pooling |
| ORM | Prisma | Type-safe, migrations, studio |
| Auth | NextAuth + Google | Quick setup, JWT for serverless |
| Email | Resend | Simple API, free tier, good deliverability |
| Images | Cloudinary | Auto-optimization, face detection crop |
| Analytics | GA4 | Free, comprehensive, integrates with GSC |
| Maps | Leaflet + OpenStreetMap | Free, no API key, Hebrew labels in Israel |
| Icons | Lucide React | Tree-shakeable, consistent, 1000+ icons |
