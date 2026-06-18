# netbox-vdi-billing

[![NetBox 4.5](https://img.shields.io/badge/NetBox-4.5.x-blue)](https://github.com/netbox-community/netbox)
[![NetBox 4.6](https://img.shields.io/badge/NetBox-4.6.x-blue)](https://github.com/netbox-community/netbox)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20me%20a%20coffee-dcpaul83-yellow?logo=buy-me-a-coffee)](https://buymeacoffee.com/dcpaul83)

A NetBox plugin for **cost-center-based VDI chargeback**. It calculates monthly costs from VM resources (vCPU, RAM, optional GPU surcharge) and groups them by cost center for internal billing reports.

> ☕ If this plugin saves you time, consider [buying me a coffee](https://buymeacoffee.com/dcpaul83)

---

## What it does

Each virtual machine in NetBox can be assigned to a **cost center** with a **billing profile**. The plugin then calculates monthly costs automatically and shows a consolidated chargeback report per cost center.

```
Billing Profile  +  VM Assignment  =  Chargeback Report
────────────────────────────────────────────────────────
"Standard VDI"      VM "vdi-user-01"   Cost Center: Engineering
$2.00/vCPU      →   4 vCPU             Department: R&D
$0.50/GB RAM        8 GB RAM           Assigned to: j.smith
                    ──────────         Monthly cost: $12.00
                    4×2 + 8×0.5 = 12
```

---

## Prerequisites

- **NetBox 4.5.x or 4.6.x**
- Python 3.10+
- No external dependencies (runs inside the NetBox virtualenv)
- Optional: `reportlab` for server-side PDF generation

### Optional: GPU surcharge

If you want to charge a GPU surcharge, create a custom field on Virtual Machines in NetBox:

*Customization → Custom Fields → Add*
- **Object type:** `virtualization | virtual machine`
- **Name:** `gpu`
- **Type:** Text or Boolean

The surcharge is applied automatically when this field has a truthy value.

---

## Installation

```bash
# 1. Install the plugin
sudo /opt/netbox/venv/bin/pip install \
  https://github.com/dc-paul-83/netbox-vdi-billing-plugin/archive/refs/heads/main.tar.gz

# 2. Add to configuration.py
sudo nano /opt/netbox/netbox/netbox/configuration.py
# Add: PLUGINS = ['netbox_vdi_billing']

# 3. Run database migration
cd /opt/netbox
sudo /opt/netbox/venv/bin/python netbox/manage.py migrate netbox_vdi_billing

# 4. Collect static files
sudo /opt/netbox/venv/bin/python netbox/manage.py collectstatic --no-input

# 5. Restart NetBox
sudo systemctl restart netbox netbox-rq
```

### Update

```bash
sudo /opt/netbox/venv/bin/pip install --upgrade --force-reinstall \
  https://github.com/dc-paul-83/netbox-vdi-billing-plugin/archive/refs/heads/main.tar.gz

cd /opt/netbox
sudo /opt/netbox/venv/bin/python netbox/manage.py migrate netbox_vdi_billing
sudo systemctl restart netbox netbox-rq
```

---

## Usage

### Step 1 — Create billing profiles

**VDI Billing → Configuration → Billing Profiles → Add**

A profile defines the pricing rules for a VM class:

| Field | Description | Example |
|---|---|---|
| **Name** | Profile identifier | `Standard VDI` |
| **Base Price** | Fixed monthly amount per VM | `$5.00` |
| **Price per vCPU** | Multiplied by the VM's vCPU count | `$2.00` |
| **Price per GB RAM** | Multiplied by the VM's RAM in GB | `$0.50` |
| **GPU Surcharge** | Added if the `gpu` custom field is set | `$80.00` |

**Example calculation** for a VM with 4 vCPU, 16 GB RAM, no GPU:
```
Base price:      $5.00
4 × $2.00:       $8.00
16 × $0.50:      $8.00
─────────────────────
Total:          $21.00/month
```

**Typical profiles:**

| Profile | Base | $/vCPU | $/GB RAM | GPU |
|---|---|---|---|---|
| Standard VDI | $5 | $2 | $0.50 | $0 |
| Persistent VDI | $10 | $3 | $0.75 | $0 |
| GPU Workstation | $15 | $4 | $1.00 | $80 |

> **No profile needed?** If a VM has a fixed contract price, set a **Fixed Price** directly on the assignment — it overrides the profile calculation.

---

### Step 2 — Assign VMs

**VDI Billing → Reports → All Assignments → Add**

| Field | Description | Required |
|---|---|---|
| **Virtual Machine** | The NetBox VM | ✅ |
| **Billing Profile** | Which profile to use for calculation | – |
| **Cost Center** | Any identifier: number, name, team, project | – |
| **Department** | Sub-group within the cost center | – |
| **Assigned To** | Username or team | – |
| **Fixed Price** | Fixed $/month — overrides profile | – |
| **Notes** | Internal notes | – |

> ⚠️ A VM without a profile and without a fixed price will show **$0.00**.

**Pricing priority:**
```
1. Fixed Price set?  → use fixed price
2. Profile set?      → base + vCPUs × price + RAM × price (+ GPU)
3. Nothing set?      → $0.00
```

---

### Step 3 — Chargeback overview

**VDI Billing → Reports → Chargeback Overview**

Shows all cost centers with:
- Number of VMs
- Monthly and annual totals
- Per-VM breakdown (vCPU, RAM, pricing source)
- **PDF button** per cost center for printable reports

---

### VM detail panel

On every NetBox VM detail page a **VDI Billing** panel appears showing:
- Cost center & department
- Assigned to
- Billing profile & pricing source
- Monthly and annual cost

---

## Bulk assignment

For large environments with many VMs, manual one-by-one assignment is impractical. Two approaches are available:

### Option A — Browser UI (NetBox Custom Scripts)

No SSH required. Scripts run directly in the browser under **Customization → Scripts**.

#### One-time setup

Tell NetBox where the scripts are located:

```bash
sudo nano /opt/netbox/netbox/netbox/configuration.py
```

Add:
```python
SCRIPTS_ROOT = '/opt/netbox/venv/lib/python3.x/site-packages/netbox_vdi_billing'
```

> Find the exact path with:
> `sudo find /opt/netbox/venv -name "scripts.py" -path "*/netbox_vdi_billing/*"`

Restart NetBox:
```bash
sudo systemctl restart netbox netbox-rq
```

#### Available scripts

**1. VDI Auto-Assignment**
Reads cost center and department automatically from NetBox fields.

| Option | Description |
|---|---|
| Default Profile | Profile applied to all standard VMs |
| Cost Center Field | `Tenant`, `Role`, `Cluster`, or a Custom Field |
| Department Field | Optional — same sources as cost center |
| GPU Cluster Pattern | Regex, e.g. `.*gpu.*` — these VMs get the GPU profile |
| GPU Profile | Separate profile for GPU VMs |
| Filter by Cluster / Role | Only process VMs matching a pattern |
| Overwrite existing | Also update already-assigned VMs |

> **Dry run:** Leave the "Commit" checkbox unchecked to preview changes without saving.

**2. VDI CSV Import**
Assign cost centers and profiles via a table.

CSV format (semicolon-separated):
```
vm_name;cost_center;department;profile
vdi-alice-01;Engineering;R&D;Standard VDI
vdi-bob-02;Sales;EMEA;Standard VDI
vdi-render-01;Design;Creative;GPU Workstation
```

Paste the CSV content into the text field in the browser, check "Commit" → done.

---

### Option B — CLI (Management Command)

```bash
cd /opt/netbox

# Dry run — show what would happen without saving
sudo /opt/netbox/venv/bin/python netbox/manage.py auto_assign_vdi --dry-run

# All VMs, use Tenant as cost center, apply "Standard VDI" profile
sudo /opt/netbox/venv/bin/python netbox/manage.py auto_assign_vdi \
  --profile "Standard VDI" \
  --cost-center-field tenant

# With GPU cluster detection
sudo /opt/netbox/venv/bin/python netbox/manage.py auto_assign_vdi \
  --profile "Standard VDI" \
  --cost-center-field tenant \
  --gpu-cluster-pattern ".*GPU.*" \
  --gpu-profile "GPU Workstation"

# Only VMs in specific clusters
sudo /opt/netbox/venv/bin/python netbox/manage.py auto_assign_vdi \
  --profile "Standard VDI" \
  --cost-center-field tenant \
  --filter-cluster "VDI-.*"

# Import from CSV file
sudo /opt/netbox/venv/bin/python netbox/manage.py auto_assign_vdi \
  --csv /tmp/vdi_assignments.csv
```

#### All options

| Option | Description | Default |
|---|---|---|
| `--profile NAME` | Default billing profile | – |
| `--cost-center-field` | `tenant`, `role`, `cluster`, `custom:fieldname` | `tenant` |
| `--department-field` | Same syntax as above, for department | – |
| `--gpu-cluster-pattern` | Regex matched against cluster name | – |
| `--gpu-profile NAME` | Profile for GPU VMs | – |
| `--filter-cluster` | Only VMs in clusters matching this regex | – |
| `--filter-role` | Only VMs with this role | – |
| `--overwrite` | Overwrite existing assignments | off |
| `--dry-run` | Preview only, no changes saved | off |
| `--csv FILE` | Import from CSV instead of auto-mapping | – |

---

## Automated operation (cron job)

If your VMs are synced from vCenter and change frequently, a daily cron job keeps assignments up to date — creating new entries and removing assignments for VMs that lost the VDI tag.

```bash
sudo crontab -e
```

Example (runs daily at 02:00):
```
0 2 * * * /opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py \
    auto_assign_vdi \
    --profile "Standard VDI" \
    --cost-center-field tenant \
    --filter-tag VDI \
    --cleanup-untagged \
    >> /var/log/netbox/vdi_billing.log 2>&1
```

Create the log directory once:
```bash
sudo mkdir -p /var/log/netbox
```

**What the cron job does:**
- ✅ New VMs (tagged `VDI`) → assignment created
- ✅ Already assigned VMs → skipped (no accidental overwrites)
- ✅ VMs whose tag was removed → assignment deleted
- ✅ Deleted VMs → assignment removed automatically via database cascade

---

## Menu structure

```
VDI Billing (sidebar)
├── Reports
│   ├── Chargeback Overview   ← main view with cost center totals
│   └── All Assignments       ← full list of VM assignments
└── Configuration
    └── Billing Profiles      ← manage pricing rules
```

---

## License

MIT — see [LICENSE](LICENSE)
