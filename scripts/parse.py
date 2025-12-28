#!/usr/bin/env python3
"""
USPTO Trademark XML Parser

Parses USPTO bulk XML files and normalizes to structured records.
Handles schema variations across different years of data.

Usage:
    python parse.py --input /path/to/raw --output /path/to/releases
    python parse.py --sample  # Parse sample data only
"""

import argparse
import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Iterator, Dict, Any, Optional
from xml.etree import ElementTree as ET

import yaml

# Try to import optional dependencies
try:
    import pyarrow as pa
    import pyarrow.parquet as pq
    HAS_PARQUET = True
except ImportError:
    HAS_PARQUET = False
    print("Warning: pyarrow not installed, will output JSON instead of parquet")


def load_config():
    """Load configuration from config.yaml"""
    config_path = Path(__file__).parent.parent / "config" / "config.yaml"
    if not config_path.exists():
        return {
            "data": {
                "raw_path": "/tmp/ilegalflow/raw",
                "output_path": "/tmp/ilegalflow/releases"
            },
            "processing": {"workers": 4, "batch_size": 10000}
        }
    with open(config_path) as f:
        return yaml.safe_load(f)


def parse_date(date_str: Optional[str]) -> Optional[str]:
    """Parse various USPTO date formats to ISO format."""
    if not date_str:
        return None

    # Try common formats
    for fmt in ["%Y%m%d", "%Y-%m-%d", "%m/%d/%Y"]:
        try:
            return datetime.strptime(date_str.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def extract_text(element: Optional[ET.Element], default: str = "") -> str:
    """Safely extract text from XML element."""
    if element is None:
        return default
    return (element.text or default).strip()


def extract_classes(case_file: ET.Element) -> list:
    """Extract Nice classification codes."""
    classes = []
    for classification in case_file.findall(".//classification"):
        intl_code = classification.find("international-code-total-no")
        if intl_code is not None and intl_code.text:
            try:
                classes.append(int(intl_code.text))
            except ValueError:
                pass

    # Also check class-codes pattern
    for class_code in case_file.findall(".//class-code"):
        if class_code.text:
            try:
                classes.append(int(class_code.text))
            except ValueError:
                pass

    return sorted(set(classes))


def extract_filing_basis(case_file: ET.Element) -> list:
    """Extract filing basis codes."""
    bases = []
    for basis in case_file.findall(".//filing-basis"):
        code = extract_text(basis.find("filing-basis-code"))
        if code:
            bases.append(code)
    return bases


def parse_case_file(case_file: ET.Element) -> Optional[Dict[str, Any]]:
    """Parse a single case-file element to normalized record."""
    try:
        serial = case_file.find(".//serial-number")
        if serial is None or not serial.text:
            return None

        serial_number = serial.text.strip().zfill(8)

        # Find mark text
        mark_text = ""
        for path in [".//mark-text", ".//word-mark", ".//standard-character-claim-in/text-element"]:
            element = case_file.find(path)
            if element is not None and element.text:
                mark_text = element.text.strip()
                break

        # Determine status
        status_code = extract_text(case_file.find(".//status-code"))

        # Map status codes to simple status
        if status_code.startswith("6"):
            status = "LIVE"  # Registered
        elif status_code.startswith("8") or status_code.startswith("9"):
            status = "DEAD"  # Abandoned/Cancelled
        else:
            status = "PENDING"

        # Extract goods/services
        goods_services_parts = []
        for gs in case_file.findall(".//goods-and-services"):
            text = extract_text(gs.find("goods-services-text"))
            if text:
                goods_services_parts.append(text)
        goods_services = " | ".join(goods_services_parts)

        # Extract owner
        owner_name = ""
        owner_type = "OTHER"
        for party in case_file.findall(".//party-name"):
            owner_name = extract_text(party)
            break

        # Attorney
        attorney = None
        attorney_elem = case_file.find(".//attorney-name")
        if attorney_elem is not None:
            attorney = extract_text(attorney_elem)

        record = {
            "serial_number": serial_number,
            "registration_number": extract_text(case_file.find(".//registration-number")) or None,
            "mark_text": mark_text,
            "mark_type": "STANDARD",  # Simplified
            "status": status,
            "status_code": status_code,
            "status_date": parse_date(extract_text(case_file.find(".//status-date"))),
            "filing_date": parse_date(extract_text(case_file.find(".//filing-date"))),
            "registration_date": parse_date(extract_text(case_file.find(".//registration-date"))),
            "abandonment_date": parse_date(extract_text(case_file.find(".//abandonment-date"))),
            "filing_basis": extract_filing_basis(case_file),
            "classes": extract_classes(case_file),
            "goods_services": goods_services,
            "owner_name": owner_name,
            "owner_type": owner_type,
            "attorney_name": attorney,
            "design_codes": []
        }

        return record

    except Exception as e:
        print(f"Error parsing case file: {e}")
        return None


def parse_xml_file(xml_path: Path) -> Iterator[Dict[str, Any]]:
    """Parse an XML file, yielding trademark records."""
    print(f"Parsing {xml_path.name}...")

    # Handle zip files
    if xml_path.suffix == ".zip":
        with zipfile.ZipFile(xml_path) as zf:
            for name in zf.namelist():
                if name.endswith(".xml"):
                    with zf.open(name) as f:
                        yield from parse_xml_content(f)
    else:
        with open(xml_path, "rb") as f:
            yield from parse_xml_content(f)


def parse_xml_content(file_obj) -> Iterator[Dict[str, Any]]:
    """Parse XML content, yielding records."""
    count = 0
    errors = 0

    for event, elem in ET.iterparse(file_obj, events=["end"]):
        if elem.tag == "case-file":
            record = parse_case_file(elem)
            if record:
                count += 1
                yield record
            else:
                errors += 1

            # Clear element to save memory
            elem.clear()

    print(f"  Parsed {count} records, {errors} errors")


def save_records(records: list, output_path: Path, format: str = "json"):
    """Save records to file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if format == "parquet" and HAS_PARQUET:
        # Convert to parquet
        # This is simplified - real implementation would handle nested types
        table = pa.Table.from_pylist(records)
        pq.write_table(table, output_path)
    else:
        # Fall back to JSON
        json_path = output_path.with_suffix(".json")
        with open(json_path, "w") as f:
            json.dump(records, f, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Parse USPTO trademark XML")
    parser.add_argument("--input", type=Path, help="Input directory with XML files")
    parser.add_argument("--output", type=Path, help="Output directory")
    parser.add_argument("--sample", action="store_true", help="Parse sample only")
    parser.add_argument("--limit", type=int, help="Limit number of records")

    args = parser.parse_args()
    config = load_config()

    input_path = args.input or Path(config["data"]["raw_path"])
    output_path = args.output or Path(config["data"]["output_path"])

    # Find XML/ZIP files
    xml_files = list(input_path.glob("**/*.zip")) + list(input_path.glob("**/*.xml"))

    if not xml_files:
        print(f"No XML files found in {input_path}")
        return

    print(f"Found {len(xml_files)} files to process")

    all_records = []
    for xml_file in xml_files:
        for record in parse_xml_file(xml_file):
            all_records.append(record)
            if args.limit and len(all_records) >= args.limit:
                break
        if args.limit and len(all_records) >= args.limit:
            break

    # Create release directory
    today = datetime.now().strftime("%Y-%m-%d")
    release_path = output_path / today

    # Save output
    print(f"Saving {len(all_records)} records...")
    save_records(all_records, release_path / "marks.json")

    # Create manifest
    manifest = {
        "version": "1.0.0",
        "date": today,
        "counts": {
            "total_records": len(all_records),
            "live": sum(1 for r in all_records if r["status"] == "LIVE"),
            "dead": sum(1 for r in all_records if r["status"] == "DEAD"),
            "pending": sum(1 for r in all_records if r["status"] == "PENDING")
        }
    }

    with open(release_path / "MANIFEST.json", "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"Output saved to {release_path}")
    print(f"Stats: {manifest['counts']}")


if __name__ == "__main__":
    main()
