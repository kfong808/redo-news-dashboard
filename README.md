# REDO News Dashboard

A free, always-on dashboard that scrapes ecommerce news every hour and surfaces opportunities and threats for REDO. Color-coded, accessible from any browser on REDO's WiFi (or anywhere with internet).

**How it works:** GitHub Actions runs the scraper hourly, writes results to `news.json`, and commits that file back to your repo. GitHub Pages serves the static dashboard at a public URL. Zero servers to maintain. Total cost: $0.

---

## What you need

1. A GitHub account (free). If you don't have one, sign up at [github.com](https://github.com).
2. About 20 minutes for the one-time setup.
3. *(Optional, can add later)* An Anthropic API key for smarter classification. Get one at [console.anthropic.com](https://console.anthropic.com) — you get $5 in free credit on signup, which lasts roughly 6 months at this dashboard's usage.

Without an API key the dashboard still works — it falls back to keyword-based classification, less accurate but free forever.

---

## Setup (one-time, about 20 min)

### Step 1: Create the repository

1. Go to [github.com/new](https://github.com/new).
2. Repository name: `redo-news-dashboard` (any name works, but this one matches the folder).
3. Choose **Public**. (GitHub Pages free tier requires public repos.)
4. Do NOT check "Add a README file." Leave it empty.
5. Click **Create repository**.

### Step 2: Upload these files

1. On the new empty repo page, click **uploading an existing file** (it's a link in the middle of the page).
2. Open the `redo-news-dashboard` folder on your Desktop in Finder.
3. Drag every file AND the `.github` folder into the GitHub upload area.
   - If GitHub doesn't show the `.github` folder, in Finder press `Cmd+Shift+.` to reveal hidden folders, then drag it in.
4. Scroll down, leave "Commit directly to the `main` branch" selected, click **Commit changes**.

### Step 3: Enable GitHub Pages

1. On your repo page, click **Settings** (top right tab).
2. In the left sidebar, click **Pages**.
3. Under **Build and deployment**, set:
   - Source: **Deploy from a branch**
   - Branch: **main** / **/ (root)**
4. Click **Save**.
5. Wait about 60 seconds, then refresh the Pages settings page. You'll see a green box with your dashboard URL, something like:
   `https://YOUR-USERNAME.github.io/redo-news-dashboard/`

### Step 4: Allow GitHub Actions to commit back to your repo

1. Still in **Settings**, in the left sidebar click **Actions** → **General**.
2. Scroll to **Workflow permissions** at the bottom.
3. Select **Read and write permissions**.
4. Click **Save**.

### Step 5: Trigger the first refresh

1. Go to your repo's **Actions** tab (top of the page).
2. If prompted, click **I understand my workflows, go ahead and enable them**.
3. In the left sidebar, click **Refresh news dashboard**.
4. Click the **Run workflow** dropdown on the right, then **Run workflow** (green button).
5. Wait about 90 seconds. The run will show a green checkmark when done.
6. Open your dashboard URL from Step 3. You should see stories with green (opportunities) and red (threats) tags.

From now on, the workflow runs automatically every hour.

---

## Optional: Upgrade to LLM-based classification (later)

When you're ready for better classification:

1. Sign up at [console.anthropic.com](https://console.anthropic.com), grab your API key from the **API Keys** section.
2. In your GitHub repo, go to **Settings** → **Secrets and variables** → **Actions**.
3. Click **New repository secret**.
4. Name: `ANTHROPIC_API_KEY` (exact spelling, all caps with underscores).
5. Value: paste your API key.
6. Click **Add secret**.

The next hourly run automatically picks up the key and switches to LLM classification. No redeploy needed. The dashboard's "Classifier" indicator will switch from `keyword` to `llm` on the next refresh.

If you ever want to pause API usage, just delete the secret — the system falls back to keyword mode automatically.

---

## Using the dashboard

- **All / Opportunities / Threats** filter buttons at the top.
- **Search box** filters by any text in the title, summary, or source.
- **Color coding:** green left border = opportunity, red left border = threat.
- **Tag intensity:** darker tag = high confidence, lighter = medium or low.
- **Auto-refresh:** the page silently re-fetches the news every 5 minutes while open, so you don't need to manually reload.

---

## What it scrapes

**Always-on feeds:**

- Practical Ecommerce, Modern Retail, Retail Dive, eCommerce Bytes
- Hacker News
- r/shopify, r/ecommerce

**Google News searches:**

Klaviyo, Yotpo, Loop Returns, Attentive, Omnisend, Postscript, Shopify, Mailchimp, ShipStation, Narvar, agentic commerce, AI shopping agent, post-purchase ecommerce, abandoned cart recovery, DTC ecommerce, ecommerce SaaS, Shopify Plus, returns management software, headless commerce

To add or remove sources, edit `scraper.py` (the `FEEDS` and `GOOGLE_NEWS_TERMS` lists at the top) and push the change to GitHub.

---

## Troubleshooting

**The dashboard URL says "404 - file not found."** GitHub Pages takes 1-2 minutes to publish after first enabling. Wait and refresh. If it persists, check Settings → Pages and confirm the source is set to `main` branch root.

**The dashboard loads but says "No data yet."** The first Actions run hasn't completed. Go to the Actions tab and check the most recent run. If it failed, click into it to see the error. If it hasn't run yet, follow Step 5 above to trigger it manually.

**A workflow run failed.** Click into the failed run in the Actions tab to see the error log. The most common issue is the `news.json` file getting locked or a single feed timing out — the next hourly run usually resolves it on its own.

**Stories look miscategorized.** Keyword classification is rough. Adding an Anthropic API key (Optional step above) noticeably improves accuracy.

**I want to change the hourly schedule.** Edit `.github/workflows/refresh.yml`. The cron expression `0 * * * *` means "every hour at minute 0." Change to `0 */2 * * *` for every 2 hours, `0 8,12,16 * * *` for 3 specific times daily, etc.

---

## File map

```
redo-news-dashboard/
├── README.md                   ← you are here
├── index.html                  ← the dashboard (served by GitHub Pages)
├── news.json                   ← scraped data (auto-updated hourly)
├── scraper.py                  ← pulls RSS feeds
├── classifier.py               ← labels stories as opportunity/threat
├── refresh.py                  ← main entry point, runs the whole pipeline
├── requirements.txt            ← Python dependencies
└── .github/
    └── workflows/
        └── refresh.yml         ← the GitHub Actions schedule
```
