#!/bin/bash
# =============================================================================
# QEMU/KVM Alpine Linux VM Setup Script
# Assignment 3: VCC - Auto-scaling Local VM to Cloud
# Author: Samnit Mehandiratta (M25AI2087), IIT Jodhpur
# =============================================================================

set -e

VM_NAME="alpine-autoscale"
ISO_PATH="/home/samnitmehandiratta/Documents/VCC_Assignment_3/iso/alpine-standard-3.19.0-x86_64.iso"
VM_DIR="$HOME/qemu_vms/$VM_NAME"
DISK_PATH="$VM_DIR/alpine-autoscale.qcow2"
RAM_SIZE=2048
CPUS=2
DISK_SIZE=8G

# Colors
GREEN='\033[0;32m'
NC='\033[0m'

echo "============================================================================="
echo "     QEMU/KVM Alpine Linux VM Setup"
echo "     Author: Samnit Mehandiratta (M25AI2087), IIT Jodhpur"
echo "============================================================================="

# Create VM directory
mkdir -p "$VM_DIR"

# Create disk image
echo "[INFO] Creating disk image ($DISK_SIZE)..."
qemu-img create -f qcow2 "$DISK_PATH" "$DISK_SIZE"

echo ""
echo "============================================================================="
echo "                    VM Setup Complete!"
echo "============================================================================="
echo "  VM Name:        $VM_NAME"
echo "  RAM:            ${RAM_SIZE}MB"
echo "  CPUs:           $CPUS"
echo "  Disk Size:      $DISK_SIZE"
echo "  ISO Path:       $ISO_PATH"
echo "  Disk Path:      $DISK_PATH"
echo "============================================================================="
echo ""
echo "Start the VM with:"
echo "  $HOME/qemu_vms/start_vm.sh"
echo ""
echo "Or run directly:"
echo "  qemu-system-x86_64 -enable-kvm -m $RAM_SIZE -smp $CPUS \\"
echo "    -hda $DISK_PATH -cdrom $ISO_PATH -boot d \\"
echo "    -netdev user,id=net0,hostfwd=tcp::2222-:22 -device virtio-net-pci,netdev=net0"
echo "============================================================================="

# Create startup script
cat > "$VM_DIR/start_vm.sh" << 'EOF'
#!/bin/bash
VM_NAME="alpine-autoscale"
ISO_PATH="/home/samnitmehandiratta/Documents/VCC_Assignment_3/iso/alpine-standard-3.19.0-x86_64.iso"
VM_DIR="$HOME/qemu_vms/$VM_NAME"
DISK_PATH="$VM_DIR/alpine-autoscale.qcow2"

qemu-system-x86_64 -enable-kvm \
  -name "$VM_NAME" \
  -m 2048 \
  -smp 2 \
  -hda "$DISK_PATH" \
  -cdrom "$ISO_PATH" \
  -boot d \
  -netdev user,id=net0,hostfwd=tcp::2222-:22 \
  -device virtio-net-pci,netdev=net0 \
  -display gtk,gl=off \
  -vga qxl
EOF

chmod +x "$VM_DIR/start_vm.sh"

echo "[INFO] Startup script created: $VM_DIR/start_vm.sh"
