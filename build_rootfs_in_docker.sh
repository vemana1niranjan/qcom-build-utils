echo "Debian Rootfs Creation
This section creates a bootable Ubuntu/Debian root filesystem image using the kernel artifacts generated above."
mkdir $WORKSPACE/rootfs
ROOTFS="$WORKSPACE/rootfs"
cd $ROOTFS
ROOTFS_IMG="$ROOTFS/rootfs.img"
MNT_DIR="$WORKSPACE/mnt"
KVER=$(ls "${OUT_DIR}/modules/lib/modules/" | head -n 1)
echo "Building Rootfs for Kernel Version: ${KVER}"
sudo mkdir -p "${MNT_DIR}"
sudo debootstrap --arch="arm64" --variant=minbase --components="main,universe" --include="tar,xz-utils,initramfs-tools,lsb-release,ca-certificates,sudo,adduser,passwd,systemd-sysv,apt" "trixie" "$ROOTFS" "http://ftp.debian.org/debian"
sudo cp -L /etc/resolv.conf ./etc/resolv.conf
echo "qcom" | sudo tee "./etc/hostname" > /dev/null
sudo tee "./etc/hosts" > /dev/null <<EOF
127.0.0.1   localhost
127.0.1.1   qcom
EOF
echo "[INFO] Binding system directories..."
sudo mount -o bind /proc "./proc"
sudo mount -o bind /sys "./sys"
sudo mount -o bind /dev "./dev"
sudo mount --bind /dev/pts "./dev/pts"
#env DISTRO="ubuntu" CODENAME="trixie" VARIANT="minbase" -->skipping
sudo cp -r $WORKSPACE/kernel-qcom/*.deb $ROOTFS/.
sudo chroot . /bin/bash -c '
    set -e
    apt-get update
    apt-get install -y initramfs-tools
    deb=$(ls /linux-kernel-*-arm64.deb | head -n1)
    [ -n "$deb" ] || { echo "Missing /linux-kernel-*-arm64.deb"; exit 1; }
    dpkg -i "$deb" || apt-get -f install -y
    kver=$(basename "$deb" | sed "s/^linux-kernel-//; s/-arm64\.deb$//")
    update-initramfs -c -k "$kver"
    cat >/boot/grub.cfg <<EOF
    set timeout=5
        menuentry "debian trixie" {
            search --no-floppy --label system --set=root
            devicetree /lib/firmware/$kver/device-tree/glymur-crd.dtb
            linux /boot/vmlinuz-$kver earlycon console=ttyMSM0,115200n8 root=LABEL=system cma=128M rw cpuidle.off=1 clk_ignore_unused pd_ignore_unused efi=noruntime rootwait ignore_loglevel
            initrd /boot/initrd.img-$kver
        }
EOF
'
sudo umount -lf ./dev/pts || true
sudo umount -lf ./dev     || true
sudo umount -lf ./proc    || true
sudo umount -lf ./sys     || true
ROOTFS="$WORKSPACE/rootfs"
ROOTFS_IMG="rootfs.img"
mkdir -p "$WORKSPACE/mnt"
MNT_DIR="$WORKSPACE/mnt"
truncate -s 8G "$ROOTFS_IMG"
mkfs.ext4 -L system "$ROOTFS_IMG"
echo "[INFO] Copying rootfs contents into image..."
sudo mount -o loop "$ROOTFS_IMG" "$MNT_DIR" 
sudo cp -rap "$ROOTFS/"* "$MNT_DIR/"
echo "[INFO] Writing static /etc/resolv.conf for runtime DNS resolution..."
#sudo rm -f "$MNT_DIR/etc/resolv.conf"
#sudo echo -e 'nameserver 1.1.1.1\nnameserver 8.8.8.8' > "$MNT_DIR/etc/resolv.conf"
sudo umount -l "$MNT_DIR"