# Setup

Steps required to get a new environment fully operational. Local dev setup is handled by config files; the items below are manual one-time steps in external dashboards.

---

## Supabase — production dashboard steps

### 1. Set Site URL and redirect allowlist

**Dashboard → Authentication → URL Configuration**

| Field | Value |
|---|---|
| Site URL | `https://<your-production-domain>` |
| Redirect URLs | `https://<your-production-domain>/**` |

### 2. Configure Resend SMTP

**Dashboard → Project Settings → Authentication → SMTP Settings** — enable Custom SMTP.

| Field | Value |
|---|---|
| Host | `smtp.resend.com` |
| Port | `465` |
| Username | `resend` |
| Password | Resend API key |
| Sender name | `Game On Tabletop` |
| Sender email | `noreply@<your-verified-domain>` |

> The default Supabase SMTP only delivers to project team members and has a low hourly rate limit. Custom SMTP is required before auth emails can reach real users.

### 3. Copy email templates

**Dashboard → Authentication → Email Templates**

Paste the HTML from each file into the matching tab:

| Template file | Dashboard tab |
|---|---|
| `supabase/templates/confirmation.html` | Confirm signup |
| `supabase/templates/recovery.html` | Reset Password |
| `supabase/templates/invite.html` | Invite User |
| `supabase/templates/email_change.html` | Change Email |

---

## BGG API token

The BoardGameGeek API requires an application token (`BGG_APPLICATION_TOKEN`). Without it the `/api/bgg/*` endpoints return `503`.

### Local (Docker)

Add the token to the root `.env` file — Docker Compose interpolates it automatically:

```
BGG_APPLICATION_TOKEN=your-token-here
```

### GitHub secret

The deploy workflow reads this secret to push it to Vercel on every deploy to `main`.

**GitHub → Repository → Settings → Secrets and variables → Actions → New repository secret**

| Name | Value |
|---|---|
| `BGG_APPLICATION_TOKEN` | your token |

### Vercel

The deploy workflow upserts the token into the Vercel backend project automatically once the GitHub secret above is set. To set it manually instead:

**Vercel → gameontabletop-backend → Settings → Environment Variables**

| Key | Value | Environment |
|---|---|---|
| `BGG_APPLICATION_TOKEN` | your token | Production |

---

## Local development

Start the local Supabase stack (replaces docker-compose `db` service):

```bash
supabase start
```

Auth emails sent during local dev are captured by Inbucket — no real emails are sent.
View them at **http://localhost:54324**.

Stop the stack:

```bash
supabase stop
```
