#!/usr/bin/env python3
"""
USPTO Trademark Bulk Data Downloader

Downloads trademark XML data from USPTO bulk data portal.
Supports daily updates and annual historical archives.

Usage:
    python download.py --sample          # Download small sample for testing
    python download.py --daily           # Download latest daily files
    python download.py --year 2024       # Download annual archive
    python download.py --all             # Download everything
"""

import argparse
import hashlib
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import urlretrieve
from urllib.error import URLError

import yaml

# USPTO Bulk Data URLs
USPTO_DAILY_BASE = "https://bulkdata.uspto.gov/data/trademark/dailyxml/applications/"
USPTO_ANNUAL_BASE = "https://bulkdata.uspto.gov/data/trademark/"

def load_config():
    """Load configuration from config.yaml"""
    config_path = Path(__file__).parent.parent / "config" / "config.yaml"
    if not config_path.exists():
        print("Warning: config.yaml not found, using defaults")
        return {
            "data": {
                "raw_path": "/tmp/ilegalflow/raw",
                "output_path": "/tmp/ilegalflow/releases"
            }
        }
    with open(config_path) as f:
        return yaml.safe_load(f)


def download_file(url: str, dest_path: Path, force: bool = False) -> bool:
    """Download a file with progress indication."""
    if dest_path.exists() and not force:
        print(f"  Skipping {dest_path.name} (already exists)")
        return True

    dest_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"  Downloading {url}...")
    try:
        urlretrieve(url, dest_path)
        print(f"  Saved to {dest_path}")
        return True
    except URLError as e:
        print(f"  Error: {e}")
        return False


def get_daily_filename(date: datetime) -> str:
    """Generate daily XML filename for a date."""
    # Format: apcYYMMDD.zip (e.g., apc241228.zip)
    return f"apc{date.strftime('%y%m%d')}.zip"


def download_sample(config: dict):
    """Download a small sample for testing."""
    raw_path = Path(config["data"]["raw_path"]) / "daily"

    # Get yesterday's file (today's might not exist yet)
    yesterday = datetime.now() - timedelta(days=1)
    filename = get_daily_filename(yesterday)
    url = f"{USPTO_DAILY_BASE}{filename}"
    dest = raw_path / filename

    print(f"Downloading sample: {filename}")
    return download_file(url, dest)


def download_daily(config: dict, days: int = 7):
    """Download recent daily files."""
    raw_path = Path(config["data"]["raw_path"]) / "daily"

    for i in range(1, days + 1):
        date = datetime.now() - timedelta(days=i)
        filename = get_daily_filename(date)
        url = f"{USPTO_DAILY_BASE}{filename}"
        dest = raw_path / filename
        download_file(url, dest)


def download_annual(config: dict, year: int):
    """Download annual archive for a year."""
    raw_path = Path(config["data"]["raw_path"]) / "annual"

    # Annual files have various naming conventions
    # This is a simplified version - actual URLs may vary
    filename = f"trademark_applications_{year}.zip"
    url = f"{USPTO_ANNUAL_BASE}{year}/{filename}"
    dest = raw_path / filename

    print(f"Downloading annual archive: {year}")
    return download_file(url, dest)


def main():
    parser = argparse.ArgumentParser(description="Download USPTO trademark data")
    parser.add_argument("--sample", action="store_true", help="Download small sample")
    parser.add_argument("--daily", action="store_true", help="Download recent daily files")
    parser.add_argument("--year", type=int, help="Download annual archive for year")
    parser.add_argument("--days", type=int, default=7, help="Number of daily files")
    parser.add_argument("--all", action="store_true", help="Download everything")

    args = parser.parse_args()
    config = load_config()

    if args.sample:
        download_sample(config)
    elif args.daily:
        download_daily(config, args.days)
    elif args.year:
        download_annual(config, args.year)
    elif args.all:
        download_daily(config, 30)
        for year in range(2020, datetime.now().year + 1):
            download_annual(config, year)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
