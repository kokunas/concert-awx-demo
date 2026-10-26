# PHP2Shell demo flows (IBM Concert Workflows)

| Flow | What it does |
|---|---|
| `Remediate_PHP2Shell.json` | Approval (Common/Pause), then launches AWX JT `Remediate-PHP2Shell` (OpenShift copy of php-portal to PHP 8.4.27, rescan, report to Concert). |
| `Reset_PHP2Shell_Demo.json` | Launches AWX JT `Reset-PHP2Shell-Demo` (back to PHP 8.4.24) before each rehearsal. |
| `vm/RHEL_SCAN_OSCAP.json` | Copy of IBM's `RHEL_SCAN_OSCAP_GRYPE` sample without the Grype step (OpenSCAP + Red Hat OVAL only). |
| `vm/Remediation_Master/` | IBM's `Remediation_Master` sample; its `Apply_Linux_Patch` helper restarts php-fpm and httpd instead of rebooting the host. |

The two `vm/` items are derived from IBM's samples in
[github.com/IBM/Concert](https://github.com/IBM/Concert/tree/main/concert-workflows/Vulnerability) (Apache-2.0).
