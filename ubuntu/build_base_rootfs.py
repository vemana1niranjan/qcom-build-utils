import os
import shutil
from helpers import run_command, logger, create_new_directory, check_if_root, umount_dir, check_and_append_line_in_file, cleanup_file
from constants import TERMINAL, HOST_FS_MOUNT

def create_disk_image(IMAGE_NAME: str, BOOT_PART_SIZE_IN_M: int, ROOT_PART_SIZE: int, IMAGE_SIZE_IN_G: int):
    logger.info("Create disk image")
    sector_count = IMAGE_SIZE_IN_G * 1024
    run_command(f"dd if=/dev/zero of={IMAGE_NAME} bs=1M count=$(({sector_count}))")

    logger.info("Create partitions")
    run_command(f"parted {IMAGE_NAME} mklabel gpt")
    run_command(f"parted {IMAGE_NAME} mkpart ESP fat32 1MiB {BOOT_PART_SIZE_IN_M}MiB")
    run_command(f"parted {IMAGE_NAME} set 1 boot on")
    run_command(f"parted {IMAGE_NAME} mkpart root ext4 {BOOT_PART_SIZE_IN_M}MiB {ROOT_PART_SIZE}%")

def setup_loop_device(IMAGE_NAME: str):
    logger.info("Set loop device")

    loop_dev = run_command(f"losetup --find --show --partscan {IMAGE_NAME}")

    run_command(f"mkfs.vfat -F 32 -I {loop_dev}p1")
    run_command(f"mkfs.ext4 -F {loop_dev}p2")

    return loop_dev

def bootstrap_ubuntu(MOUNT_DIR: str, loop_dev):
    create_new_directory(MOUNT_DIR, delete_if_exists=False)

    run_command(f"mount {loop_dev}p2 {MOUNT_DIR}")

    run_command(f"debootstrap --arch=arm64 noble {MOUNT_DIR} http://ports.ubuntu.com/ubuntu-ports/")

    # Mount filesystem
    for direc in HOST_FS_MOUNT:
        run_command(f"mount --bind /{direc} {MOUNT_DIR}/{direc}")

def chroot_setup(MOUNT_DIR: str):
    logger.info("Setup chroot")

    run_command(f"chroot {MOUNT_DIR} {TERMINAL} -c 'apt update && apt install -y grub-efi-arm64 linux-image-generic initramfs-tools'")
    run_command(f"chroot {MOUNT_DIR} {TERMINAL} -c 'echo root:password | chpasswd'")
    check_and_append_line_in_file(f"{MOUNT_DIR}/etc/apt/sources.list", "deb http://ports.ubuntu.com/ubuntu-ports noble main universe multiverse restricted", True)

def chroot_ssl_setup(MOUNT_DIR: str):
    run_command(f"chroot {MOUNT_DIR} {TERMINAL} -c 'apt install -y wget'")
    run_command(f"chroot {MOUNT_DIR} {TERMINAL} -c 'wget http://pki.qualcomm.com/ssl_v4_cert.crt -O /usr/local/share/ca-certificates/ssl_v4_cert.crt && wget http://pki.qualcomm.com/ssl_v2_cert.crt -O /usr/local/share/ca-certificates/ssl_v2_cert.crt && wget http://pki.qualcomm.com/qc_root_g2_cert.crt -O /usr/local/share/ca-certificates/qc_root_g2_cert.crt && /usr/sbin/update-ca-certificates'")
    run_command(f"chroot {MOUNT_DIR} {TERMINAL} -c 'apt update'")

def install_grub(MOUNT_DIR, loop_dev):
    logger.info("Install grub")

    create_new_directory(f"{MOUNT_DIR}/boot/efi")
    run_command(f"mount {loop_dev}p1 {MOUNT_DIR}/boot/efi")
    run_command(f"chroot {MOUNT_DIR} {TERMINAL} -c 'grub-install --target=arm64-efi --efi-directory=/boot/efi --bootloader-id=ubuntu'")
    run_command(f"chroot {MOUNT_DIR} {TERMINAL} -c 'update-grub'")

def install_vmlinux(MOUNT_DIR, VMLINUZ_FILENAME, GRUB_CFG_PATH, OUT_DIR) -> bool:
    vmlinuz_path = os.path.join(OUT_DIR, VMLINUZ_FILENAME)
    if not os.path.exists(vmlinuz_path):
        logger.error(f"{vmlinuz_path} does not exist.")
        return False
    
    if not os.path.exists(GRUB_CFG_PATH):
        logger.error(f"{GRUB_CFG_PATH} does not exist.")
        return False

    run_command(f"touch {MOUNT_DIR}/boot/{VMLINUZ_FILENAME}")

    shutil.copy(vmlinuz_path, f"{MOUNT_DIR}/boot/{VMLINUZ_FILENAME}")
    shutil.copy(GRUB_CFG_PATH, f"{MOUNT_DIR}/boot/grub/grub.cfg")
    return True

def is_vmlinux_installed(MOUNT_DIR, VMLINUZ_FILENAME):
    vmlinuz_path = os.path.join(MOUNT_DIR, "boot", VMLINUZ_FILENAME)
    return os.path.exists(vmlinuz_path)

def generate_final_img(loop_dev, IMAGE_NAME, OUT_DIR):
    run_command(f"dd if={loop_dev}p1 of={OUT_DIR}/efi.bin bs=4M status=progress")
    run_command(f"dd if={loop_dev}p2 of={OUT_DIR}/{IMAGE_NAME} bs=4M status=progress")

def cleanup(MOUNT_DIR, IMAGE_NAME, loop_dev):
    umount_dir(f"{MOUNT_DIR}/boot/efi")
    umount_dir(f"{MOUNT_DIR}", UMOUNT_HOST_FS=True)
    run_command(f"losetup -d {loop_dev}")
    if IMAGE_NAME:
        cleanup_file(IMAGE_NAME)

def build_base_rootfs(IMAGE_NAME: str, VMLINUZ_FILENAME: str, OUT_DIR: str, BOOT_PART_SIZE_IN_M: int, ROOT_PART_SIZE: int, IMAGE_SIZE_IN_G: int, GRUB_CFG_PATH, MOUNT_DIR="/mnt/sysroot", GEN_FINAL_IMAGE=True, CLEAN_LOOP_DEV=True):
    if not check_if_root():
        logger.error('Please run this script as root user.')
        exit(1)

    create_disk_image(IMAGE_NAME, BOOT_PART_SIZE_IN_M, ROOT_PART_SIZE, IMAGE_SIZE_IN_G)
    loop_dev = setup_loop_device(IMAGE_NAME)
    bootstrap_ubuntu(MOUNT_DIR, loop_dev)
    chroot_setup(MOUNT_DIR)
    chroot_ssl_setup(MOUNT_DIR)
    install_grub(MOUNT_DIR, loop_dev)
    install_vmlinux(MOUNT_DIR, VMLINUZ_FILENAME, GRUB_CFG_PATH, OUT_DIR)

    if GEN_FINAL_IMAGE and is_vmlinux_installed(MOUNT_DIR, VMLINUZ_FILENAME):
        generate_final_img(loop_dev, IMAGE_NAME, OUT_DIR)
    else:
        logger.error(f"vmlinuz not installed in {MOUNT_DIR}")
        exit(1)
    if CLEAN_LOOP_DEV:
        cleanup(MOUNT_DIR, IMAGE_NAME, loop_dev)
    return loop_dev
