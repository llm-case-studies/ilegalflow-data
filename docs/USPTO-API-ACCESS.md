# USPTO Open Data Portal API Access

## Overview

The USPTO migrated from the legacy Bulk Data Storage System (BDSS) to the new Open Data Portal (ODP) in 2025. This fundamentally changed how bulk data is accessed:

| Old System (BDSS) | New System (ODP) |
|-------------------|------------------|
| Static file server | API-first gateway |
| Anonymous access | **ID.me verified API key required** |
| Predictable URLs | Dynamic, tokenized URLs |
| `wget`/`curl` friendly | Requires proper headers + redirect handling |

## Getting Your API Key

### Step 1: Navigate to the Portal
Go to [data.uspto.gov/myodp](https://data.uspto.gov/myodp)

### Step 2: Sign In
Use your existing my.uspto.gov credentials (email and password).

### Step 3: ID.me Verification (Critical)
Once logged in, you will likely see a blank or "unauthorized" status for the API Key.

You **must** click the button to "Verify with ID.me". The USPTO requires identity proofing:
- Upload a driver's license or passport
- Complete multi-factor authentication
- Verify via an ID.me approved method

This is a one-time process - once verified, it stays linked permanently.

### Step 4: Retrieve Your Key
After ID.me verification succeeds, your 40-character `x-api-key` will appear on the screen at data.uspto.gov/myodp.

## API Key Storage

**Never commit your API key to git!**

Store it in `.env` (gitignored):
```bash
USPTO_API_KEY=your_40_character_api_key_here
```

## Using the API

### Key Constraints

| Constraint | Value | Implication |
|------------|-------|-------------|
| Concurrency | **1 call at a time** | Requests are blocked, not queued |
| Rate Limit | 60 requests/minute | Serial processing required |
| Burst Limit | 1 | Cannot parallelize downloads |

### Download Command

```bash
curl -L -O \
  -H "x-api-key: YOUR_USPTO_API_KEY" \
  -H "Accept: application/zip" \
  https://api.uspto.gov/api/v1/datasets/products/files/TRTDXFAP/apc251227.zip
```

**Critical flags:**
- `-L`: Follow HTTP 307 redirects (required!)
- `-H "x-api-key: ..."`: Authentication header

### Metadata-First Approach (Recommended)

Instead of guessing filenames, query the API for available files:

```bash
curl -H "x-api-key: YOUR_USPTO_API_KEY" \
  https://api.uspto.gov/api/v1/datasets/products/TRTDXFAP
```

This returns JSON with all available files and their download URLs.

## Product Identifiers

| Product ID | Name | Description | Frequency |
|------------|------|-------------|-----------|
| **TRTDXFAP** | Trademark Daily XML - Applications | Daily updates, 10-50MB/day | Tue-Sat |
| **TRTYRAP** | Trademark Annual XML - Applications | Full backfile (1884-present) | Annual |
| **TRTDXFAG** | Trademark Daily XML - Assignments | Ownership transfers | Daily |
| **TRTYRAG** | Trademark Annual XML - Assignments | Assignment backfile | Annual |

## Personal Key for Commercial Use

### Can I use a personal key for iLegalFlow?

**Yes.** There is no "Company" or "Commercial" account type. API keys are assigned to natural persons, not legal entities. The data itself is public domain - commercial redistribution is explicitly allowed.

### Risks to Engineer Around

#### 1. Bus Factor Risk
The key is tied to your identity. If you leave the company, the key goes with you.

**Mitigation:**
- Treat the key as a "Root Secret" in a secrets manager
- Document a credential rotation process
- New employee must get their own ID.me verified key

#### 2. Concurrency Block (Critical for SaaS)
One call at a time per key. If User A searches while User B's request is processing, User B gets a 429 error.

**Mitigation:**
- **Never use the API for real-time user queries**
- Use the key only for background/batch ingestion
- Build a local database (Manticore) for user searches

## Architecture: Local Data Lake

```
USPTO API ──(nightly batch)──> Parse XML ──> Manticore ──> iLegalFlow Users
    │                                              │
Personal Key                                Our infrastructure
(serial downloads)                          (unlimited concurrency)
```

### For iLegalFlow Extension (Free)
- Uses founder's personal key for shared public data
- Nightly batch ingestion only

### For Law Firm Appliance ($10K)
- Firm provides their own USPTO API key
- Complete data sovereignty - their key, their data
- No dependency on iLegalFlow infrastructure

## Support

- API issues: APIhelp@uspto.gov
- Documentation: [data.uspto.gov/support](https://data.uspto.gov/support)
- Release notes: [data.uspto.gov/support/release/summary](https://data.uspto.gov/support/release/summary)
