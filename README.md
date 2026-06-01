# Nick Thesis Research Engine

A local research CLI that turns an investment thesis into an evidence-backed
public-company watchlist. It encodes Nick's framework:

1. Check sector rotation before falling in love with a chart or narrative.
2. Map the value chain and look beyond the obvious leader.
3. Prioritize bottlenecks and second-order beneficiaries.
4. Rank thesis fit, evidence, catalysts, liquidity, and risk separately.
5. Keep risks and invalidation conditions visible.

The engine surfaces information. It does not issue buy/sell recommendations,
position sizes, targets, or stops.

## Run It

Python 3 is the only requirement.

```bash
PYTHONPATH=src python3 -m nick_engine.cli \
  --thesis "construction equipment demand will skyrocket" \
  --max-market-cap-b 15 \
  --output-dir output/construction-equipment
```

## Daily Email Automation

The repository includes a GitHub Actions workflow that sends one combined
research digest to `marko@advertra.ca` at approximately 9:00 AM Toronto time.
It checks at `13:07 UTC` and `14:07 UTC`, then exits immediately unless Toronto
local time is in the `9 AM` hour. This keeps daylight-saving changes automatic
while limiting GitHub Actions usage to two short checks per day.

The email combines:

- AI optical-networking bottleneck research
- AI memory and HBM bottleneck research
- Construction-equipment demand research

This remains a fixture-backed seed universe until a live research provider is
added. The email labels that limitation explicitly.

### Zero-Cost Setup

1. Create a free Resend account.
2. Verify a sending domain in Resend. After a domain is verified, Resend allows
   sending from any address at that domain.
3. Create a Resend API key.
4. In the GitHub repository, open `Settings > Secrets and variables > Actions`.
5. Add repository secret `RESEND_API_KEY`.
6. Add repository secret `RESEND_FROM_EMAIL`, for example:

```text
Nick Research <research@your-verified-domain.com>
```

7. Open the repository's `Actions` tab and enable workflows if GitHub asks.

The workflow file is `.github/workflows/daily-stock-research.yml`.

Resend's free tier currently allows `3,000` transactional emails per month and
`100` per day. This workflow sends at most one accepted email per day. GitHub
Actions use is free for standard runners in public repositories. Private
repositories consume a small amount of the repository owner's included monthly
Linux-runner minutes.

### Test Without Sending Email

Run a local preview:

```bash
PYTHONPATH=src python3 -m nick_engine.daily_digest --dry-run --force
```

Manual GitHub Actions runs also use dry-run mode and do not call Resend.
Scheduled runs use Resend's API with a Toronto-date idempotency key so retries
cannot create duplicate morning emails.

## Test

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```
