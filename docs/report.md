# Assignment 3: Auto-Scaling Local VM to GCP Cloud

## Document Report

**Student:** Samnit Mehandiratta  
**Roll Number:** M25AI2087  
**Email:** m25ai2087@iitj.ac.in  
**Program:** M.Tech AI (2025-2027)  
**Institution:** IIT Jodhpur  
**Course:** CSL7510 VCC  
**Instructor:** Sumit Kalra  

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [System Architecture](#2-system-architecture)
3. [Prerequisites](#3-prerequisites)
4. [Step-by-Step Implementation](#4-step-by-step-implementation)
5. [Testing and Validation](#5-testing-and-validation)
6. [Troubleshooting](#6-troubleshooting)
7. [Conclusion](#7-conclusion)

---

## 1. Introduction

### 1.1 Objective

This assignment implements an auto-scaling solution that monitors resource usage on a local Virtual Machine (VM) and automatically scales to Google Cloud Platform (GCP) when CPU or RAM usage exceeds 75%.

### 1.2 Key Components

1. **Local VM**: Alpine Linux running on VirtualBox (lightweight ~60MB OS)
2. **Resource Monitor**: Python script monitoring CPU/RAM usage
3. **Sample Application**: Web server with load generator for testing
4. **Cloud Scaling**: GCP Compute Engine integration via gcloud CLI
5. **Auto-Scaling Logic**: Threshold-based triggering with cooldown periods

### 1.3 Features

- Real-time resource monitoring (5-second intervals)
- Configurable thresholds (default: 75% CPU/RAM)
- Consecutive trigger requirement (prevents false positives)
- Cooldown period after scaling (prevents rapid scaling)
- Full GCP integration with instance creation
- Managed Instance Group support for production scaling

---

## 2. System Architecture

### 2.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         LOCAL ENVIRONMENT                           │
│  ┌─────────────────┐     ┌─────────────────┐     ┌───────────────┐ │
│  │  VirtualBox VM  │────▶│  Resource       │────▶│  Threshold    │ │
│  │  (Alpine Linux) │     │  Monitor        │     │  Detection    │ │
│  │                 │     │  (CPU/RAM)      │     │  (>75%)       │ │
│  └─────────────────┘     └─────────────────┘     └───────┬───────┘ │
└──────────────────────────────────────────────────────────┼──────────┘
                                                           │
                                                           │ SCALE
                                                           │ TRIGGER
                                                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      GOOGLE CLOUD PLATFORM                          │
│  ┌─────────────────┐     ┌─────────────────┐     ┌───────────────┐ │
│  │  gcloud CLI     │────▶│  Compute        │────▶│  Managed      │ │
│  │  / API          │     │  Engine VM      │     │  Instance     │ │
│  │                 │     │  (e2-medium)    │     │  Group        │ │
│  └─────────────────┘     └─────────────────┘     └───────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Data Flow

1. **Monitoring Phase**: Resource monitor checks CPU/RAM every 5 seconds
2. **Detection Phase**: When usage exceeds 75% for 3 consecutive checks
3. **Trigger Phase**: Scaling script invokes gcloud API
4. **Provisioning Phase**: GCP creates new VM instance
5. **Distribution Phase**: Load balancer distributes traffic

---

## 3. Prerequisites

### 3.1 Software Requirements

| Software | Version | Purpose |
|----------|---------|---------|
| VirtualBox | 7.x | Local VM hosting |
| Python | 3.8+ | Script execution |
| Google Cloud SDK | Latest | GCP integration |
| Alpine Linux ISO | 3.19+ | Lightweight OS |

### 3.2 GCP Requirements

1. **GCP Account**: Active Google Cloud Platform account
2. **Project**: GCP project with billing enabled
3. **APIs Enabled**:
   - Compute Engine API
   - Cloud Resource Manager API

### 3.3 Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| RAM | 4 GB | 8 GB |
| Storage | 10 GB | 20 GB |
| CPU | 2 cores | 4 cores |
| Network | 1 Mbps | 10 Mbps |

---

## 4. Step-by-Step Implementation

### 4.1 Creating the Local VM

#### Step 4.1.1: Download Alpine Linux

```bash
# Download Alpine Linux virtual ISO (approximately 60MB)
wget https://dl-cdn.alpinelinux.org/alpine/v3.19/releases/x86_64/alpine-virt-3.19.0-x86_64.iso
```

#### Step 4.1.2: Setup VirtualBox VM

```bash
# Navigate to project directory
cd VCC_Assignment_3/scripts

# Make setup script executable
chmod +x setup_vm.sh

# Run the VM setup script
./setup_vm.sh
```

#### Step 4.1.3: Manual VM Creation (Alternative)

```bash
# Create VM
VBoxManage createvm --name "alpine-autoscale" --ostype "Linux26_64" --register

# Configure system
VBoxManage modifyvm "alpine-autoscale" --memory 1024 --cpus 2
VBoxManage modifyvm "alpine-autoscale" --nic1 nat
VBoxManage modifyvm "alpine-autoscale" --natpf1 "guestssh,tcp,,2222,,22"

# Create disk
VBoxManage createmedium disk --filename "$HOME/VirtualBox VMs/alpine-autoscale/alpine-autoscale.vdi" --size 8192

# Add storage controllers
VBoxManage storagectl "alpine-autoscale" --name "SATA Controller" --add sata
VBoxManage storagectl "alpine-autoscale" --name "IDE Controller" --add ide

# Attach disk and ISO
VBoxManage storageattach "alpine-autoscale" --storagectl "SATA Controller" --port 0 --device 0 --type hdd --medium "$HOME/VirtualBox VMs/alpine-autoscale/alpine-autoscale.vdi"
VBoxManage storageattach "alpine-autoscale" --storagectl "IDE Controller" --port 0 --device 0 --type dvddrive --medium alpine-virt-3.19.0-x86_64.iso

# Start VM
VBoxManage startvm "alpine-autoscale" --type gui
```

#### Step 4.1.4: Alpine Linux Installation

```bash
# Login (default: root, no password)
login: root

# Setup disk
setup-disk

# Configure network (usually automatic via DHCP)
setup-interfaces

# Set timezone
setup-timezone

# Set hostname
setup-hostname

# Install packages
apk add python3 py3-pip openssh

# Enable SSH
rc-update add sshd
rc-service sshd start

# Set root password
passwd
```

### 4.2 Implementing Resource Monitoring

#### Step 4.2.1: Install Monitoring Script

```bash
# Copy monitoring script to VM (from host)
scp -P 2222 scripts/monitor.py root@localhost:/root/

# Or install directly on VM
cd /root
```

#### Step 4.2.2: Configure Monitoring

Edit `monitor.py` configuration section:

```python
CONFIG = {
    "cpu_threshold": 75.0,        # CPU threshold percentage
    "ram_threshold": 75.0,        # RAM threshold percentage
    "check_interval": 5,          # Check every 5 seconds
    "consecutive_triggers": 3,    # Number of consecutive triggers
    "cooldown_period": 300,       # 5 minutes cooldown after scaling
    "gcp_project": "your-project-id",
    "gcp_region": "us-central1",
    "gcp_zone": "us-central1-a",
}
```

#### Step 4.2.3: Run Monitor

```bash
# Make script executable
chmod +x monitor.py

# Run the monitor
python3 monitor.py
```

### 4.3 Configuring GCP Auto-Scaling

#### Step 4.3.1: Install GCP SDK (if not installed)

```bash
# Download and install
curl https://sdk.cloud.google.com | bash

# Initialize
gcloud init
```

#### Step 4.3.2: Authenticate with GCP

```bash
# Login
gcloud auth login

# Set project
gcloud config set project vm-scaling-assignment

# Verify
gcloud auth list
gcloud config get-value project
```

#### Step 4.3.3: Enable Required APIs

```bash
gcloud services enable compute.googleapis.com
gcloud services enable cloudresourcemanager.googleapis.com
```

#### Step 4.3.4: Test GCP Scaling

```bash
# Run setup
python3 scripts/scale_to_gcp.py setup --project vm-scaling-assignment

# Create test instance
python3 scripts/scale_to_gcp.py create --project vm-scaling-assignment

# List instances
python3 scripts/scale_to_gcp.py list --project vm-scaling-assignment
```

### 4.4 Deploying Sample Application

#### Step 4.4.1: Start Web Server

```bash
# On the VM
cd /root/app
python3 sample_server.py server --port 8080
```

#### Step 4.4.2: Generate Load

```bash
# In another terminal, generate CPU load
python3 sample_server.py load --cpu 80 --ram 80 --duration 300

# Or send HTTP requests
python3 sample_server.py flood --url http://localhost:8080/health --requests 1000
```

### 4.5 Complete Auto-Scaling Setup

#### Step 4.5.1: Start All Components

```bash
# Terminal 1: Resource Monitor
python3 scripts/monitor.py

# Terminal 2: Sample Server
python3 app/sample_server.py server --port 8080

# Terminal 3: Load Generator
python3 app/sample_server.py load --cpu 85 --ram 85 --duration 600
```

#### Step 4.5.2: Monitor Logs

```bash
# View monitoring logs
tail -f logs/monitor.log

# Expected output when threshold exceeded:
# [timestamp] - WARNING - Threshold exceeded! (CPU=85.5%, RAM=82.3%) Consecutive: 3/3
# [timestamp] - CRITICAL - AUTO-SCALE TRIGGERED!
# [timestamp] - INFO - Successfully created GCP instance: autoscale-vm-1234567890
```

---

## 5. Testing and Validation

### 5.1 Test Scenarios

| Test | Description | Expected Result |
|------|-------------|-----------------|
| T1 | Normal operation (< 75% usage) | No scaling triggered |
| T2 | Brief spike (> 75% for < 15s) | No scaling (consecutive check) |
| T3 | Sustained high usage (> 75% for > 15s) | Scaling triggered |
| T4 | Multiple triggers within cooldown | Second trigger ignored |
| T5 | GCP instance creation | VM created successfully |

### 5.2 Validation Commands

```bash
# Check local VM resources
top
free -h

# Check GCP instances
gcloud compute instances list

# Check monitoring logs
cat logs/monitor.log

# Verify auto-scaling
gcloud compute instance-groups managed describe autoscale-group --zone us-central1-a
```

### 5.3 Expected Output

```
======================================================================
Resource Monitor with Auto-Scaling
Author: Samnit Mehandiratta (M25AI2087), IIT Jodhpur
======================================================================
2026-03-29 20:00:00 - INFO - CPU:  45.2% | RAM:  52.1% | Disk:  35.0%
2026-03-29 20:00:05 - INFO - CPU:  68.5% | RAM:  61.3% | Disk:  35.0%
2026-03-29 20:00:10 - INFO - CPU:  78.2% | RAM:  76.8% | Disk:  35.0%
2026-03-29 20:00:10 - WARNING - Threshold exceeded! (CPU=78.2%, RAM=76.8%) Consecutive: 1/3
2026-03-29 20:00:15 - INFO - CPU:  82.1% | RAM:  79.5% | Disk:  35.0%
2026-03-29 20:00:15 - WARNING - Threshold exceeded! (CPU=82.1%, RAM=79.5%) Consecutive: 2/3
2026-03-29 20:00:20 - INFO - CPU:  85.3% | RAM:  81.2% | Disk:  35.0%
2026-03-29 20:00:20 - WARNING - Threshold exceeded! (CPU=85.3%, RAM=81.2%) Consecutive: 3/3
2026-03-29 20:00:20 - CRITICAL - AUTO-SCALE TRIGGERED!
2026-03-29 20:00:20 - CRITICAL - Reason: CPU=85.3%, RAM=81.2%
2026-03-29 20:00:25 - INFO - Successfully created GCP instance: autoscale-vm-1711739220
```

---

## 6. Troubleshooting

### 6.1 Common Issues

#### Issue 1: VirtualBox VM won't start
```bash
# Check VirtualBox installation
VBoxManage --version

# Check VT-x/AMD-V is enabled in BIOS
# Check no other hypervisor is running
```

#### Issue 2: GCP Authentication Failed
```bash
# Re-authenticate
gcloud auth login
gcloud auth application-default login

# Check project
gcloud config list
```

#### Issue 3: Scaling not triggering
```bash
# Check threshold configuration in monitor.py
# Verify consecutive_triggers setting
# Check logs: tail -f logs/monitor.log
```

#### Issue 4: GCP instance creation fails
```bash
# Check billing is enabled
# Verify APIs are enabled
# Check quota limits in GCP Console
gcloud compute instances list --project vm-scaling-assignment
```

### 6.2 Debug Mode

```bash
# Run monitor with verbose logging
python3 scripts/monitor.py 2>&1 | tee debug.log

# Test GCP connection
gcloud compute instances list --project vm-scaling-assignment --format=json
```

---

## 7. Conclusion

### 7.1 Summary

This implementation successfully demonstrates:
1. Local VM creation using VirtualBox and Alpine Linux
2. Real-time resource monitoring with configurable thresholds
3. Automatic scaling to GCP when resources exceed 75%
4. Complete integration with Google Cloud Platform
5. Sample application for testing and validation

### 7.2 Future Enhancements

1. **Multi-cloud support**: Add AWS and Azure scaling targets
2. **Kubernetes integration**: Scale to GKE instead of Compute Engine
3. **Cost optimization**: Implement spot/preemptible instance scaling
4. **Advanced metrics**: Add disk I/O and network monitoring
5. **Web dashboard**: Real-time monitoring UI with Grafana

### 7.3 Lessons Learned

1. Alpine Linux provides excellent minimal footprint for VMs
2. Consecutive trigger requirement prevents false scaling
3. Cooldown periods are essential for cost control
4. GCP's gcloud CLI provides robust automation capabilities
5. Resource monitoring requires careful threshold tuning

---

## Declaration

I, **Samnit Mehandiratta** (M25AI2087), declare that this implementation and documentation 
is my original work and has not been copied from any other source. All external resources 
and references have been appropriately acknowledged.

**Signature:** Samnit Mehandiratta  
**Date:** March 29, 2026  
**Place:** IIT Jodhpur

---

## References

1. Alpine Linux Documentation: https://wiki.alpinelinux.org/
2. VirtualBox Manual: https://www.virtualbox.org/manual/
3. Google Cloud SDK: https://cloud.google.com/sdk/docs
4. GCP Compute Engine: https://cloud.google.com/compute/docs
5. Python Documentation: https://docs.python.org/3/
