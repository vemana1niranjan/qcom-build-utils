import os

LINUX_IMAGE_UNSIGNED_DEB = "linux-image-unsigned-*-qcom/linux-image-unsigned-*_arm64.deb"
LINUX_MODULES_DEB = "linux-modules-*-qcom/linux-modules-*_arm64.deb"

KERNEL_DEBS = [
    "linux-modules",
    "linux-tools",
    "linux-buildinfo",
    "linux-qcom-tools",
    "linux-headers",
    "linux-image-unsigned",
    "linux-libc-dev-qcom",
    "linux-source",
    "linux-qcom-headers",
    "linux-qcom-tools"
]

COMBINED_DTB_FILE  = "combined-dtb.dtb"
VMLINUX_QCOM_FILE  = "vmlinuz-qcom"
IMAGE_NAME         = "system.img"

BOOT_PART_SIZE_IN_M = 512
ROOT_PART_SIZE      = 100
IMAGE_SIZE_IN_G     = 8

GRUB_CFG_PATH = f"{os.path.dirname(os.path.abspath(__file__))}/files/grub.cfg"
SCHROOT_CFG_PATH = f"{os.path.dirname(os.path.abspath(__file__))}/files/schroot.conf.template"

TERMINAL = "/bin/bash"

HOST_FS_MOUNT = ["dev", "proc", "sys", "run"]
