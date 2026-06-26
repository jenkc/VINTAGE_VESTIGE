# KG_PHASE2_AWS_SETUP.md
# Phase 2 — AWS Setup

**Duration:** 2–3 days  
**Can run parallel with:** Phase 3 (Design Element Extraction)  
**Status:** 🔲 Not Started  
**Prerequisite:** Phase 1 schema finalized

---

## Checklist

### Account + Billing
- [ ] AWS account created at aws.amazon.com
- [ ] Root MFA enabled
- [ ] IAM user created for development (don't use root)
- [ ] Billing alert created: $50/month via CloudWatch
- [ ] Cost Explorer enabled
- [ ] Budget: $30/month reserved for Neptune dev usage

### Neptune Serverless Cluster
- [ ] Navigate to Amazon Neptune in AWS Console
- [ ] Create DB cluster → Serverless
- [ ] Engine version: Neptune 1.3+ (latest stable)
- [ ] Query languages enabled: **openCypher** + **SPARQL** (both)
- [ ] Region: `us-east-1` (or your closest)
- [ ] Min capacity: **1 NCU**
- [ ] Max capacity: **8 NCU** (sufficient for 866 nodes, increase later)
- [ ] VPC: default VPC is fine for development
- [ ] Cluster endpoint URL saved to `.env`

### S3 Bucket
- [ ] Bucket name: `vintage-vestige-neptune-data`
- [ ] Region: **same as Neptune cluster** (critical)
- [ ] Block all public access: enabled
- [ ] Versioning: enabled
- [ ] Folder created: `s3://vintage-vestige-neptune-data/load/`

### IAM Role
- [ ] Role name: `NeptuneLoadFromS3`
- [ ] Trust policy: Neptune service principal
- [ ] Inline policy attached:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::vintage-vestige-neptune-data",
        "arn:aws:s3:::vintage-vestige-neptune-data/*"
      ]
    }
  ]
}
```

- [ ] Role ARN saved to `.env` as `NEPTUNE_LOAD_ROLE_ARN`
- [ ] Role associated with Neptune cluster

### Neptune Notebook
- [ ] Neptune Notebook created (managed Jupyter inside VPC)
- [ ] Kernel: Python 3 + Gremlin/openCypher extensions
- [ ] Can execute: `%%oc` (openCypher) and `%%gremlin` cells
- [ ] Test query executes: `MATCH (n) RETURN count(n)` → returns 0

### Environment Variables
Add to `.env`:
```bash
NEPTUNE_ENDPOINT=your-cluster.cluster-xyz.us-east-1.neptune.amazonaws.com
NEPTUNE_PORT=8182
NEPTUNE_LOAD_ROLE_ARN=arn:aws:iam::account:role/NeptuneLoadFromS3
NEPTUNE_REGION=us-east-1
S3_NEPTUNE_BUCKET=vintage-vestige-neptune-data
```

### Validation
- [ ] Neptune Notebook can connect to cluster
- [ ] Empty graph query returns 0 nodes
- [ ] S3 bucket accessible from Neptune (test with a tiny CSV load)

---

## Cost Estimate

| Resource | Estimated Cost |
|---|---|
| Neptune Serverless (dev usage) | $5–15/month |
| S3 storage (CSV files < 100MB) | < $1/month |
| Data transfer | < $1/month |
| **Total** | **< $20/month** |

At production scale (866 nodes, 7,324 bridges): Neptune Serverless will
auto-scale down to near-zero when not in use. Only pay for active query time.
