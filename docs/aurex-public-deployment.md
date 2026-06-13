# AUREX Public Deployment

The public AUREX surface is a static GitHub Pages deployment for:

```text
https://aurex.archive.trading
```

It does not expose the private local LaunchAgent or `127.0.0.1:8765`. The local
terminal remains the operator console. The public site is generated from the
same scoring and learning-center code and is deployed for free through GitHub
Actions.

## Generated Files

The generator is:

```text
src/aurex/static_site.py
```

Run locally:

```bash
PYTHONPATH=src python3 -m aurex.static_site --output-dir public --domain aurex.archive.trading
```

It writes:

- `public/index.html`
- `public/404.html`
- `public/CNAME`
- `public/robots.txt`
- `public/api/dashboard.json`
- `public/api/learning.json`
- `public/site-manifest.json`

## GitHub Pages

The deployment workflow is:

```text
.github/workflows/aurex-pages.yml
```

It runs tests, generates the static site, verifies the `CNAME`, uploads the
Pages artifact, and deploys through `actions/deploy-pages`.

## DNS

Namecheap DNS record required:

```text
Type:  CNAME
Host:  aurex
Value: markomavrak.github.io
TTL:   Automatic
```

The published artifact includes:

```text
aurex.archive.trading
```

in `CNAME`, which tells GitHub Pages to serve the custom subdomain.
