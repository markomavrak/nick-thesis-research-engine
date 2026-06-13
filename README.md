# Aurex Research Terminal

Aurex is a live research terminal for finding and monitoring public-company
setups that fit a defined market thesis. It combines:

- thesis-fit scoring
- sector/value-chain mapping
- hidden-gem candidate screening
- live public-source enrichment from SEC filings, Yahoo Finance RSS, and Stooq daily OHLCV
- unusual daily volume and price-impulse flags
- manual block-activity tape entry
- daily 9 AM email digest automation

Aurex surfaces research targets and source trails. It does not issue buy/sell
recommendations, position sizes, price targets, or stops.

## Run The Live Terminal

Python 3 is the only requirement.

```bash
PYTHONPATH=src python3 -m aurex --open
```

Then open:

```text
http://127.0.0.1:8765
```

Useful options:

```bash
PYTHONPATH=src python3 -m aurex \
  --host 127.0.0.1 \
  --port 8765 \
  --cache-seconds 300 \
  --block-activity-path data/block-activity.json
```

The terminal auto-refreshes every 5 minutes in the browser. Public-source market
data is cached server-side so repeated clicks do not hammer free data sources.

## What The Terminal Shows

The default dashboard includes:

- **High-conviction screen:** 80+ score candidates that clear setup gates.
- **Unusual activity tape:** daily volume ratio, one-day price impulse, fresh filings/news, and manual block entries.
- **Deep-dive panel:** ticker-level thesis fit, setup score, risk tier, catalysts, risks, invalidation checks, filings, news, and source links.
- **Manual block tape:** quick entry for block prints, dark-pool notes, unusual options blocks, or broker-observed activity.

True intraday block-trade feeds require a paid market-data provider. Until one is
connected, Aurex clearly labels block activity as manual and uses public daily
volume as the unusual-activity proxy.

## Generate A Thesis Report

```bash
PYTHONPATH=src python3 -m aurex.cli \
  --thesis "construction equipment demand will skyrocket" \
  --max-market-cap-b 15 \
  --output-dir output/construction-equipment
```

The command writes:

- `aurex-research-report.md`
- `aurex-research-report.json`

## Daily Email Automation

GitHub Actions sends one combined research digest at approximately 9:00 AM
Toronto time. The schedule runs at both `13:00 UTC` and `14:00 UTC`; the app
gates by `America/Toronto`, so only the matching daylight/standard-time run
sends.

The digest uses a durable ledger at:

```text
.github/digest-history.json
```

Every sent ticker is recorded there, and future digests exclude those tickers.
That means daily emails do not repeat the same names.

### Email Setup

1. Create a Resend account.
2. Verify a sending domain.
3. Add a GitHub Actions secret named `RESEND_API_KEY`.
4. Set the workflow sender to a verified domain address.

Current production sender:

```text
Market Research <research@updates.advertra.ca>
```

Current recipients are configured in code:

```text
marko@advertra.ca
ikeepitstream@gmail.com
```

### Test The Digest Without Sending

```bash
PYTHONPATH=src python3 -m aurex.daily_digest --dry-run --force
```

This writes:

```text
output/daily-digest/daily-stock-research-preview.html
```

## Data Boundary

Free public sources currently wired:

- SEC ticker map, submissions, and companyfacts
- Yahoo Finance RSS headlines
- Stooq daily OHLCV
- manually entered block-activity observations

Not yet wired:

- live intraday quotes
- exchange-level block prints
- unusual options flow feed
- institutional ownership/fund flow feed
- earnings-call transcripts

Those can be added behind the same terminal UI as provider adapters.

## Test

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

