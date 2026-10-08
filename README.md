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
| [`collections/requirements.yml`](collections/requirements.yml) | `amazon.aws` — AWX installs it on project sync (the stock EE has boto3 but not this collection). |
| [`inventory/hosts.ini`](inventory/hosts.ini) | Just `localhost` — the playbooks run on the AWX control node against the AWS API. |

## AWS credentials

The playbooks use no embedded keys. AWX injects AWS credentials from an
**"Amazon Web Services"** credential (scoped IAM user `ansibleuser`,
EC2-only, limited to `eu-central-1`) as `AWS_ACCESS_KEY_ID` /
`AWS_SECRET_ACCESS_KEY` at run time.

## Extra variables (optional, set on the job template or at launch)

- `aws_region` (default `eu-central-1`)
- `instance_type` (default `t3.micro`)
- `instance_name` (default `concert-awx-demo`)
- `ssh_cidr` (default empty = no inbound SSH rule)
