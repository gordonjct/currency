#!/Users/gordon/python/currency/bin/python3

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv
from tabulate import tabulate

FALLBACK_CURRENCY_DETAILS = {
    "AUD": {"name": "Australian Dollar", "symbol": "A$"},
    "BGN": {"name": "Bulgarian Lev", "symbol": "lev"},
    "BRL": {"name": "Brazilian Real", "symbol": "R$"},
    "CAD": {"name": "Canadian Dollar", "symbol": "C$"},
    "CHF": {"name": "Swiss Franc", "symbol": "CHF"},
    "CNY": {"name": "Chinese Yuan", "symbol": "CN¥"},
    "CZK": {"name": "Czech Koruna", "symbol": "Kc"},
    "DKK": {"name": "Danish Krone", "symbol": "kr"},
    "EUR": {"name": "Euro", "symbol": "€"},
    "GBP": {"name": "British Pound Sterling", "symbol": "£"},
    "HKD": {"name": "Hong Kong Dollar", "symbol": "HK$"},
    "HRK": {"name": "Croatian Kuna", "symbol": "kn"},
    "HUF": {"name": "Hungarian Forint", "symbol": "Ft"},
    "IDR": {"name": "Indonesian Rupiah", "symbol": "Rp"},
    "ILS": {"name": "Israeli New Shekel", "symbol": "NIS"},
    "INR": {"name": "Indian Rupee", "symbol": "Rs"},
    "ISK": {"name": "Icelandic Krona", "symbol": "kr"},
    "JPY": {"name": "Japanese Yen", "symbol": "¥"},
    "KRW": {"name": "South Korean Won", "symbol": "₩"},
    "MXN": {"name": "Mexican Peso", "symbol": "MX$"},
    "MYR": {"name": "Malaysian Ringgit", "symbol": "RM"},
    "NOK": {"name": "Norwegian Krone", "symbol": "kr"},
    "NZD": {"name": "New Zealand Dollar", "symbol": "NZ$"},
    "PHP": {"name": "Philippine Peso", "symbol": "₱"},
    "PLN": {"name": "Polish Zloty", "symbol": "zl"},
    "RON": {"name": "Romanian Leu", "symbol": "lei"},
    "RUB": {"name": "Russian Ruble", "symbol": "₽"},
    "SEK": {"name": "Swedish Krona", "symbol": "kr"},
    "SGD": {"name": "Singapore Dollar", "symbol": "S$"},
    "THB": {"name": "Thai Baht", "symbol": "฿"},
    "TRY": {"name": "Turkish Lira", "symbol": "₺"},
    "USD": {"name": "United States Dollar", "symbol": "US$"},
    "ZAR": {"name": "South African Rand", "symbol": "R"},
}


def load_currencies():
    currencies_str = os.getenv("CURRENCIES", "AUD,EUR,GBP,NZD,USD")
    return [currency.strip().upper() for currency in currencies_str.split(",") if currency.strip()]


def load_api_key():
    if load_dotenv():
        api_key = os.getenv("CURRENCY_API_KEY")
        if api_key:
            return api_key

    env_path = Path.home() / ".env"
    if env_path.exists() and load_dotenv(dotenv_path=env_path):
        api_key = os.getenv("CURRENCY_API_KEY")
        if api_key:
            return api_key

    raise EnvironmentError(
        "API key not found. Please create a .env file with CURRENCY_API_KEY=your_api_key "
        "in either the current directory or your home directory."
    )


def parse_args():
    parser = argparse.ArgumentParser(
        description="Look up exchange rates using freecurrencyapi.com."
    )
    parser.add_argument(
        "-c",
        "--currency",
        help="Base currency code to convert from, for example USD.",
    )
    parser.add_argument(
        "-a",
        "--amount",
        type=float,
        help="Amount in the base currency to convert.",
    )
    args = parser.parse_args()

    if (args.currency and args.amount is None) or (args.amount is not None and not args.currency):
        parser.error("Both --currency and --amount must be provided together.")

    if args.currency:
        args.currency = args.currency.upper()

    if args.amount is not None and args.amount < 0:
        parser.error("--amount must be zero or greater.")

    return args


def get_cache_path():
    cache_dir = Path.home() / ".currency_converter"
    cache_dir.mkdir(exist_ok=True)
    return cache_dir / "supported_currencies.json"


def load_cached_currencies():
    cache_path = get_cache_path()
    if not cache_path.exists():
        return None, False

    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            cache_data = json.load(f)

        last_updated = datetime.fromtimestamp(cache_data.get("timestamp", 0))
        cache_age = datetime.now() - last_updated
        cache_expired = cache_age > timedelta(days=7)

        cached_currencies = cache_data.get("currencies")
        if isinstance(cached_currencies, list):
            currency_map = {
                code.upper(): get_currency_details(code)
                for code in cached_currencies
                if isinstance(code, str)
            }
        elif isinstance(cached_currencies, dict):
            currency_map = {}
            for code, meta in cached_currencies.items():
                if not isinstance(code, str):
                    continue
                meta = meta if isinstance(meta, dict) else {}
                fallback_meta = get_currency_details(code)
                currency_map[code.upper()] = {
                    "name": meta.get("name") or fallback_meta["name"],
                    "symbol": meta.get("symbol") or fallback_meta["symbol"],
                }
        else:
            return None, False

        return currency_map, cache_expired
    except (json.JSONDecodeError, KeyError, OSError) as e:
        print(f"Warning: Error reading cache file: {e}")
        return None, False


def save_currencies_to_cache(currencies):
    cache_path = get_cache_path()
    try:
        cache_data = {
            "currencies": currencies,
            "timestamp": datetime.now().timestamp(),
        }
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache_data, f)
        return True
    except OSError as e:
        print(f"Warning: Could not save currency cache: {e}")
        return False


def get_currency_details(code):
    normalized_code = code.upper()
    fallback = FALLBACK_CURRENCY_DETAILS.get(normalized_code, {})
    return {
        "name": fallback.get("name") or normalized_code,
        "symbol": fallback.get("symbol") or "",
    }


def get_supported_currencies(api_key):
    cached_currencies, cache_expired = load_cached_currencies()

    if cached_currencies and not cache_expired:
        print("Using cached list of supported currencies")
        return cached_currencies

    print("Updating supported currencies list from API...")
    url = f"https://api.freecurrencyapi.com/v1/currencies?apikey={api_key}"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        raw_currencies = data["data"]
        currencies = {}

        for code, meta in raw_currencies.items():
            meta = meta if isinstance(meta, dict) else {}
            fallback_meta = get_currency_details(code)
            currencies[code.upper()] = {
                "name": meta.get("name") or fallback_meta["name"],
                "symbol": meta.get("symbol") or fallback_meta["symbol"],
            }

        save_currencies_to_cache(currencies)
        return currencies
    except requests.exceptions.RequestException as e:
        print(f"Network error: {e}")
        if cached_currencies:
            print("Using expired cached data as fallback")
            return cached_currencies
        return {}
    except ValueError as e:
        print(f"Invalid response format: {e}")
        if cached_currencies:
            print("Using cached data as fallback")
            return cached_currencies
        return {}
    except Exception as e:
        print(f"Failed to fetch supported currencies: {e}")
        if cached_currencies:
            print("Using cached data as fallback")
            return cached_currencies
        return {}


def convert_currency(base, api_key, currencies):
    currencies_str = ",".join(currencies)
    base_url = f"https://api.freecurrencyapi.com/v1/latest?apikey={api_key}"
    url = f"{base_url}&base_currency={base}&currencies={currencies_str}"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        return data["data"]
    except requests.exceptions.RequestException as e:
        print(f"Network error: {e}")
        return None
    except ValueError as e:
        print(f"Invalid response format: {e}")
        return None
    except Exception as e:
        print(f"Error fetching conversion rates: {e}")
        return None


def format_currency_label(code, currency_details):
    details = currency_details.get(code, {})
    name = details.get("name") or code
    symbol = details.get("symbol") or ""
    suffix = f" ({symbol})" if symbol else ""
    return f"{code} - {name}{suffix}"


def print_table(base, data, currencies, currency_details):
    rows = []
    for ticker in currencies:
        if ticker != base and ticker in data:
            rows.append(
                [
                    format_currency_label(ticker, currency_details),
                    f"{data[ticker]:.2f}",
                ]
            )

    print(f"\nExchange Rates (Base: {format_currency_label(base, currency_details)})")
    print(
        tabulate(
            rows,
            headers=["Currency", "Rate"],
            tablefmt="fancy_grid",
            disable_numparse=True,
            colalign=("left", "right"),
        )
    )


def print_conversion_table(base, amount, data, currencies, currency_details):
    base_label = format_currency_label(base, currency_details)
    rows = []
    for ticker in currencies:
        if ticker != base and ticker in data:
            rate = data[ticker]
            converted_amount = amount * rate
            rows.append(
                [
                    format_currency_label(ticker, currency_details),
                    f"{rate:.2f}",
                    f"{converted_amount:.2f}",
                ]
            )

    print(f"\nConversions for {amount:.2f} {base_label}")
    print(
        tabulate(
            rows,
            headers=["Currency", "Rate", "Converted Amount"],
            tablefmt="fancy_grid",
            disable_numparse=True,
            colalign=("left", "right", "right"),
        )
    )


def main():
    try:
        args = parse_args()
        api_key = load_api_key()
        currencies = load_currencies()

        if not currencies:
            print("Error: No currencies specified in .env file or defaults.")
            return

        print(f"Working with currencies: {', '.join(currencies)}")

        supported_currencies = get_supported_currencies(api_key)
        if not supported_currencies:
            print("Unable to continue without supported currency list.")
            return

        unsupported = [c for c in currencies if c not in supported_currencies]
        if unsupported:
            print(f"Warning: Some requested currencies are not supported: {', '.join(unsupported)}")
            currencies = [c for c in currencies if c in supported_currencies]
            if not currencies:
                print("Error: None of the requested currencies are supported.")
                return
            print(f"Continuing with supported currencies: {', '.join(currencies)}")

        if args.currency:
            base = args.currency
            if base not in supported_currencies:
                print("Invalid currency code. Please try again.")
                return

            data = convert_currency(base, api_key, currencies)
            if not data:
                return

            print_conversion_table(base, args.amount, data, currencies, supported_currencies)
            return

        while True:
            base = input("Enter the base currency (q to quit): ").upper()
            if base == "Q":
                break
            if base not in supported_currencies:
                print("Invalid currency code. Please try again.")
                continue

            data = convert_currency(base, api_key, currencies)
            if not data:
                continue

            print_table(base, data, currencies, supported_currencies)

    except EnvironmentError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nProgram terminated by user.")
        sys.exit(0)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
