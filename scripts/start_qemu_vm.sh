#!/bin/bash
# QEMU Alpine VM - Fixed display settings
ISO_PATH="/home/samnitmehandiratta/Documents/VCC_Assignment_3/iso/alpine-standard-3.19.0-x86_64.iso"
VM_DIR="$HOME/qemu_vms/alpine-autoscale"
DISK_PATH="$VM_DIR/alpine-autoscale.qcow2"

mkdir -p "$VM_DIR"

if [ ! -f "$DISK_PATH" ]; then
    qemu-img create -f qcow2 "$DISK_PATH" 8G
fi

qemu-system-x86_64 -enable-kvm \
  -name "alpine-autoscale" \
  -m 2048 \
  -smp 2 \
  -hda "$DISK_PATH" \
  -cdrom "$ISO_PATH" \
  -boot d \
  -netdev user,id=net0,hostfwd=tcp::2222-:22 \
  -device virtio-net-pci,netdev=net0 \
  -display sdl,gl=off \
  -vga std \
  -cpu host \
  -no-shutdown
