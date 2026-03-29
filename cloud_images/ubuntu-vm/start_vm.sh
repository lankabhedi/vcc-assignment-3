#!/bin/bash
# Ubuntu Cloud Image VM - No installation needed!
cd /home/samnitmehandiratta/Documents/VCC_Assignment_3/cloud_images/ubuntu-vm

echo "============================================================================="
echo "     Starting Ubuntu Cloud VM (QEMU/KVM)"
echo "============================================================================="
echo ""
echo "Default login: root / alpine"
echo "SSH: ssh -p 2222 root@localhost"
echo "============================================================================="

qemu-system-x86_64 -enable-kvm \
  -name "ubuntu-autoscale" \
  -m 2048 \
  -smp 2 \
  -hda ubuntu-vm.qcow2 \
  -drive file=fat:rw:.,format=raw,media=cdrom,label=cidata \
  -netdev user,id=net0,hostfwd=tcp::2222-:22 \
  -device virtio-net-pci,netdev=net0 \
  -display sdl,gl=off \
  -vga std \
  -cpu host \
  -no-shutdown
