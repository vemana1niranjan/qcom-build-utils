WORKSPACE=$(pwd)
OUT_DIR="${WORKSPACE}/out"
mkdir -p "${OUT_DIR}/modules" "${OUT_DIR}/kernel"
git clone git@github.com:qualcomm-linux/kernel.git --single-branch -b qcom-next-6.19-rc8-20260210 --depth=1 $WORKSPACE/kernel-qcom
cd "${WORKSPACE}/kernel-qcom"
make ARCH=arm64 defconfig qcom.config
cp .config "${OUT_DIR}"
make ARCH=arm64 -j$(nproc)
make ARCH=arm64 modules
cp arch/arm64/boot/Image "${OUT_DIR}"
make ARCH=arm64 modules_install INSTALL_MOD_PATH="${OUT_DIR}/modules" INSTALL_MOD_STRIP=1
find arch/arm64/boot/dts -type f -name 'glymur-crd.dtb' -exec cp "{}" "${OUT_DIR}/" \;
BASE_KERNEL_VERSION=$(basename "$OUT_DIR"/modules/lib/modules/* 2>/dev/null)
PKG_KERNEL_VERSION="$BASE_KERNEL_VERSION"
DEB_DIR="linux-kernel-$PKG_KERNEL_VERSION-arm64"
DEB_PACKAGE="$DEB_DIR.deb"
IMAGE="$OUT_DIR/Image"
CONFIG="$OUT_DIR/.config"
MODULES="$OUT_DIR/modules/lib/modules/$BASE_KERNEL_VERSION"
DTB_GLOB="$OUT_DIR/*.dtb"
mkdir -p "$DEB_DIR/DEBIAN"
mkdir -p "$DEB_DIR/boot"
mkdir -p "$DEB_DIR/lib/firmware/$BASE_KERNEL_VERSION/device-tree"
mkdir -p "$DEB_DIR/lib/modules/$BASE_KERNEL_VERSION"
chmod 0755 "$DEB_DIR/DEBIAN"
chmod -R g-s "$DEB_DIR/DEBIAN"
cp "$IMAGE" "$DEB_DIR/boot/vmlinuz-$BASE_KERNEL_VERSION"
cp "$CONFIG" "$DEB_DIR/boot/config-$BASE_KERNEL_VERSION"
cp -rap "$MODULES" "$DEB_DIR/lib/modules/"
cp "$OUT_DIR"/*.dtb "$DEB_DIR/lib/firmware/$BASE_KERNEL_VERSION/device-tree/"
cat > "$DEB_DIR/DEBIAN/control" <<EOF
Package: linux-kernel-$PKG_KERNEL_VERSION
Version: $PKG_KERNEL_VERSION
Architecture: arm64
Section: kernel
Priority: optional
Description: Linux kernel Image, dtb and modules for $BASE_KERNEL_VERSION
EOF
cat > "$DEB_DIR/DEBIAN/preinst" <<EOF
#!/bin/sh
set -e
kernel_version=$BASE_KERNEL_VERSION
# Remove old kernel files (cleanup)
rm -f /boot/config-\$kernel_version
rm -f /boot/vmlinuz-\$kernel_version
rm -f /boot/initrd.img-\$kernel_version
rm -rf /lib/modules/\$kernel_version
rm -rf /lib/firmware/\$kernel_version
exit 0
EOF
chmod 0755 "$DEB_DIR/DEBIAN/preinst"
cat > "$DEB_DIR/DEBIAN/postinst" <<EOF
#!/bin/sh
set -e
kernel_version=$BASE_KERNEL_VERSION
update-initramfs -k \$kernel_version -c || true
update-grub || true
echo "Kernel \$kernel_version installed."
exit 0
EOF
chmod 0755 "$DEB_DIR/DEBIAN/postinst"
cat > "$DEB_DIR/DEBIAN/postrm" <<EOF
#!/bin/sh
set -e
update-grub || true
exit 0
EOF
chmod 0755 "$DEB_DIR/DEBIAN/postrm"
dpkg-deb --build "$DEB_DIR"
rm -rf "$DEB_DIR"