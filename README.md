# WQDataScraper

Bulk-export every data field from the [WorldQuant BRAIN](https://platform.worldquantbrain.com) platform into structured JSON and CSV files — ready for LLM reference documents, programmatic alpha generation, or offline exploration.

BRAIN hosts **85,000+ data fields** across dozens of datasets (price/volume, fundamentals, sentiment, analyst models, news, etc.), but provides no built-in export. This script authenticates against BRAIN's undocumented REST API, paginates through the entire `/data-fields` catalog, and saves the result locally.

---

## What You Get

Running `scraper.py` produces two files:

| File | Format | Contents |
|------|--------|----------|
| `brain_data_fields.json` | JSON array | Every field object with all metadata returned by the API |
| `brain_data_fields.csv` | Flat CSV | One row per field with flattened dataset info — opens in Excel/Sheets |

Each field record includes:

- **`id`** — The field name used in FAST Expressions (e.g., `close`, `news_eod_high`, `snt1_d1_earningsrevision`)
- **`description`** — Human-readable explanation of the field
- **`type`** — `MATRIX`, `VECTOR`, `GROUP`, or `UNIVERSE`
- **`dataset_id` / `dataset_name`** — Parent dataset membership
- **`coverage`** — What fraction of the universe has non-NaN values
- **`alphaCount`** — How many existing alphas on the platform use this field
- Additional metadata fields as returned by the API

---

## Prerequisites

- **Python 3.8+**
- **A WorldQuant BRAIN account** — [Sign up free](https://platform.worldquantbrain.com) if you don't have one
- Your account must be **fully verified** — log into the web UI first and complete any Persona identity verification prompts before running the script

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/WQDataScraper.git
cd WQDataScraper
```

### 2. Create a virtual environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

If there is no `requirements.txt` yet, install manually:

```bash
pip install requests python-dotenv
```

### 4. Configure your credentials

Create a `.env` file in the project root:

```bash
touch .env
```

Add your BRAIN login credentials:

```env
WQB_EMAIL=your_email@example.com
WQB_PASSWORD=your_password_here
```

**Critical `.env` formatting rules:**

| Rule | Why |
|------|-----|
| **No quotes** around values | `python-dotenv` will include literal `"` characters in the value |
| **No trailing spaces** | Invisible whitespace causes auth failures |
| **No `#` comments on the same line** as a value | Everything after `#` gets stripped |

```env
# ✅ Correct
WQB_EMAIL=alice@university.edu
WQB_PASSWORD=MyStr0ngP@ss!

# ❌ Wrong — quotes become part of the value
WQB_EMAIL="alice@university.edu"
WQB_PASSWORD="MyStr0ngP@ss!"

# ❌ Wrong — trailing space
WQB_EMAIL=alice@university.edu
```

> **Passwords with special characters:** If your password contains `#`, `$`, `=`, or spaces, the safest approach is to change it to something alphanumeric via the BRAIN web UI, or URL-encode the special characters.

---

## Usage

### Run the scraper

```bash
python scraper.py
```

The script runs through five stages and prints clear status at each step:

```
============================================================
CREDENTIAL DIAGNOSTICS
============================================================
  Email loaded   : 'alice@university.edu'
  Email length   : 21
  Password loaded: '**************'
  Password length: 14

============================================================
AUTHENTICATION TEST (raw requests, no wqb)
============================================================
  POSTing to https://api.worldquantbrain.com/authentication ...
  Status: 201 Created

[OK] Authentication successful!

============================================================
DATA FIELDS TEST
============================================================
  GETting https://api.worldquantbrain.com/data-fields (1 field test) ...
  Status: 200
  Total fields available: 85,247
  Sample field: close — Closing price of the instrument

[OK] Data fields endpoint working!

============================================================
EXTRACTING ALL 85,247 FIELDS
============================================================
  [100.0%] 85,247 / 85,247 fields

============================================================
EXPORTING
============================================================
  JSON: brain_data_fields.json (42.3 MB)
  CSV:  brain_data_fields.csv (18.7 MB)

[DONE]
```

### Extraction time

The BRAIN API enforces rate limits of **1 request/second** and **30 requests/minute** on the data-fields endpoint. The script respects these limits automatically.

| Fields | Page size | Approx. time |
|--------|-----------|--------------|
| ~85,000 | 50/page | **30–60 minutes** |

The script prints live progress and automatically backs off when approaching rate limits.

---

## Customization

### Change region, universe, or delay

Edit the `params` dictionary in `scraper.py` to target different markets:

```python
params = {
    "region": "USA",         # Options: USA, CHN, ASI, EUR, etc.
    "delay": 1,              # Options: 0 (no delay) or 1 (1-day delay)
    "universe": "TOP3000",   # Options: TOP200, TOP500, TOP1000, TOP3000
    "instrumentType": "EQUITY",
    "limit": PAGE_SIZE,
    "offset": offset,
}
```

> **Note:** Different region/delay/universe combinations return different field subsets. To get the complete catalog across all regions, run the script multiple times with different `region` values and merge the output.

### Multi-region extraction

To extract fields for all major regions in a single run, wrap the extraction loop:

```python
regions = ["USA", "EUR", "ASI", "CHN"]
for region in regions:
    # ... run extraction with region=region
    # ... save to brain_data_fields_{region}.json
```

---

## Output Schema

### JSON structure

Each entry in `brain_data_fields.json` is an object as returned by the API:

```json
{
  "id": "news_eod_high",
  "description": "Highest price reached between the time of news and the end of the session",
  "type": "MATRIX",
  "dataset": {
    "id": "news12",
    "name": "US News Data"
  },
  "coverage": 0.97,
  "alphaCount": 1210,
  "userCount": 342
}
```

### CSV columns

The CSV flattens the nested `dataset` object:

| Column | Description |
|--------|-------------|
| `id` | Field name used in FAST Expressions |
| `description` | What the field represents |
| `type` | `MATRIX`, `VECTOR`, `GROUP`, or `UNIVERSE` |
| `dataset_id` | Parent dataset identifier |
| `dataset_name` | Human-readable dataset name |
| `coverage` | Instrument coverage (0.0–1.0) |
| `alphaCount` | Number of alphas using this field |
| `userCount` | Number of users who have used this field |

Additional columns may appear depending on what the API returns for your account's access tier.

---

## Troubleshooting

### `INVALID_CREDENTIALS` (401)

This is the most common error. Work through these checks in order:

1. **Verify your credentials work in a browser** — Go to [platform.worldquantbrain.com](https://platform.worldquantbrain.com) and log in manually with the same email and password. If that fails, the credentials are wrong.

2. **Check `.env` formatting** — The script prints what it loaded. Look for:
   - Literal quote characters in the email/password
   - Unexpected lengths (too short or too long)
   - Extra whitespace

3. **Complete Persona verification** — New accounts or accounts that haven't been used recently may require identity verification. The web UI will show a prompt. Complete it, then retry the script.

4. **Password special characters** — If your password contains `#`, the `.env` parser may truncate it. Try changing your BRAIN password to something without `#`.

### `API rate limit exceeded` (429)

The authentication endpoint only allows **5 requests per minute**. If you see this:

- Wait at least 60 seconds before retrying
- The script handles this automatically on subsequent runs
- Don't spam-run the script when debugging — fix the issue first, then try once

### `Session expired` during extraction (401 mid-run)

The script automatically re-authenticates if the session expires during a long extraction. If re-auth also fails, it will stop and save whatever was collected so far. You can resume by adjusting the starting `offset` in the script.

### `Zero fields returned`

Your account's access tier may not include data for the requested region/universe combination. Try `region=USA, universe=TOP3000` first — this is the most commonly available configuration.

### Persona / biometric verification required

If the auth response contains an `"inquiry"` key, your account needs Persona verification:

1. Open [platform.worldquantbrain.com](https://platform.worldquantbrain.com) in a browser
2. Log in and follow the verification prompts
3. After completing verification, re-run the script

---

## How It Works

The script interacts with BRAIN's undocumented REST API at `api.worldquantbrain.com`:

```
1. POST /authentication        ← HTTP Basic Auth → JWT session cookie
2. GET  /data-fields?limit=1   ← Test request, get total field count
3. GET  /data-fields?limit=50&offset=0     ← Page 1
   GET  /data-fields?limit=50&offset=50    ← Page 2
   GET  /data-fields?limit=50&offset=100   ← Page 3
   ...                                      ← (~1,700 pages)
4. Export to JSON + CSV
```

Rate limiting is managed by reading `X-RateLimit-Remaining-Minute` from response headers and sleeping when the budget gets low. The script also handles 429 (Too Many Requests) and 401 (session expired) responses gracefully with automatic retry logic.

---

## Use Cases

### LLM-powered alpha generation

Feed the exported JSON/CSV into an LLM as a reference document so it knows every available data field when composing FAST Expressions:

```
You have access to the following WorldQuant BRAIN data fields:
[paste or attach brain_data_fields.json]

Write a mean-reversion alpha using sentiment and price data...
```

### Programmatic alpha mining

Use the field catalog to programmatically generate alpha candidates:

```python
import json

with open('brain_data_fields.json') as f:
    fields = json.load(f)

# Find all high-coverage matrix fields from sentiment datasets
sentiment_fields = [
    f['id'] for f in fields
    if f.get('type') == 'MATRIX'
    and 'sentiment' in f.get('dataset', {}).get('name', '').lower()
    and f.get('coverage', 0) > 0.5
]
```

### Offline exploration

Open `brain_data_fields.csv` in Excel or Google Sheets to browse, filter, and sort the entire field catalog without logging into the platform.

---

## Project Structure

```
WQDataScraper/
├── scraper.py                  # Main extraction script
├── .env                        # Your credentials (DO NOT COMMIT)
├── .gitignore                  # Excludes .env and output files
├── requirements.txt            # Python dependencies
├── README.md                   # This file
├── brain_data_fields.json      # Output: full field catalog (JSON)
└── brain_data_fields.csv       # Output: flattened field catalog (CSV)
```

---

## Security

- **Never commit your `.env` file.** Add it to `.gitignore`:
  ```
  .env
  ```
- The script prints your email for diagnostic purposes but always masks your password.
- Credentials are only sent to `api.worldquantbrain.com` over HTTPS.

---

## Related Resources

- [WorldQuant BRAIN Platform](https://platform.worldquantbrain.com) — The web UI
- [BRAIN FAST Expression Documentation](https://platform.worldquantbrain.com/learn) — Operators and language reference
- [wqb Python library](https://github.com/rocky-d/wqb) — Alternative API wrapper with auto-pagination
- [WQ-Brain](https://github.com/RussellDash332/WQ-Brain) — Community alpha submission automation
- [worldquant-miner](https://github.com/zhutoutoutousan/worldquant-miner) — Comprehensive API reverse-engineering and alpha mining

---

## Disclaimer

This tool interacts with an undocumented API. WorldQuant may change or restrict API access at any time. Use responsibly and respect rate limits. This project is not affiliated with or endorsed by WorldQuant LLC.

---

## License

MIT