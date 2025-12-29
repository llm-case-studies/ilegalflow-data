#!/usr/bin/env python3
"""
USPTO Trademark Bulk Data Downloader

Downloads trademark XML data from USPTO Open Data Portal (ODP).
Requires API key from data.uspto.gov/myodp (ID.me verification required).

Usage:
    python download.py --sample          # Download latest daily file for testing
    python download.py --daily           # Download recent daily files
    python download.py --list            # List available files without downloading
    python download.py --year 2024       # Download annual archive
"""

import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
import yaml
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(Path(__file__).parent.parent / ".env")

# USPTO Open Data Portal API
USPTO_API_BASE = "https://api.uspto.gov/api/v1/datasets/products"
PRODUCT_DAILY = "TRTDXFAP"  # Trademark Daily XML - Applications
PRODUCT_ANNUAL = "TRTYRAP"  # Trademark Annual XML - Applications


def get_api_key() -> str:
    """Get USPTO API key from environment."""
    key = os.environ.get("USPTO_API_KEY")
    if not key:
        print("Error: USPTO_API_KEY not found in environment")
        print("Set it in .env file or export USPTO_API_KEY=your_key")
        print("Get your key at: https://data.uspto.gov/myodp")
        sys.exit(1)
    return key


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


def get_headers(api_key: str) -> dict:
    """Build request headers with API key."""
    return {
        "x-api-key": api_key,
        "Accept": "application/json"
    }


def list_available_files(product_id: str, api_key: str, limit: int = 10) -> list:
    """Query API for available files in a product."""
    url = f"{USPTO_API_BASE}/{product_id}"
    headers = get_headers(api_key)

    print(f"Querying {product_id} metadata...")
    response = requests.get(url, headers=headers, timeout=30)

    if response.status_code != 200:
        print(f"Error: API returned {response.status_code}")
        print(f"Response: {response.text[:500]}")
        return []

    data = response.json()

    # Navigate the USPTO response structure
    # Structure: bulkDataProductBag[0].productFileBag.fileDataBag
    products = data.get("bulkDataProductBag", [])
    if not products:
        print("No products found in response")
        return []

    file_bag = products[0].get("productFileBag", {})
    files = file_bag.get("fileDataBag", [])

    # Map to simpler structure
    result = []
    for f in files:
        result.append({
            "fileName": f.get("fileName"),
            "fileSize": f.get("fileSize", 0),
            "releaseDate": f.get("fileReleaseDate", ""),
            "fileDownloadUrl": f.get("fileDownloadURI")
        })

    # Sort by release date (newest first)
    result.sort(key=lambda x: x.get("releaseDate", ""), reverse=True)

    return result[:limit] if limit else result


def download_file(file_info: dict, dest_dir: Path, api_key: str, force: bool = False) -> bool:
    """Download a single file from USPTO API."""
    filename = file_info.get("fileName")
    download_url = file_info.get("fileDownloadUrl")
    file_size = file_info.get("fileSize", 0)

    if not filename or not download_url:
        print(f"  Error: Missing filename or URL in file info")
        return False

    dest_path = dest_dir / filename

    if dest_path.exists() and not force:
        print(f"  Skipping {filename} (already exists)")
        return True

    dest_dir.mkdir(parents=True, exist_ok=True)

    print(f"  Downloading {filename} ({file_size:,} bytes)...")

    headers = {
        "x-api-key": api_key,
        "Accept": "application/zip"
    }

    try:
        # Stream download with redirect following (critical for USPTO)
        with requests.get(download_url, headers=headers, stream=True,
                         allow_redirects=True, timeout=300) as r:
            r.raise_for_status()

            # Verify we got a ZIP, not HTML error page
            content_type = r.headers.get("Content-Type", "")
            if "text/html" in content_type:
                print(f"  Error: Received HTML instead of ZIP (likely auth issue)")
                return False

            with open(dest_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

        actual_size = dest_path.stat().st_size
        print(f"  Saved {filename} ({actual_size:,} bytes)")
        return True

    except requests.exceptions.RequestException as e:
        print(f"  Error downloading {filename}: {e}")
        if dest_path.exists():
            dest_path.unlink()  # Remove partial download
        return False


def download_latest(config: dict, api_key: str, count: int = 1):
    """Download the latest daily file(s)."""
    raw_path = Path(config["data"]["raw_path"]) / "daily"

    files = list_available_files(PRODUCT_DAILY, api_key, limit=count)

    if not files:
        print("No files found")
        return

    print(f"Found {len(files)} file(s) to download")

    for file_info in files:
        download_file(file_info, raw_path, api_key)
        # Respect rate limits - wait between downloads
        if len(files) > 1:
            time.sleep(1)


def download_daily(config: dict, api_key: str, days: int = 7):
    """Download recent daily files."""
    raw_path = Path(config["data"]["raw_path"]) / "daily"

    files = list_available_files(PRODUCT_DAILY, api_key, limit=days)

    if not files:
        print("No files found")
        return

    print(f"Downloading {len(files)} daily file(s)...")

    success = 0
    for file_info in files:
        if download_file(file_info, raw_path, api_key):
            success += 1
        # Respect rate limits
        time.sleep(1)

    print(f"Downloaded {success}/{len(files)} files")


def list_files(api_key: str, product: str = PRODUCT_DAILY, limit: int = 20):
    """List available files without downloading."""
    files = list_available_files(product, api_key, limit=limit)

    if not files:
        print("No files found")
        return

    print(f"\nAvailable files ({product}):")
    print("-" * 60)

    for f in files:
        name = f.get("fileName", "?")
        size = f.get("fileSize", 0)
        date = f.get("releaseDate", "?")
        print(f"  {name:<25} {size:>12,} bytes  {date}")


def download_all(config: dict, api_key: str, product: str, subdir: str):
    """Download ALL files from a product (annual backfile or all daily)."""
    raw_path = Path(config["data"]["raw_path"]) / subdir

    # Get ALL files (no limit)
    files = list_available_files(product, api_key, limit=None)

    if not files:
        print("No files found")
        return

    # Calculate total size
    total_size = sum(f.get("fileSize", 0) for f in files)
    print(f"\nDownloading {len(files)} files ({total_size / (1024**3):.1f} GB total)")
    print(f"Destination: {raw_path}")
    print("-" * 60)

    success = 0
    downloaded_bytes = 0

    for i, file_info in enumerate(files, 1):
        filename = file_info.get("fileName", "?")
        filesize = file_info.get("fileSize", 0)

        print(f"\n[{i}/{len(files)}] {filename}")

        if download_file(file_info, raw_path, api_key):
            success += 1
            downloaded_bytes += filesize

        # Progress update
        pct = (downloaded_bytes / total_size * 100) if total_size else 0
        print(f"  Progress: {downloaded_bytes / (1024**3):.2f} / {total_size / (1024**3):.1f} GB ({pct:.1f}%)")

        # Respect rate limits - wait between downloads
        time.sleep(2)

    print(f"\n{'='*60}")
    print(f"Complete! Downloaded {success}/{len(files)} files")
    print(f"Total: {downloaded_bytes / (1024**3):.2f} GB")


def main():
    parser = argparse.ArgumentParser(
        description="Download USPTO trademark data via Open Data Portal API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python download.py --list              # See available daily files
    python download.py --list --annual     # See available annual files
    python download.py --sample            # Download latest daily file
    python download.py --daily --days 7    # Download last 7 daily files
    python download.py --all --annual      # Download FULL annual backfile (~9GB)
    python download.py --all               # Download ALL daily files for 2025

Requires USPTO_API_KEY environment variable.
Get your key at: https://data.uspto.gov/myodp
        """
    )
    parser.add_argument("--sample", action="store_true",
                       help="Download latest daily file for testing")
    parser.add_argument("--daily", action="store_true",
                       help="Download recent daily files")
    parser.add_argument("--list", action="store_true",
                       help="List available files without downloading")
    parser.add_argument("--days", type=int, default=7,
                       help="Number of daily files to download (default: 7)")
    parser.add_argument("--annual", action="store_true",
                       help="Use annual archive instead of daily")
    parser.add_argument("--all", action="store_true",
                       help="Download ALL files (use with --annual for full backfile)")
    parser.add_argument("--force", action="store_true",
                       help="Re-download even if file exists")

    args = parser.parse_args()

    # Get API key and config
    api_key = get_api_key()
    config = load_config()

    product = PRODUCT_ANNUAL if args.annual else PRODUCT_DAILY
    subdir = "annual" if args.annual else "daily"

    if args.list:
        limit = 100 if args.annual else 30
        list_files(api_key, product=product, limit=limit)
    elif args.all:
        download_all(config, api_key, product, subdir)
    elif args.sample:
        download_latest(config, api_key, count=1)
    elif args.daily:
        download_daily(config, api_key, days=args.days)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
