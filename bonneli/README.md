# Bonneli New Releases Helper

Utilities for collecting the latest Sergio Bonelli comic book releases
for a few favourite series.

## Requirements

- Python 3.8 or newer.
- Internet access to download the RSS feed from `en.shop.sergiobonelli.it`.

## Usage

The `scripts/bonelli_new_releases.py` script fetches the shop RSS feed (`rss.jsp?sezione=100010`) from Sergio Bonelli Editore and filters it for Dylan Dog, Martin Mystere, and Zagor issues by default.

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

### CSV history

Provide a path via `--csv` to append each run's results (including the fetch timestamp) to a CSV file, letting you build your own archive over time:

```shell
python scripts/bonelli_new_releases.py --csv data/bonelli_releases.csv
```

### Custom series

You can match different series names by providing them explicitly:

```shell
python scripts/bonelli_new_releases.py --series "Nathan Never" "Dragonero"
```

### Feed overrides

When run without arguments it first targets the English RSS endpoint and
automatically falls back to alternative shop mirrors if that URL errors out.
If you need to use a different RSS endpoint, pass the URL directly:

```shell
python scripts/bonelli_new_releases.py --feed-url https://shop.sergiobonelli.it/rss/ultime-uscite
```

## Development

Run a quick syntax check after making changes:

```shell
python -m compileall scripts/bonelli_new_releases.py
```
