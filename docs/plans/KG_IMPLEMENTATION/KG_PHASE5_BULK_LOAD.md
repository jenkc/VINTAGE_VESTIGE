# KG_PHASE5_BULK_LOAD.md
# Phase 5 — Bulk Load + Validation

**Duration:** 1–2 days  
**Status:** 🔲 Not Started  
**Prerequisite:** Phase 4 (all CSV files validated, zero errors)  
**Output:** Populated Neptune graph, all 3 validation queries passing  
**Last Updated:** March 2026 (v2.0)

---

## Checklist

### Pre-Load
- [ ] All CSVs validated by `validate_exports.py` (zero errors)
- [ ] Neptune cluster running and reachable from Neptune Notebook
- [ ] S3 bucket exists in same region as Neptune
- [ ] IAM role attached to Neptune cluster

### Upload to S3
- [ ] Run `scripts/kg/upload_to_s3.py`
- [ ] Verify all files appear in `s3://vintage-vestige-neptune-data/load/`
- [ ] File count matches expected (14 CSV files)

```python
# scripts/kg/upload_to_s3.py
import boto3
from pathlib import Path

s3 = boto3.client('s3', region_name='us-east-1')
bucket = 'vintage-vestige-neptune-data'

for csv_file in sorted(Path('data/neptune').glob('*.csv')):
    key = f"load/{csv_file.name}"
    s3.upload_file(str(csv_file), bucket, key)
    print(f"✅ Uploaded {csv_file.name}")
```

### Bulk Load
- [ ] Run bulk loader via Neptune Notebook or `scripts/kg/trigger_load.py`
- [ ] Save `load_id` from response
- [ ] Monitor until `LOAD_COMPLETED`

```python
# scripts/kg/trigger_load.py
import requests, time, os

endpoint = os.getenv('NEPTUNE_ENDPOINT')
role_arn = os.getenv('NEPTUNE_LOAD_ROLE_ARN')
bucket   = os.getenv('S3_NEPTUNE_BUCKET')

response = requests.post(
    f"https://{endpoint}:8182/loader",
    json={
        "source": f"s3://{bucket}/load/",
        "format": "csv",
        "iamRoleArn": role_arn,
        "region": "us-east-1",
        "failOnError": "FALSE",
        "parallelism": "MEDIUM",
        "updateSingleCardinalityProperties": "FALSE",
        "queueRequest": "TRUE"
    },
    verify=False  # Neptune uses self-signed cert inside VPC
)

load_id = response.json()['payload']['loadId']
print(f"Load started: {load_id}")

while True:
    status_resp = requests.get(
        f"https://{endpoint}:8182/loader/{load_id}",
        verify=False
    ).json()
    status = status_resp['payload']['overallStatus']['status']
    total = status_resp['payload']['overallStatus'].get('totalRecords', '?')
    print(f"  Status: {status} | Records: {total}")
    if status in ['LOAD_COMPLETED', 'LOAD_FAILED']:
        break
    time.sleep(15)

if status == 'LOAD_COMPLETED':
    print("✅ Load complete!")
else:
    print("❌ Load failed. Check errors:")
    print(status_resp['payload'].get('errors', {}))
```

### Post-Load Validation (run in Neptune Notebook)

- [ ] **Node counts match exports:**

```cypher
MATCH (g:Garment) RETURN count(g) as garments
// Expected: ~1,500 (enriched products only)

MATCH (b:Bridge) RETURN count(b) as bridges
// Expected: ~10,000–15,000 (recomputed after data growth)

MATCH (de:DesignElement) RETURN count(de) as elements
// Expected: matches design_elements_seed.py count

MATCH (e:Era) RETURN count(e) as eras
// Expected: 15

MATCH (c:Collection) RETURN count(c) as collections
// Expected: ≥3 (distinct platforms in Supabase — check with SELECT DISTINCT platform FROM products)
```

- [ ] **Edge counts look right:**

```cypher
MATCH ()-[r:CONNECTED_VIA]->() RETURN count(r)
MATCH ()-[r:CONNECTS]->() RETURN count(r)
MATCH ()-[r:ARGUES_THROUGH]->() RETURN count(r)
MATCH ()-[r:FROM_ERA]->() RETURN count(r)
```

- [ ] **Spot-check known high-score bridge (bridge_score = 0.9348):**

```cypher
// Find the bridge with highest score (ID will vary after data growth recompute)
MATCH (b:Bridge)
WHERE b.score > 0.93
MATCH (b)-[:ARGUES_THROUGH]->(de:DesignElement)
RETURN b.score, b.narrative, collect(de.name) as elements
LIMIT 5
```

- [ ] **Validation Query 1 — Influence Chain returns results:**

```cypher
MATCH (modern:Garment {platform: 'fashionpedia'})
  -[:CONNECTED_VIA]->(b1:Bridge)
  -[:CONNECTS]->(g2:Garment)
  -[:CONNECTED_VIA]->(b2:Bridge)
  -[:CONNECTS]->(historical:Garment)
WHERE historical.platform IN ['met_museum', 'smithsonian']
  AND b1.score > 0.6 AND b2.score > 0.6
RETURN modern.title, b1.narrative, g2.title, b2.narrative, historical.title
LIMIT 5
```

- [ ] **Validation Query 2 — Design Movement returns results:**

```cypher
MATCH (de:DesignElement)
  <-[:ARGUES_THROUGH]-(b:Bridge)
  -[:CONNECTS]->(g:Garment)
  -[:FROM_ERA]->(era:Era)
WITH de, count(DISTINCT era) as era_count,
     collect(DISTINCT era.name) as eras,
     count(b) as bridge_count
WHERE era_count >= 2
RETURN de.name, era_count, eras, bridge_count
ORDER BY bridge_count DESC
LIMIT 10
```

- [ ] **Validation Query 3 — Cross-Institutional bridges return results:**

```cypher
MATCH (g1:Garment {platform: 'met_museum'})
  -[:CONNECTED_VIA]->(b:Bridge)
  -[:CONNECTS]->(g2:Garment {platform: 'smithsonian'})
WHERE b.score > 0.6
RETURN g1.title, b.narrative, g2.title, b.score
ORDER BY b.score DESC
LIMIT 10
```

- [ ] All 3 validation queries return ≥ 1 result
- [ ] Performance: simple traversal query < 500ms
- [ ] `KG_MASTER_PLAN.md` Phase 5 checkboxes updated

---

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `LOAD_FAILED` with "invalid edge" | `~from` or `~to` references non-existent node | Run `validate_exports.py`, fix orphan edges |
| `LOAD_FAILED` with "duplicate ID" | Duplicate `~id` in a node file | Add deduplication to export script |
| Validation query returns 0 | Edges not loaded or wrong direction | Check edge CSV headers, verify `~from`/`~to` columns |
| Neptune unreachable | VPC routing | Use Neptune Notebook (inside VPC) not local curl |
| Slow queries > 2s | Missing index or NCU limit | Increase max NCUs temporarily |
