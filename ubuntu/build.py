import os
import shutil
import argparse
from build_kernel import build_kernel, reorganize_kernel_debs
from build_dtb import build_dtb
from build_vmlinuz import build_vmlinuz
from build_base_rootfs import build_base_rootfs
from build_deb import PackageBuilder
from constants import *
from datetime import date
from helpers import create_new_directory, mount_img, umount_dir, check_if_root, check_and_append_line_in_file, cleanup_file, logger, move_files_with_ext, cleanup_directory, change_folder_perm_read_write, print_build_logs, stop_local_apt_servers
from deb_organize import generate_manifest_map
from pack_deb import PackagePacker

def parse_arguments():
    parser = argparse.ArgumentParser(description="Process command line arguments.")

    parser.add_argument('--apt-server-config', type=str, required=False,
                        help='APT Server configuration to use')
    parser.add_argument('--mount_dir', type=str, required=False,
                        help='Mount directoryfor builds (default: <workspace>/build)')
    parser.add_argument('--workspace', type=str, required=True,
                        help='Workspace directory (mandatory)')
    parser.add_argument('--skip-starter-image', action='store_true', default=False,
                        help='Build starter image')
    parser.add_argument('--build-kernel', action='store_true', default=False,
                        help='Build kernel')
    parser.add_argument('--kernel-dir', type=str, required=False,
                        help='Kernel directory (default: <workspace>/kernel)')
    parser.add_argument('--flavor', type=str, choices=['server', 'desktop'], default='server',
                        help='Image flavor (only server or desktop, default: server)')
    parser.add_argument('--debians-path', type=str, required=False,
                        help='Directory with debians to install')
    parser.add_argument('--gen-debians', action='store_true', default=False,
                        help='Generate Debian binary (default: False)')
    parser.add_argument('--pack-image', action='store_true', default=False,
                        help='Pack system.img with generated debians (default: False)')
    parser.add_argument('--pack-variant', type=str, choices=['base', 'qcom'], default='qcom',
                        help='Pack variant (only base or qcom, default: qcom)')
    parser.add_argument('--output-image-file', type=str, required=False,
                        help='Path for output system.img (default: <workspace>/out/system.img)')
    parser.add_argument('--input-image-file', type=str, required=False,
                        help='Path for input system.img')
    parser.add_argument('--chroot-name', type=str, required=False,
                        help='chroot name to use')
    parser.add_argument('--package', type=str, required=False,
                        help='Package to build')
    parser.add_argument("--nocleanup", action="store_true",
                        help="Cleanup workspace after build", default=False)

    args = parser.parse_args()

    return args

args = parse_arguments()

WORKSPACE_DIR = args.workspace
IMAGE_TYPE = args.flavor
CHROOT_NAME = args.chroot_name if args.chroot_name else f"ubuntu-{date.today()}"

SKIP_STARTER_IMAGE = args.skip_starter_image
IN_SYSTEM_IMG = args.input_image_file
OUT_SYSTEM_IMG = args.output_image_file

BUILD_PACKAGE_NAME = args.package

DEBIAN_INSTALL_DIR = args.debians_path
IF_BUILD_KERNEL = args.build_kernel
CAN_GEN_DEBIANS = True
IF_GEN_DEBIANS = args.gen_debians
IF_PACK_IMAGE = args.pack_image
PACK_VARIANT = args.pack_variant
IS_CLEANUP_ENABLED = not args.nocleanup

MOUNT_DIR = args.mount_dir if args.mount_dir else os.path.join(WORKSPACE_DIR, "build")
MOUNT_DIR = os.path.join(MOUNT_DIR, CHROOT_NAME)

KERNEL_DIR = args.kernel_dir if args.kernel_dir else os.path.join(WORKSPACE_DIR, "kernel")
SOURCES_DIR = os.path.join(WORKSPACE_DIR, "sources")
OUT_DIR = os.path.join(WORKSPACE_DIR, "out")
DEB_OUT_DIR = os.path.join(WORKSPACE_DIR, "debian_packages")

OSS_DEB_OUT_DIR = os.path.join(DEB_OUT_DIR, "oss")
PROP_DEB_OUT_DIR = os.path.join(DEB_OUT_DIR, "prop")
TEMP_DIR = os.path.join(DEB_OUT_DIR, "temp")

if not check_if_root():
    logger.error('Please run this script as root user.')
    exit(1)

create_new_directory(WORKSPACE_DIR, delete_if_exists=False)
create_new_directory(MOUNT_DIR, delete_if_exists=False)
create_new_directory(KERNEL_DIR, delete_if_exists=False)
create_new_directory(SOURCES_DIR, delete_if_exists=False)
create_new_directory(OUT_DIR, delete_if_exists=False)
create_new_directory(DEB_OUT_DIR, delete_if_exists=False)
create_new_directory(OSS_DEB_OUT_DIR, delete_if_exists=False)
create_new_directory(PROP_DEB_OUT_DIR, delete_if_exists=False)
create_new_directory(TEMP_DIR, delete_if_exists=True)

APT_SERVER_CONFIG = args.apt_server_config.strip() if args.apt_server_config else None

MANIFEST_MAP = generate_manifest_map(WORKSPACE_DIR)

ERROR_EXIT_BUILD = False

if IN_SYSTEM_IMG is None and not SKIP_STARTER_IMAGE:
    try:
        if IF_BUILD_KERNEL:
            os.chdir(WORKSPACE_DIR)
            build_kernel(KERNEL_DIR)
            reorganize_kernel_debs(WORKSPACE_DIR, OSS_DEB_OUT_DIR)

        build_dtb(OSS_DEB_OUT_DIR, LINUX_MODULES_DEB, COMBINED_DTB_FILE, OUT_DIR)

        build_vmlinuz(OSS_DEB_OUT_DIR, LINUX_IMAGE_UNSIGNED_DEB, VMLINUX_QCOM_FILE, OUT_DIR)

        build_base_rootfs(IMAGE_STARTER_NAME, VMLINUX_QCOM_FILE, OUT_DIR, BOOT_PART_SIZE_IN_M, ROOT_PART_SIZE, IMAGE_SIZE_IN_G, GRUB_CFG_PATH, MOUNT_DIR, TEMP_DIR=TEMP_DIR)
    except Exception as e:
        logger.error(e)
        ERROR_EXIT_BUILD = True

    SYSTEM_IMAGE = os.path.join(OUT_DIR, IMAGE_STARTER_NAME)
elif IN_SYSTEM_IMG is not None:
    SYSTEM_IMAGE = IN_SYSTEM_IMG
else:
    CAN_GEN_DEBIANS = False

if ERROR_EXIT_BUILD:
    exit(1)

if IF_GEN_DEBIANS:
    if not CAN_GEN_DEBIANS:
        logger.error("Debian generation is not possible. Please provide a starting system.img.")
        exit(1)

    builder = None

    try:
        mount_img(SYSTEM_IMAGE, MOUNT_DIR)
        builder = PackageBuilder(MOUNT_DIR, SOURCES_DIR, DEB_OUT_DIR, APT_SERVER_CONFIG, CHROOT_NAME, MANIFEST_MAP, TEMP_DIR)
        builder.load_packages()
        if BUILD_PACKAGE_NAME:
            # TODO: Check if package is available
            can_build = builder.build_specific_package(BUILD_PACKAGE_NAME)
            if not can_build:
                exit(1)
        else:
            builder.build_all_packages()

    except Exception as e:
        logger.error(e)
        print_build_logs(TEMP_DIR)
        ERROR_EXIT_BUILD = True

    finally:
        if IS_CLEANUP_ENABLED:
            umount_dir(MOUNT_DIR)
            cleanup_file(f"/etc/schroot/chroot.d/{CHROOT_NAME}.conf")
        if ERROR_EXIT_BUILD:
            exit(1)

if OUT_SYSTEM_IMG is None:
    OUT_SYSTEM_IMG = os.path.join(OUT_DIR, IMAGE_NAME)

if IF_PACK_IMAGE:
    packer = None
    cleanup_file(OUT_SYSTEM_IMG)
    create_new_directory(MOUNT_DIR)
    try:
        packer = PackagePacker(MOUNT_DIR, IMAGE_TYPE, PACK_VARIANT, DEBIAN_INSTALL_DIR, OUT_DIR, OUT_SYSTEM_IMG, APT_SERVER_CONFIG, TEMP_DIR)

        packer.build_image()
    except Exception as e:
        logger.error(e)
        print_build_logs(TEMP_DIR)
        ERROR_EXIT_BUILD = True

    finally:
        stop_local_apt_servers()
        if IS_CLEANUP_ENABLED:
            umount_dir(MOUNT_DIR, UMOUNT_HOST_FS=True)
            cleanup_directory(MOUNT_DIR)
        if ERROR_EXIT_BUILD:
            exit(1)

if IS_CLEANUP_ENABLED:
    try:
        change_folder_perm_read_write(OSS_DEB_OUT_DIR)
        change_folder_perm_read_write(PROP_DEB_OUT_DIR)
        change_folder_perm_read_write(DEB_OUT_DIR)
        change_folder_perm_read_write(OUT_DIR)
    except Exception:
        ERROR_EXIT_BUILD = True

if ERROR_EXIT_BUILD:
    exit(1)
