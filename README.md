# Currency

`currency.py` is a small command-line utility for looking up foreign exchange rates with `freecurrencyapi.com`. It supports an interactive prompt mode and a direct CLI mode for converting an amount from one base currency into a configured list of target currencies.

## Features

- Interactive lookup mode for repeated currency checks
- CLI mode with `-c/--currency` and `-a/--amount`
- Full currency labels, for example `USD - United States Dollar (US$)`
- Box-drawn terminal tables using `tabulate`
- Cached supported-currency metadata with offline fallback

## Requirements

- Python 3
- A valid `freecurrencyapi` API key
- Packages listed in [requirements.txt](/Users/gordon/codex/requirements.txt:1)

Install dependencies with:

```bash
pip install -r requirements.txt
```

## Configuration

Create a local `.env` file based on [.env.example](/Users/gordon/codex/.env.example:1):

```env
CURRENCY_API_KEY=your_freecurrencyapi_key_here
CURRENCIES=AUD,EUR,GBP,USD,CAD
```

Settings:

- `CURRENCY_API_KEY` is required
- `CURRENCIES` is a comma-separated list of target currencies to display

Supported currency metadata is cached in `~/.currency_converter/supported_currencies.json` for 7 days.

## Usage

Run in interactive mode:

```bash
./currency.py
```

Run a one-off conversion:

```bash
./currency.py -c USD -a 10
```

Rules:

- `--currency` and `--amount` must be used together
- currency codes are normalized to uppercase
- amounts must be zero or greater

## Example Output

```text
Conversions for 10.00 USD - United States Dollar (US$)
╒══════════════════════════════════╤════════╤════════════════════╕
│ Currency                         │   Rate │   Converted Amount │
╞══════════════════════════════════╪════════╪════════════════════╡
│ AUD - Australian Dollar (A$)     │   1.50 │              15.00 │
│ EUR - Euro (€)                   │   0.90 │               9.00 │
│ GBP - British Pound Sterling (£) │   0.80 │               8.00 │
│ CAD - Canadian Dollar (C$)       │   1.30 │              13.00 │
╘══════════════════════════════════╧════════╧════════════════════╛
```

## Project Structure

```text
currency.py
requirements.txt
.env.example
README.md
```

## Development

Useful commands:

```bash
/Users/gordon/python/currency/bin/python3 -m py_compile currency.py
./currency.py --help
./currency.py -c USD -a 10
```

## Notes

- `.env` is ignored and should not be committed
- `.currency_converter/` is generated cache data and should stay out of Git
- if the API is unavailable, the script can fall back to expired cached currency metadata
