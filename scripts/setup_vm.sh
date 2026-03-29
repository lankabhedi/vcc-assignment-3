#!/bin/bash
# =============================================================================
# VirtualBox Alpine Linux VM Setup Script (Fixed Version)
# Assignment 3: VCC - Auto-scaling Local VM to Cloud
# Author: Samnit Mehandiratta (M25AI2087), IIT Jodhpur
# =============================================================================

set -e

# Configuration
VM_NAME="alpine-autoscale"
ISO_PATH="/home/samnitmehandiratta/Documents/VCC_Assignment_3/iso/alpine-standard-3.19.0-x86_64.iso"
VM_DIR="$HOME/VirtualBox VMs/$VM_NAME"
RAM_SIZE=2048        # 2GB RAM (more stable)
DISK_SIZE=8192       # 8GB disk
CPU_COUNT=2

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo "============================================================================="
echo "     Alpine Linux VM Setup for Auto-scaling Assignment"
echo "     Author: Samnit Mehandiratta (M25AI2087), IIT Jodhpur"
echo "============================================================================="

# Check if VM already exists
if VBoxManage list vms | grep -q "\"$VM_NAME\""; then
    log_warn "VM '$VM_NAME' already exists. Removing it..."
    VBoxManage unregistervm "$VM_NAME" --delete || true
fi

# Create VM with BIOS mode (more compatible)
log_info "Creating VM '$VM_NAME'..."
VBoxManage createvm --name "$VM_NAME" --ostype "Linux26_64" --register

# System settings - disable problematic features
VBoxManage modifyvm "$VM_NAME" --memory $RAM_SIZE
VBoxManage modifyvm "$VM_NAME" --cpus $CPU_COUNT
VBoxManage modifyvm "$VM_NAME" --ioapic on
VBoxManage modifyvm "$VM_NAME" --pae on

# Disable features that can cause crashes
VBoxManage modifyvm "$VM_NAME" --nested-hw-virt off
VBoxManage modifyvm "$VM_NAME" --hwvirtex on
VBoxManage modifyvm "$VM_NAME" --nested-paging on

# Network settings (NAT for internet access)
VBoxManage modifyvm "$VM_NAME" --nic1 nat
VBoxManage modifyvm "$VM_NAME" --natpf1 "guestssh,tcp,,2222,,22"
VBoxManage modifyvm "$VM_NAME" --cableconnected1 on

# Graphics settings
VBoxManage modifyvm "$VM_NAME" --graphicscontroller vmsvga
VBoxManage modifyvm "$VM_NAME" --vram 128
VBoxManage modifyvm "$VM_NAME" --accelerate3d off

# Boot order
VBoxManage modifyvm "$VM_NAME" --boot1 dvd --boot2 disk --boot3 none

log_info "Creating virtual hard disk..."

# Create VDI disk
VBoxManage createmedium disk --filename "$VM_DIR/$VM_NAME.vdi" --size $DISK_SIZE --format VDI

# Create SATA controller and attach disk
VBoxManage storagectl "$VM_NAME" --name "SATA Controller" --add sata --controller IntelAhci
VBoxManage storageattach "$VM_NAME" --storagectl "SATA Controller" --port 0 --device 0 --type hdd --medium "$VM_DIR/$VM_NAME.vdi"

# Create IDE controller and attach ISO
VBoxManage storagectl "$VM_NAME" --name "IDE Controller" --add ide --controller PIIX4
VBoxManage storageattach "$VM_NAME" --storagectl "IDE Controller" --port 0 --device 0 --type dvddrive --medium "$ISO_PATH"

log_info "VM created successfully!"

echo ""
echo "============================================================================="
echo "                    VM Setup Complete!"
echo "============================================================================="
echo "  VM Name:        $VM_NAME"
echo "  OS Type:        Alpine Linux 64-bit"
echo "  RAM:            ${RAM_SIZE}MB"
echo "  CPUs:           $CPU_COUNT"
echo "  Disk Size:      ${DISK_SIZE}MB"
echo "  SSH Port:       2222 (forwarded to guest:22)"
echo "  ISO Path:       $ISO_PATH"
echo "============================================================================="
echo ""
echo "Next Steps:"
echo "  1. Start the VM: VBoxManage startvm '$VM_NAME' --type gui"
echo "  2. Login as: root (no password)"
echo "  3. Install: setup-disk -> sda -> sys"
echo "  4. Network: setup-interfaces"
echo "  5. Packages: apk add python3 py3-pip openssh bash"
echo "  6. SSH: rc-update add sshd && rc-service sshd start && passwd"
echo "============================================================================="
