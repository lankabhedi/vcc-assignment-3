# VCC Assignment 3: Auto-Scaling Local VM to GCP Cloud

> **Student:** Samnit Mehandiratta (M25AI2087)  
> **Email:** m25ai2087@iitj.ac.in  
> **Institution:** IIT Jodhpur  
> **Course:** CSL7510 VCC  
> **Instructor:** Sumit Kalra

---

## 📋 Overview

This project implements an auto-scaling solution that monitors resource usage on a local Virtual Machine and automatically scales to Google Cloud Platform (GCP) when CPU or RAM usage exceeds **75%**.

### Key Features

- ✅ Lightweight Alpine Linux VM (~60MB)
- ✅ Real-time resource monitoring (5s intervals)
- ✅ Configurable thresholds (default: 75%)
- ✅ Automatic GCP VM provisioning
- ✅ Managed Instance Group support
- ✅ Sample web server with load generator

---

## 🏗️ Project Structure

```
VCC_Assignment_3/
├── docs/
│   ├── report.md              # Detailed documentation report
│   └── architecture.svg       # Architecture diagram
├── scripts/
│   ├── setup_vm.sh            # VirtualBox VM setup script
│   ├── monitor.py             # Resource monitoring script
│   └── scale_to_gcp.py        # GCP auto-scaling script
├── app/
│   └── sample_server.py       # Web server + load generator
├── config/
│   └── monitor_state.json     # Monitor state (auto-generated)
├── logs/
│   └── monitor.log            # Monitoring logs (auto-generated)
├── iso/
│   └── alpine-virt-3.23.3-x86_64.iso  # Alpine Linux ISO
├── README.md                  # This file
└── assignment_details.txt     # Original assignment brief
```

---

## 🚀 Quick Start

### Prerequisites

1. **VirtualBox 7.x** - [Download](https://www.virtualbox.org/wiki/Downloads)
2. **Python 3.8+** - `python3 --version`
3. **Google Cloud SDK** - [Install](https://cloud.google.com/sdk/docs/install)
4. **GCP Account** - Active project with billing enabled

### Step 1: Setup VirtualBox VM

```bash
# Make setup script executable
chmod +x scripts/setup_vm.sh

# Run VM setup
./scripts/setup_vm.sh

# Start the VM (GUI mode for installation)
VBoxManage startvm "alpine-autoscale" --type gui
```

### Step 2: Install Alpine Linux

```bash
# Login credentials
Username: root
Password: (none, press Enter)

# Run setup commands in VM
setup-disk          # Install to disk
setup-interfaces    # Configure network
setup-timezone      # Set timezone
setup-hostname      # Set hostname (e.g., alpine-vm)

# Install required packages
apk add python3 py3-pip openssh curl

# Enable SSH
rc-update add sshd
rc-service sshd start

# Set root password
passwd
```

### Step 3: Configure GCP

```bash
# Authenticate with GCP
gcloud auth login

# Set your project
gcloud config set project YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable compute.googleapis.com
gcloud services enable cloudresourcemanager.googleapis.com

# Verify setup
gcloud auth list
gcloud config list
```

### Step 4: Copy Scripts to VM

```bash
# From host machine, copy scripts to VM
scp -P 2222 scripts/monitor.py root@localhost:/root/
scp -P 2222 scripts/scale_to_gcp.py root@localhost:/root/
scp -P 2222 app/sample_server.py root@localhost:/root/

# Or use shared folder / direct download
```

### Step 5: Run the Auto-Scaling System

```bash
# Terminal 1: Start the resource monitor
python3 scripts/monitor.py

# Terminal 2: Start the sample web server
python3 app/sample_server.py server --port 8080

# Terminal 3: Generate load to trigger scaling
python3 app/sample_server.py load --cpu 85 --ram 85 --duration 600
```

---

## 📖 Usage Guide

### Resource Monitor

```bash
# Run with default settings (75% threshold, 5s interval)
python3 scripts/monitor.py

# Configuration (edit monitor.py)
CONFIG = {
    "cpu_threshold": 75.0,        # CPU trigger percentage
    "ram_threshold": 75.0,        # RAM trigger percentage
    "check_interval": 5,          # Monitoring interval (seconds)
    "consecutive_triggers": 3,    # Triggers before scaling
    "cooldown_period": 300,       # Cooldown after scaling (seconds)
    "gcp_project": "your-project-id",
    "gcp_zone": "us-central1-a",
}
```

### GCP Scaling Script

```bash
# Setup GCP project
python3 scripts/scale_to_gcp.py setup --project YOUR_PROJECT_ID

# Create a VM instance
python3 scripts/scale_to_gcp.py create --project YOUR_PROJECT_ID

# List all instances
python3 scripts/scale_to_gcp.py list --project YOUR_PROJECT_ID

# Delete an instance
python3 scripts/scale_to_gcp.py delete --project YOUR_PROJECT_ID --name autoscale-vm-123456

# Create Managed Instance Group with auto-scaling
python3 scripts/scale_to_gcp.py mig --project YOUR_PROJECT_ID \
    --group-name autoscale-group \
    --min-instances 1 \
    --max-instances 5 \
    --target-cpu 0.75

# Estimate costs
python3 scripts/scale_to_gcp.py cost --machine-type e2-medium --hours 24
```

### Sample Server

```bash
# Start web server
python3 app/sample_server.py server --port 8080

# Generate CPU/RAM load
python3 app/sample_server.py load --cpu 80 --ram 80 --duration 300

# HTTP flood test
python3 app/sample_server.py flood --url http://localhost:8080/health --requests 1000
```

### Server Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Server info page |
| `GET /health` | Health check (returns JSON) |
| `GET /compute?seconds=5` | CPU-intensive task |
| `GET /memory?mb=100` | Allocate memory |

---

## 🏛️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    LOCAL VM (VirtualBox)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Alpine Linux │─▶│   Monitor    │─▶│  Threshold >75%  │  │
│  │   (~60MB)    │  │  (CPU/RAM)   │  │   (3 triggers)   │  │
│  └──────────────┘  └──────────────┘  └─────────┬────────┘  │
└─────────────────────────────────────────────────┼───────────┘
                                                  │ SCALE
                                                  ▼
┌─────────────────────────────────────────────────────────────┐
│                  GOOGLE CLOUD PLATFORM                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   gcloud     │─▶│   Compute    │─▶│    Managed       │  │
│  │     CLI      │  │   Engine     │  │  Instance Group  │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

See `docs/architecture.svg` for detailed diagram.

---

## 🧪 Testing

### Test Scenarios

```bash
# Test 1: Normal operation (no scaling expected)
python3 app/sample_server.py server --port 8080
# Monitor should show <75% usage

# Test 2: Trigger scaling
python3 app/sample_server.py load --cpu 85 --ram 85 --duration 600
# Monitor should trigger GCP scaling after 3 consecutive checks

# Test 3: Verify GCP instance
gcloud compute instances list
# Should see new autoscale-vm-* instance
```

### Expected Log Output

```
2026-03-29 20:00:00 - INFO - CPU:  45.2% | RAM:  52.1% | Disk:  35.0%
2026-03-29 20:00:10 - INFO - CPU:  78.2% | RAM:  76.8% | Disk:  35.0%
2026-03-29 20:00:10 - WARNING - Threshold exceeded! Consecutive: 1/3
2026-03-29 20:00:15 - WARNING - Threshold exceeded! Consecutive: 2/3
2026-03-29 20:00:20 - WARNING - Threshold exceeded! Consecutive: 3/3
2026-03-29 20:00:20 - CRITICAL - AUTO-SCALE TRIGGERED!
2026-03-29 20:00:25 - INFO - Successfully created GCP instance
```

---

## 🔧 Troubleshooting

### Common Issues

**VirtualBox VM won't start:**
```bash
# Enable virtualization in BIOS
# Close other VMs/hypervisors
VBoxManage --version  # Verify installation
```

**GCP authentication failed:**
```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

**Scaling not triggering:**
```bash
# Check logs
tail -f logs/monitor.log

# Verify threshold config in monitor.py
# Ensure GCP project is set correctly
```

**Instance creation fails:**
```bash
# Check billing is enabled
# Verify API is enabled
gcloud services enable compute.googleapis.com

# Check quota
gcloud compute project-info describe --project YOUR_PROJECT_ID
```

---

## 📊 Monitoring & Logs

```bash
# View live monitoring logs
tail -f logs/monitor.log

# Check monitor state
cat config/monitor_state.json

# GCP instance status
gcloud compute instances list --project YOUR_PROJECT_ID

# VM resource usage (on VM)
top
free -h
df -h
```

---

## 💰 Cost Estimation

```bash
# Estimate costs for e2-medium
python3 scripts/scale_to_gcp.py cost --machine-type e2-medium --hours 24

# Output:
# Machine Type: e2-medium
# Hourly Rate: $0.0332
# Duration: 24 hours
# Estimated Cost: $0.80
```

**Note:** Actual costs vary by region and usage. Always set budget alerts in GCP.

---

## 📦 Deliverables

| # | Deliverable | Link |
|---|-------------|------|
| 1 | **Document Report** (step-by-step implementation) | [docs/report.pdf](docs/report.pdf) |
| 2 | **Architecture Diagram** (local VM → monitor → GCP) | [docs/architecture.svg](docs/architecture.svg) |
| 3 | **Source Code Repository** (scripts, app, configs) | [github.com/lankabhedi/vcc-assignment-3](https://github.com/lankabhedi/vcc-assignment-3) |
| 4 | **Video Demo** (auto-scaling simulation) | [docs/demo_video.mp4](docs/demo_video.mp4) |
| 5 | **Plagiarism Declaration** | [docs/plagiarism_declaration.md](docs/plagiarism_declaration.md) |

---

## 🔒 Security Notes

1. **GCP Credentials**: Never commit service account keys
2. **SSH Keys**: Use key-based authentication for VMs
3. **Firewall Rules**: Restrict access to necessary ports
4. **Billing Alerts**: Set up GCP budget alerts

---

## 📚 References

- [Alpine Linux Documentation](https://wiki.alpinelinux.org/)
- [VirtualBox Manual](https://www.virtualbox.org/manual/)
- [Google Cloud SDK](https://cloud.google.com/sdk/docs)
- [GCP Compute Engine](https://cloud.google.com/compute/docs)
- [Python Documentation](https://docs.python.org/3/)

---

## 📄 License

This project is submitted as part of CSL7510 VCC course requirements at IIT Jodhpur.

---

## ✉️ Contact

**Samnit Mehandiratta**  
M.Tech AI (2025-2027)  
Roll Number: M25AI2087  
Email: m25ai2087@iitj.ac.in  
IIT Jodhpur

---

## 🙏 Acknowledgments

- Instructor: Sumit Kalra, CSL7510 VCC
- IIT Jodhpur for providing computational resources
- Google Cloud Platform for educational credits
