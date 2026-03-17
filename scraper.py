import json, csv, os
from wqb import WQBSession
from dotenv import load_dotenv

load_dotenv()

email = os.getenv("WQB_EMAIL")
password = os.getenv("WQB_PASSWORD")
# Authenticate (session auto-refreshes tokens)
wqbs = WQBSession((email, password))

# Auto-paginate through ALL data fields
all_fields = []
for resp in wqbs.search_fields('USA', 1, 'TOP3000', limit=50):
    page = resp.json()
    all_fields.extend(page.get('results', []))
    print(f"Fetched {len(all_fields)}/{page.get('count', '?')} fields")

# Export to JSON (for LLM reference)
with open('brain_data_fields.json', 'w') as f:
    json.dump(all_fields, f, indent=2)

# Export to flat CSV
flat = []
for field in all_fields:
    row = {k: v for k, v in field.items() if k != 'dataset'}
    if isinstance(field.get('dataset'), dict):
        row['dataset_id'] = field['dataset'].get('id', '')
        row['dataset_name'] = field['dataset'].get('name', '')
    flat.append(row)

with open('brain_data_fields.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=flat[0].keys())
    writer.writeheader()
    writer.writerows(flat)