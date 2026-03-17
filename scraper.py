import json, csv, os, sys, time
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

load_dotenv()

email = os.getenv("WQB_EMAIL")
password = os.getenv("WQB_PASSWORD")

# ── Step 1: Diagnose credential loading ──────────────────────────────
print("=" * 60)
print("CREDENTIAL DIAGNOSTICS")
print("=" * 60)

if not email:
    print("[FAIL] WQB_EMAIL is empty or not set in .env")
    sys.exit(1)
if not password:
    print("[FAIL] WQB_PASSWORD is empty or not set in .env")
    sys.exit(1)

# Show what was loaded (mask password for safety)
print(f"  Email loaded   : '{email}'")
print(f"  Email length   : {len(email)}")
print(f"  Password loaded: '{'*' * len(password)}'")
print(f"  Password length: {len(password)}")

# Check for common .env pitfalls
if email.startswith('"') or email.endswith('"'):
    print("[WARN] Email has literal quote characters — remove quotes from .env")
    print("       BAD:  WQB_EMAIL=\"user@example.com\"")
    print("       GOOD: WQB_EMAIL=user@example.com")
if password.startswith('"') or password.endswith('"'):
    print("[WARN] Password has literal quote characters — remove quotes from .env")
if ' ' in email.strip() != email:
    print("[WARN] Email has leading/trailing whitespace")
if password.strip() != password:
    print("[WARN] Password has leading/trailing whitespace")

email = email.strip().strip('"').strip("'")
password = password.strip().strip('"').strip("'")

print(f"\n  Cleaned email   : '{email}'")
print(f"  Cleaned password: '{'*' * len(password)}' (len={len(password)})")


# ── Step 2: Manual auth test (bypass wqb to isolate the problem) ─────
print("\n" + "=" * 60)
print("AUTHENTICATION TEST (raw requests, no wqb)")
print("=" * 60)

sess = requests.Session()
auth_url = "https://api.worldquantbrain.com/authentication"

print(f"\n  POSTing to {auth_url} ...")
try:
    r = sess.post(auth_url, auth=HTTPBasicAuth(email, password))
except requests.exceptions.ConnectionError as e:
    print(f"[FAIL] Connection error: {e}")
    sys.exit(1)

print(f"  Status: {r.status_code} {r.reason}")
print(f"  Body:   {r.text[:500]}")

if r.status_code == 401:
    print("\n[FAIL] INVALID_CREDENTIALS")
    print("       Possible causes:")
    print("       1. Wrong email or password — try logging in at")
    print("          https://platform.worldquantbrain.com manually first")
    print("       2. Password contains special chars (#, $, etc.) that .env")
    print("          is misreading — try wrapping ONLY the password in single quotes:")
    print("            WQB_PASSWORD='my$pecial#pass'")
    print("       3. Account may have been deactivated or locked")
    print("       4. You may need to complete Persona verification first — log")
    print("          into the web UI and check for a verification prompt")
    sys.exit(1)

if r.status_code == 429:
    retry_after = int(r.headers.get("Retry-After", 60))
    print(f"\n[RATE LIMITED] Waiting {retry_after}s before retrying...")
    time.sleep(retry_after + 1)
    r = sess.post(auth_url, auth=HTTPBasicAuth(email, password))
    print(f"  Retry status: {r.status_code} {r.reason}")
    if r.status_code != 201:
        print(f"[FAIL] Auth still failing after retry: {r.text}")
        sys.exit(1)

if r.status_code != 201:
    print(f"\n[FAIL] Unexpected status {r.status_code}: {r.text}")
    sys.exit(1)

# Check for Persona verification requirement
resp_json = r.json()
if "inquiry" in resp_json:
    print("\n[FAIL] Account requires Persona biometric verification.")
    print("       Log into https://platform.worldquantbrain.com in your browser,")
    print("       complete the verification, then re-run this script.")
    sys.exit(1)

print("\n[OK] Authentication successful!")


# ── Step 3: Test data-fields endpoint ────────────────────────────────
print("\n" + "=" * 60)
print("DATA FIELDS TEST")
print("=" * 60)

test_url = "https://api.worldquantbrain.com/data-fields"
params = {
    "region": "USA",
    "delay": 1,
    "universe": "TOP3000",
    "instrumentType": "EQUITY",
    "limit": 1,
    "offset": 0,
}

print(f"\n  GETting {test_url} (1 field test) ...")
r = sess.get(test_url, params=params)
print(f"  Status: {r.status_code}")

if r.status_code == 401:
    print("[FAIL] Session not authenticated. The cookie/token may not have persisted.")
    print("       This can happen if the API changed its auth flow.")
    sys.exit(1)

data = r.json()
total_count = data.get("count", 0)
print(f"  Total fields available: {total_count}")

if total_count == 0:
    print("[WARN] Zero fields returned. Check region/universe/delay combo.")
    sys.exit(1)

if data.get("results"):
    sample = data["results"][0]
    print(f"  Sample field: {sample.get('id', 'N/A')} — {sample.get('description', 'N/A')[:80]}")
    print(f"  Keys in response: {list(sample.keys())}")

print("\n[OK] Data fields endpoint working!")


# ── Step 4: Full extraction ──────────────────────────────────────────
print("\n" + "=" * 60)
print(f"EXTRACTING ALL {total_count} FIELDS")
print("=" * 60)

PAGE_SIZE = 50
all_fields = []
offset = 0

while offset < total_count:
    params = {
        "region": "USA",
        "delay": 1,
        "universe": "TOP3000",
        "instrumentType": "EQUITY",
        "limit": PAGE_SIZE,
        "offset": offset,
    }

    r = sess.get(test_url, params=params)

    # Handle rate limiting
    if r.status_code == 429:
        retry_after = int(r.headers.get("Retry-After", 5))
        print(f"  Rate limited — waiting {retry_after}s ...")
        time.sleep(retry_after + 1)
        continue  # Retry same offset

    if r.status_code == 401:
        print("  Session expired — re-authenticating ...")
        r2 = sess.post(auth_url, auth=HTTPBasicAuth(email, password))
        if r2.status_code == 429:
            retry_after = int(r2.headers.get("Retry-After", 30))
            print(f"  Auth rate limited — waiting {retry_after}s ...")
            time.sleep(retry_after + 1)
            r2 = sess.post(auth_url, auth=HTTPBasicAuth(email, password))
        if r2.status_code != 201:
            print(f"[FAIL] Re-auth failed: {r2.status_code} {r2.text}")
            break
        continue  # Retry same offset with new session

    if r.status_code != 200:
        print(f"  [ERROR] Status {r.status_code} at offset {offset}: {r.text[:200]}")
        break

    page = r.json()
    results = page.get("results", [])
    all_fields.extend(results)
    offset += PAGE_SIZE

    # Progress
    pct = len(all_fields) / total_count * 100
    print(f"  [{pct:5.1f}%] {len(all_fields):,} / {total_count:,} fields", end="\r")

    # Respect rate limits: 30 req/min = ~2s between requests
    remaining = int(r.headers.get("X-RateLimit-Remaining-Minute", 30))
    if remaining < 5:
        print(f"\n  Rate limit low ({remaining} remaining) — sleeping 5s ...")
        time.sleep(5)
    else:
        time.sleep(0.5)  # Conservative base delay

print(f"\n\n  Done! Fetched {len(all_fields):,} fields total.")


# ── Step 5: Export ───────────────────────────────────────────────────
print("\n" + "=" * 60)
print("EXPORTING")
print("=" * 60)

# JSON
json_path = "brain_data_fields.json"
with open(json_path, "w") as f:
    json.dump(all_fields, f, indent=2)
print(f"  JSON: {json_path} ({os.path.getsize(json_path) / 1024 / 1024:.1f} MB)")

# CSV (flattened)
csv_path = "brain_data_fields.csv"
if all_fields:
    flat = []
    for field in all_fields:
        row = {}
        for k, v in field.items():
            if k == "dataset" and isinstance(v, dict):
                row["dataset_id"] = v.get("id", "")
                row["dataset_name"] = v.get("name", "")
            elif isinstance(v, (dict, list)):
                row[k] = json.dumps(v)
            else:
                row[k] = v
        flat.append(row)

    # Collect ALL keys across all rows (some fields may have extra keys)
    all_keys = []
    seen = set()
    for row in flat:
        for k in row:
            if k not in seen:
                all_keys.append(k)
                seen.add(k)

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=all_keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(flat)
    print(f"  CSV:  {csv_path} ({os.path.getsize(csv_path) / 1024 / 1024:.1f} MB)")

print("\n[DONE]")