# Bonneli New Releases Helper

Utilities for collecting the latest Sergio Bonelli comic book releases
for a few favourite series.

## Requirements

- Python 3.8 or newer.
- Internet access to download the RSS feed from `en.shop.sergiobonelli.it`.

## Usage

The `scripts/bonelli_new_releases.py` script fetches the "New Releases" RSS
feed from the Sergio Bonelli web store and filters it for Dylan Dog, Martin
Mystere, and Zagor issues by default.

```shell
python scripts/bonelli_new_releases.py
```

Example text output (truncated):

```
2024-05-22 | Dylan Dog | Dylan Dog 439: Shades of Night | https://example.invalid/dylan-dog-439
2024-05-21 | Zagor | Zagor 701: The Dark Caravan | https://example.invalid/zagor-701
```

### JSON output

Pass `--json` to receive a JSON array instead of plain text:

```shell
python scripts/bonelli_new_releases.py --json
```

### Custom series

You can match different series names by providing them explicitly:

```shell
python scripts/bonelli_new_releases.py --series "Nathan Never" "Dragonero"
```

### Feed overrides

If you need to use a different RSS endpoint (for example, when the English
store is unavailable), pass the URL directly:

```shell
python scripts/bonelli_new_releases.py --feed-url https://shop.sergiobonelli.it/rss/ultime-uscite
```

## Development

Run a quick syntax check after making changes:

```shell
python -m compileall scripts/bonelli_new_releases.py
```
