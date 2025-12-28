# iLegalFlow Data Architecture

## Overview

This repository is the **data foundation** of the iLegalFlow ecosystem. It transforms raw USPTO bulk data into clean, searchable, educational assets.

## Design Principles

1. **Producer, not consumer** — Outputs versioned artifacts; downstream systems never parse raw USPTO data
2. **Reality as source of truth** — Every claim in the product must trace back to this data
3. **Portable scripts** — Code runs on any machine; data lives on configured storage
4. **Incremental updates** — Support daily USPTO updates without full reprocessing

## Data Sources

### USPTO Bulk Data Portal

| Dataset | URL | Update Frequency | Size |
|---------|-----|------------------|------|
| Daily Applications XML | `bulkdata.uspto.gov/data/trademark/dailyxml/applications/` | Daily | 3-60MB/day |
| Annual Applications XML | `bulkdata.uspto.gov/data/trademark/` | Annual | ~10GB/year |
| Case Files Dataset | `uspto.gov/ip-policy/economic-research/research-datasets/` | Quarterly | ~1GB |

### Data Characteristics

- **Total records**: ~13 million (3-4M live, 9-10M dead)
- **Date range**: 1884 to present
- **Format**: XML with evolving DTD schemas
- **Challenges**: Schema drift across decades, inconsistent encoding

## Processing Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                    ACQUIRE PHASE                            │
├─────────────────────────────────────────────────────────────┤
│  download.py                                                │
│  • Fetch daily/annual XML from USPTO                       │
│  • Verify checksums                                         │
│  • Store in raw_path                                       │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    PARSE PHASE                              │
├─────────────────────────────────────────────────────────────┤
│  parse.py                                                   │
│  • Stream XML (memory-efficient)                           │
│  • Handle DTD variations                                   │
│  • Normalize to marks.schema.json                          │
│  • Output: marks.parquet, status.parquet                   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   ENRICH PHASE                              │
├─────────────────────────────────────────────────────────────┤
│  features.py                                                │
│  • Phonetic encoding (Soundex, Metaphone)                  │
│  • Tokenization and n-grams                                │
│  • Dominant term extraction                                │
│  • Failure type labeling (heuristic)                       │
│  • Output: features.parquet                                │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    INDEX PHASE                              │
├─────────────────────────────────────────────────────────────┤
│  index.py                                                   │
│  • Load into search engine (Manticore/Tantivy)             │
│  • Configure phonetic morphology                           │
│  • Build HNSW indexes for vectors (future)                 │
│  • Validate search functionality                           │
└─────────────────────────────────────────────────────────────┘
```

## Output Artifacts

Each processing run produces a dated release:

```
releases/2024-12-28/
├── marks.parquet          # Core trademark data
├── status.parquet         # Status and dates
├── features.parquet       # Computed features
├── MANIFEST.json          # Metadata and checksums
└── index/                 # Optional: pre-built search index
    └── manticore/
```

### MANIFEST.json Structure

```json
{
  "version": "1.0.0",
  "date": "2024-12-28",
  "source": {
    "daily_xml": ["apc241227.zip", "apc241228.zip"],
    "annual_xml": ["2024.zip"]
  },
  "counts": {
    "total_records": 13245678,
    "live": 3456789,
    "dead": 9788889
  },
  "checksums": {
    "marks.parquet": "sha256:abc123...",
    "status.parquet": "sha256:def456...",
    "features.parquet": "sha256:ghi789..."
  }
}
```

## Storage Layout

**Git repository** (this repo):
- Scripts, schemas, docs, samples
- Small, portable, pull to any machine

**External storage** (configured path):
- Raw USPTO XML files
- Processed parquet files
- Search engine indexes

Recommended layout on external drive:
```
/mnt/uspto-data/
├── raw/
│   ├── daily/
│   │   └── 2024/
│   │       ├── apc241201.zip
│   │       └── ...
│   └── annual/
│       ├── 2024.zip
│       └── ...
├── releases/
│   └── 2024-12-28/
│       └── ...
└── indexes/
    └── manticore/
```

## Search Engine Options

| Engine | Pros | Cons | Phonetics |
|--------|------|------|-----------|
| **Manticore** | Native phonetics, SQL interface, low memory | Less ecosystem | Built-in Soundex/Metaphone |
| **Tantivy** | Rust, fast, low memory | Requires custom phonetics | Via contrib crate |
| **OpenSearch** | Full-featured, good tooling | High memory, Java | Plugin required |

**Recommendation**: Start with Manticore for POC (fastest to phonetic search).

## Curriculum Data

For the "driving school" educational features, we extract:

1. **Failure patterns** — Marks that died and why (heuristic)
2. **Office action clustering** — Common refusal reasons
3. **Success patterns** — What characteristics correlate with registration

This feeds:
- Extension "Pitfall Badges"
- Landing page "Common Accidents" dashboard
- Future AI training data

## Future: Vector Embeddings

Phase 2 will add semantic search:
- Generate embeddings for mark_text + goods_services
- Use all-MiniLM-L6-v2 or legal-domain fine-tuned model
- Store in vector-capable engine (OpenSearch, Vespa, or HNSW in Manticore)
- Enable "conceptually similar" searches beyond phonetics

## Related Repositories

| Repo | Relationship |
|------|--------------|
| `ilegalflow-web` | Consumes: charts, examples, playground data |
| `ilegalflow-extension` | Consumes: heuristics, feature patterns |
| `ilegalflow-core` | Consumes: search indexes, scoring data |
