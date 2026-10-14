# concert-awx-demo

Ansible content for the **IBM Concert Workflows → AWX** orchestration demo
(RFI de Orquestación). AWX pulls this repo as a *Project*; the playbooks are
run by AWX *Job Templates* that **Concert Workflows** launches through the
`Ansible / Automation Platform / Automation Controller` blocks
(`Job Templates Launch Create` → poll `Jobs Read` → `Jobs Stdout Read`).

## Contents

| File | Role |
|---|---|
| [`provision_ec2.yml`](provision_ec2.yml) | Creates a transient **t3.micro** in `eu-central-1` (Frankfurt): finds the latest Amazon Linux 2023 AMI, ensures a demo security group, launches the instance, prints a `PROVISIONED ...` summary that Concert collects as the job output. |
| [`terminate_ec2.yml`](terminate_ec2.yml) | Tears everything down (instances tagged `managed_by=concert-awx` + the security group). Wire as a second job template so the demo self-cleans. |
| [`archive_to_s3.yml`](archive_to_s3.yml) | **Disk-full remediation:** creates a sample file, uploads it to **S3**, deletes the local copy to free space, prints an `ARCHIVED s3_uri=...` summary. Launched by the `Disk_Full_Archive_To_S3` Concert flow. See [`DISK_FULL_SCENARIO.md`](DISK_FULL_SCENARIO.md). |
| [`concert-flows/Disk_Full_Archive_To_S3.json`](concert-flows/Disk_Full_Archive_To_S3.json) | The Concert Workflows flow: disk-full alert → (gate on usage ≥ threshold) → launch the S3 job template → poll → read stdout → report. Import/create it in Concert (e.g. via Bob `upsert_flow`). |
| [`simulate_disk_full.sh`](simulate_disk_full.sh) | Bastion script that simulates the disk-full alert and triggers the flow through the Concert MCP (`trigger_flow`) over the solis-gw tunnel. |
| [`setup/awx_add_s3_jobtemplate.py`](setup/awx_add_s3_jobtemplate.py) | Creates the `Archive-To-S3-Free-Disk` AWX job template (copies the AWS credential, enables `ask_variables_on_launch`) and prints its id. |
| [`s3-iam-policy.json`](s3-iam-policy.json) | Minimal S3 IAM policy to attach to `ansibleuser` for the disk-full scenario. |
| [`collections/requirements.yml`](collections/requirements.yml) | `amazon.aws` — AWX installs it on project sync (the stock EE has boto3 but not this collection). |
| [`inventory/hosts.ini`](inventory/hosts.ini) | Just `localhost` — the playbooks run on the AWX control node against the AWS API. |

## AWS credentials

The playbooks use no embedded keys. AWX injects AWS credentials from an
**"Amazon Web Services"** credential (scoped IAM user `ansibleuser`,
EC2-only, limited to `eu-central-1`) as `AWS_ACCESS_KEY_ID` /
`AWS_SECRET_ACCESS_KEY` at run time.

> **For the disk-full / S3 scenario** the EC2-only policy is not enough —
> `ansibleuser` also needs S3 access to the archive bucket. Pre-create the
> bucket and attach [`s3-iam-policy.json`](s3-iam-policy.json) (edit the bucket
> name first). Details in [`DISK_FULL_SCENARIO.md`](DISK_FULL_SCENARIO.md).

## Extra variables (optional, set on the job template or at launch)

- `aws_region` (default `eu-central-1`)
- `instance_type` (default `t3.micro`)
- `instance_name` (default `concert-awx-demo`)
- `ssh_cidr` (default empty = no inbound SSH rule)
