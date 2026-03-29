#!/bin/bash
# =============================================================================
# VirtualBox Alpine Linux VM Setup Script (Simple BIOS Mode)
# Assignment 3: VCC - Auto-scaling Local VM to Cloud
# Author: Samnit Mehandiratta (M25AI2087), IIT Jodhpur
# =============================================================================

set -e

VM_NAME="alpine-autoscale"
ISO_PATH="/home/samnitmehandiratta/Documents/VCC_Assignment_3/iso/alpine-standard-3.19.0-x86_64.iso"
VM_DIR="$HOME/VirtualBox VMs/$VM_NAME"
RAM_SIZE=1024
DISK_SIZE=8192
CPU_COUNT=1

GREEN='\033[0;32m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }

echo "============================================================================="
echo "     Alpine Linux VM Setup (Simple Mode)"
echo "     Author: Samnit Mehandiratta (M25AI2087), IIT Jodhpur"
echo "============================================================================="

# Remove existing VM
if VBoxManage list vms | grep -q "\"$VM_NAME\""; then
    log_info "Removing existing VM..."
    VBoxManage controlvm "$VM_NAME" poweroff 2>/dev/null || true
    sleep 2
    VBoxManage unregistervm "$VM_NAME" --delete || true
fi

# Create VM
log_info "Creating VM..."
VBoxManage createvm --name "$VM_NAME" --ostype "Linux_64" --register

# Basic settings - minimal configuration
VBoxManage modifyvm "$VM_NAME" --memory $RAM_SIZE
VBoxManage modifyvm "$VM_NAME" --cpus $CPU_COUNT
VBoxManage modifyvm "$VM_NAME" --ioapic off
VBoxManage modifyvm "$VM_NAME" --pae on
VBoxManage modifyvm "$VM_NAME" --acpi on

# Network
VBoxManage modifyvm "$VM_NAME" --nic1 nat
VBoxManage modifyvm "$VM_NAME" --natpf1 "guestssh,tcp,,2222,,22"
VBoxManage modifyvm "$VM_NAME" --cableconnected1 on

# Graphics - simple VGA
VBoxManage modifyvm "$VM_NAME" --graphicscontroller vga
VBoxManage modifyvm "$VM_NAME" --vram 16

# Boot
VBoxManage modifyvm "$VM_NAME" --boot1 dvd --boot2 disk

# Create disk
log_info "Creating disk..."
VBoxManage createmedium disk --filename "$VM_DIR/$VM_NAME.vdi" --size $DISK_SIZE

# Attach storage
VBoxManage storagectl "$VM_NAME" --name "IDE" --add ide
VBoxManage storageattach "$VM_NAME" --storagectl "IDE" --port 0 --device 0 --type hdd --medium "$VM_DIR/$VM_NAME.vdi"
VBoxManage storageattach "$VM_NAME" --storagectl "IDE" --port 0 --device 1 --type dvddrive --medium "$ISO_PATH"

log_info "VM created!"

echo ""
echo "============================================================================="
echo "  VM: $VM_NAME"
echo "  RAM: ${RAM_SIZE}MB | CPU: $CPU_COUNT | Disk: ${DISK_SIZE}MB"
echo "  SSH: port 2222"
echo "============================================================================="
echo "Start: VBoxManage startvm '$VM_NAME' --type gui"
echo "============================================================================="
