# Disk-full → archive to S3 (Concert → AWX) scenario

A simulated **"disk full"** monitoring alert triggers a Concert Workflows flow
that **launches an AWX/Ansible job template** to move a file to **S3** and free
the space — the Concert → AWX orchestration pattern, end to end.

```
 bastion                      Concert Workflows                 AWX (Ansible)              AWS
 ───────                      ─────────────────                 ─────────────              ───
 simulate_disk_full.sh  ──▶   Disk_Full_Archive_To_S3
   (MCP trigger_flow,           │  gate: usage ≥ threshold
    solis-gw tunnel)            │  Job Templates Launch Create ──▶ Archive-To-S3-Free-Disk
                                │  poll Jobs Read (while)          (archive_to_s3.yml)
                                │  Jobs Stdout Read  ◀──────────── "ARCHIVED s3_uri=…"  ──▶ s3://bucket/…
                                ▼
                             result: archived_to = s3://…
```

Nothing here is large: the playbook creates a small sample file, uploads it, and
deletes the local copy. The point is the **orchestration + governance**, not the
bytes.

---

## One-time setup

### 1. S3 bucket + IAM (AWS)

`ansibleuser` is EC2-only, so grant it S3 on a dedicated bucket. Pick a globally
unique name and pre-create the bucket (this also settles name uniqueness):

```bash
BUCKET=kokunas-concert-disk-archive        # must be globally unique
aws s3api create-bucket --bucket "$BUCKET" \
  --region eu-central-1 \
  --create-bucket-configuration LocationConstraint=eu-central-1
```

Edit [`s3-iam-policy.json`](s3-iam-policy.json) (replace the bucket name) and
attach it to `ansibleuser`:

```bash
sed "s/REPLACE-WITH-YOUR-BUCKET/$BUCKET/g" s3-iam-policy.json > /tmp/s3pol.json
aws iam put-user-policy --user-name ansibleuser \
  --policy-name ConcertDiskArchive --policy-document file:///tmp/s3pol.json
```

### 2. Publish the Ansible content

AWX syncs this repo on launch, so just make sure `archive_to_s3.yml` and
`collections/requirements.yml` are pushed to `github.com/kokunas/concert-awx-demo`
(main). The job-template script below also forces a project re-sync.

### 3. Create the AWX job template

From the bastion (or anywhere with cluster access). Get the AWX host + admin
password from the cluster, then run the script:

```bash
export AWX_HOST=$(oc -n awx get route awx -o jsonpath='{.spec.host}')
export AWX_PW=$(oc -n awx get secret awx-admin-password -o jsonpath='{.data.password}' | base64 -d)
python3 setup/awx_add_s3_jobtemplate.py
```

Note the printed **job-template id** (e.g. `11`).

### 4. Create the Concert flow

The flow JSON is [`concert-flows/Disk_Full_Archive_To_S3.json`](concert-flows/Disk_Full_Archive_To_S3.json).
Create it in Concert with **Bob** (this is the natural-language / MCP path) — copy
the JSON to the bastion and ask Bob to validate and upsert it:

```
# in Bob, after `scp`-ing the JSON to the bastion:
valida y crea en Concert el workflow del fichero Disk_Full_Archive_To_S3.json
(usa fact_check_flow y luego upsert_flow en la carpeta /User/)
```

Then set two flow variables to your environment:

- `job_template_id` → the id from step 3
- `s3_bucket` → your bucket name

(You can set them as the flow's variable defaults, or pass them in the trigger
body — but the simulator only sends the alert fields, so defaults are simplest.)

---

## Run the demo

On the bastion, with the solis-gw tunnel up (tmux `mcp`):

```bash
export CONCERT_PASSWORD=...        # concertuser's password
./simulate_disk_full.sh web-prod-01 /var/log 96
```

The script fires a simulated disk-full alert and triggers the flow (async).

## Verify

- **Concert**: Logs/Executions → `Disk_Full_Archive_To_S3` → the run's `result`
  shows `archived_to = s3://…`. Or ask Bob: *"muéstrame la última ejecución de
  Disk_Full_Archive_To_S3"*.
- **AWX**: Jobs → `Archive-To-S3-Free-Disk` → stdout ends with `ARCHIVED s3_uri=…`.
- **AWS**: `aws s3 ls s3://$BUCKET/disk-archive/ --recursive`.

### Below-threshold path

`./simulate_disk_full.sh web-prod-01 /var/log 50` → usage < threshold (90), so the
flow takes the `else` branch and reports a **no-op** without touching AWX. Good to
show the governance/gate.
