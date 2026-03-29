#!/bin/bash
# =============================================================================
# VirtualBox Alpine VM Setup (Matching vm-api working settings)
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
echo "     Alpine VM Setup (Matching vm-api settings)"
echo "============================================================================="

# Remove existing
if VBoxManage list vms | grep -q "\"$VM_NAME\""; then
    VBoxManage controlvm "$VM_NAME" poweroff 2>/dev/null || true
    sleep 2
    VBoxManage unregistervm "$VM_NAME" --delete || true
fi

# Create VM - matching vm-api settings
log_info "Creating VM with vm-api settings..."
VBoxManage createvm --name "$VM_NAME" --ostype "Linux_64" --register

# === MATCH vm-api EXACT SETTINGS ===
VBoxManage modifyvm "$VM_NAME" --memory 512           # Same as vm-api
VBoxManage modifyvm "$VM_NAME" --cpus 1               # Same as vm-api
VBoxManage modifyvm "$VM_NAME" --ioapic on            # Same as vm-api
VBoxManage modifyvm "$VM_NAME" --pae on               # Same as vm-api
VBoxManage modifyvm "$VM_NAME" --acpi on              # Same as vm-api
VBoxManage modifyvm "$VM_NAME" --chipset piix3        # Same as vm-api (KEY!)
VBoxManage modifyvm "$VM_NAME" --firmware bios        # Same as vm-api
VBoxManage modifyvm "$VM_NAME" --hpet on              # Same as vm-api
VBoxManage modifyvm "$VM_NAME" --graphicscontroller vmsvga  # Same as vm-api
VBoxManage modifyvm "$VM_NAME" --vram 16              # Same as vm-api
VBoxManage modifyvm "$VM_NAME" --nested-hw-virt off   # Same as vm-api
VBoxManage modifyvm "$VM_NAME" --nested-paging on     # Same as vm-api
VBoxManage modifyvm "$VM_NAME" --hwvirtex on          # Same as vm-api
VBoxManage modifyvm "$VM_NAME" --paravirtprovider kvm # Same as vm-api (KEY!)

# Network
VBoxManage modifyvm "$VM_NAME" --nic1 nat
VBoxManage modifyvm "$VM_NAME" --natpf1 "guestssh,tcp,,2222,,22"
VBoxManage modifyvm "$VM_NAME" --cableconnected1 on

# Boot
VBoxManage modifyvm "$VM_NAME" --boot1 dvd --boot2 disk

# Create disk
log_info "Creating disk..."
VBoxManage createmedium disk --filename "$VM_DIR/$VM_NAME.vdi" --size 8192

# === USE IDE CONTROLLER (like vm-api) ===
log_info "Attaching storage with IDE controller..."
VBoxManage storagectl "$VM_NAME" --name "IDE" --add ide --controller PIIX4

# Attach disk to IDE (not SATA!)
VBoxManage storageattach "$VM_NAME" --storagectl "IDE" --port 0 --device 0 --type hdd --medium "$VM_DIR/$VM_NAME.vdi"

# Attach ISO to IDE
VBoxManage storageattach "$VM_NAME" --storagectl "IDE" --port 0 --device 1 --type dvddrive --medium "$ISO_PATH"

log_info "VM created with vm-api compatible settings!"

echo ""
echo "============================================================================="
echo "  VM: $VM_NAME"
echo "  Settings: Matching vm-api (PIIX3 chipset, IDE, KVM paravirt)"
echo "  RAM: 512MB | CPU: 1 | Disk: 8GB"
echo "  SSH: port 2222"
echo "============================================================================="
echo "Start: VBoxManage startvm '$VM_NAME' --type gui"
echo "============================================================================="
