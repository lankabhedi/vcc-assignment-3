#!/bin/bash
# =============================================================================
# VirtualBox Alpine VM Setup (EXACT vm-api clone)
# Author: Samnit Mehandiratta (M25AI2087), IIT Jodhpur
# =============================================================================

set -e

VM_NAME="alpine-autoscale"
ISO_PATH="/home/samnitmehandiratta/Documents/VCC_Assignment_3/iso/alpine-standard-3.19.0-x86_64.iso"
VM_DIR="$HOME/VirtualBox VMs/$VM_NAME"

GREEN='\033[0;32m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }

echo "============================================================================="
echo "     Alpine VM Setup (EXACT vm-api clone)"
echo "============================================================================="

# Remove existing
if VBoxManage list vms | grep -q "\"$VM_NAME\""; then
    VBoxManage controlvm "$VM_NAME" poweroff 2>/dev/null || true
    sleep 2
    VBoxManage unregistervm "$VM_NAME" --delete || true
fi

# Create VM
log_info "Creating VM..."
VBoxManage createvm --name "$VM_NAME" --ostype "Linux_64" --register

# === EXACT vm-api SETTINGS ===
VBoxManage modifyvm "$VM_NAME" --memory 512
VBoxManage modifyvm "$VM_NAME" --cpus 1
VBoxManage modifyvm "$VM_NAME" --ioapic on
VBoxManage modifyvm "$VM_NAME" --pae on
VBoxManage modifyvm "$VM_NAME" --acpi on
VBoxManage modifyvm "$VM_NAME" --chipset piix3
VBoxManage modifyvm "$VM_NAME" --firmware bios
VBoxManage modifyvm "$VM_NAME" --hpet off           # vm-api has OFF
VBoxManage modifyvm "$VM_NAME" --graphicscontroller vmsvga
VBoxManage modifyvm "$VM_NAME" --vram 16
VBoxManage modifyvm "$VM_NAME" --nested-hw-virt off
VBoxManage modifyvm "$VM_NAME" --nested-paging on
VBoxManage modifyvm "$VM_NAME" --hwvirtex on
VBoxManage modifyvm "$VM_NAME" --paravirtprovider default  # vm-api uses DEFAULT

# Network
VBoxManage modifyvm "$VM_NAME" --nic1 nat
VBoxManage modifyvm "$VM_NAME" --natpf1 "guestssh,tcp,,2222,,22"
VBoxManage modifyvm "$VM_NAME" --cableconnected1 on

# Boot - disk first like vm-api
VBoxManage modifyvm "$VM_NAME" --boot1 disk --boot2 dvd --boot3 none

# Create disk
log_info "Creating disk..."
VBoxManage createmedium disk --filename "$VM_DIR/$VM_NAME.vdi" --size 8192

# === USE SATA CONTROLLER LIKE vm-api ===
log_info "Attaching storage with SATA controller (like vm-api)..."
VBoxManage storagectl "$VM_NAME" --name "SATA Controller" --add sata --controller IntelAhci

# Attach disk to SATA
VBoxManage storageattach "$VM_NAME" --storagectl "SATA Controller" --port 0 --device 0 --type hdd --medium "$VM_DIR/$VM_NAME.vdi"

# Attach ISO to SATA (vm-api style)
VBoxManage storageattach "$VM_NAME" --storagectl "SATA Controller" --port 1 --device 0 --type dvddrive --medium "$ISO_PATH"

log_info "VM created!"

echo ""
echo "============================================================================="
echo "  VM: $VM_NAME"
echo "  Settings: EXACT vm-api clone"
echo "  RAM: 512MB | CPU: 1 | Disk: 8GB"
echo "  SSH: port 2222"
echo "============================================================================="
echo "Start: VBoxManage startvm '$VM_NAME' --type gui"
echo "============================================================================="
