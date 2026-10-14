#!/usr/bin/env python3
"""Add the 'Archive-To-S3-Free-Disk' AWX job template for the disk-full demo.

Re-syncs the 'Concert AWX Demo' project (to pull the new archive_to_s3.yml),
creates the job template against the same project/inventory as the EC2 ones,
copies the AWS credential from 'Provision-Demo-EC2', enables
ask_variables_on_launch (so Concert's extra_vars are honoured at launch), and
prints the new job-template id.

Reads AWX_HOST and AWX_PW from the environment. SSL verification is disabled
(cluster edge cert). Run it after pushing archive_to_s3.yml to the project repo.

    export AWX_HOST=<awx route host>          # no scheme
    export AWX_PW=<awx admin password>
    python3 awx_add_s3_jobtemplate.py
"""
import base64, json, os, ssl, time, urllib.error, urllib.parse, urllib.request

HOST = os.environ["AWX_HOST"].rstrip("/")
PW = os.environ["AWX_PW"]
AUTH = "Basic " + base64.b64encode(f"admin:{PW}".encode()).decode()
CTX = ssl._create_unverified_context()

PROJECT_NAME = "Concert AWX Demo"
INVENTORY_NAME = "Demo Localhost"
SOURCE_JT = "Provision-Demo-EC2"      # to copy the AWS credential from
NEW_JT = "Archive-To-S3-Free-Disk"
PLAYBOOK = "archive_to_s3.yml"


def api(method, path, body=None):
    url = f"https://{HOST}/api/v2{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", AUTH)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, context=CTX, timeout=60) as r:
            raw = r.read().decode()
            return r.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        body = e.read().decode() or "{}"
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"raw": body}


def one(path, name):
    s, d = api("GET", f"{path}?name={urllib.parse.quote(name)}")
    if s == 200 and d.get("count", 0) > 0:
        return d["results"][0]
    raise SystemExit(f"[!] {path} '{name}' not found ({s}): {json.dumps(d)[:200]}")


# Resolve project / inventory
proj = one("/projects/", PROJECT_NAME)
inv = one("/inventories/", INVENTORY_NAME)
print(f"[=] project id={proj['id']}  inventory id={inv['id']}")

# Re-sync the project so the new playbook is available
s, d = api("POST", f"/projects/{proj['id']}/update/", {})
if s in (200, 201, 202):
    upd_id = d.get("id")
    print(f"[*] project sync started (job {upd_id}); waiting…")
    for _ in range(60):
        s2, d2 = api("GET", f"/project_updates/{upd_id}/")
        if d2.get("status") in ("successful", "failed", "error", "canceled"):
            print(f"    sync status = {d2.get('status')}")
            break
        time.sleep(5)
else:
    print(f"[!] could not start project sync ({s}); continuing: {json.dumps(d)[:200]}")

# Create (or find) the job template
s, d = api("GET", f"/job_templates/?name={urllib.parse.quote(NEW_JT)}")
if s == 200 and d.get("count", 0) > 0:
    jt = d["results"][0]
    print(f"[=] job template '{NEW_JT}' already exists id={jt['id']}")
else:
    s, jt = api("POST", "/job_templates/", {
        "name": NEW_JT,
        "job_type": "run",
        "inventory": inv["id"],
        "project": proj["id"],
        "playbook": PLAYBOOK,
        "ask_variables_on_launch": True,
        "ask_credential_on_launch": False,
        "verbosity": 1,
        "description": "Disk-full remediation: archive a file to S3 to free space.",
    })
    if s not in (200, 201):
        raise SystemExit(f"[!] job template create failed {s}: {json.dumps(jt)[:300]}")
    print(f"[+] job template '{NEW_JT}' created id={jt['id']}")

# Copy the AWS credential(s) from the source JT
src = one("/job_templates/", SOURCE_JT)
s, creds = api("GET", f"/job_templates/{src['id']}/credentials/")
copied = []
for c in creds.get("results", []):
    s2, _ = api("POST", f"/job_templates/{jt['id']}/credentials/", {"id": c["id"]})
    copied.append(f"{c['name']}({c['id']})->{s2}")
print(f"[+] credentials copied from '{SOURCE_JT}': {copied or 'none found'}")

print("\n=== RESULT ===")
print(json.dumps({"job_template": NEW_JT, "id": jt["id"], "playbook": PLAYBOOK}))
print(f"\nSet the Concert flow variable  job_template_id = \"{jt['id']}\"")
