import os
import shutil
import subprocess
import threading
import argparse
import importlib.util
import re
from pathlib import Path
from queue import Queue
from collections import defaultdict, deque
from constants import *
from helpers import check_if_root, logger, run_command, create_new_directory, run_command_for_result
from build_base_rootfs import build_base_rootfs
from deb_organize import search_manifest_map_for_path

class PackagePacker:
    def __init__(self, MOUNT_DIR):
        if not check_if_root():
            logger.error('Please run this script as root user.')
            exit(1)
        self.MOUNT_DIR = Path(MOUNT_DIR)

    def copy_debs_to_chroot(self, src_path):
        source_dir = Path(f"{src_path}")
        dest_dir   = Path(f"{self.MOUNT_DIR}/tmp/debs")

        if not source_dir.exists():
            logger.error(f"Source directory {src_path} does not exist. Skipping.")
            return

        if not dest_dir.exists():
            create_new_directory(f"{self.MOUNT_DIR}/tmp", delete_if_exists=False)
            create_new_directory(f"{dest_dir}", delete_if_exists=False)

        for deb_file in Path(f"{src_path}").rglob("*.deb"):
            is_kernel_deb = False
            file_name = deb_file.name
            for kernel_deb_name in KERNEL_DEBS:
                if str(file_name).startswith(kernel_deb_name) and str(file_name).endswith(".deb"):
                    logger.warning(f"{file_name} is a kernel deb. Ignoring.")
                    is_kernel_deb = True
                    break

            if not is_kernel_deb:
                shutil.copy(deb_file, dest_dir)

    def install_debs(self):
        logger.info("Installing debian packages")

        try:
            run_command(f"chroot {self.MOUNT_DIR} {TERMINAL} -c 'cd /tmp/debs && dpkg -i *.deb'")
        except:
            logger.error(f"Installation failed. Will try once more.")
        logger.info("Trigger install for the second time as a failsafe mechanism.")
        run_command(f"chroot {self.MOUNT_DIR} {TERMINAL} -c 'apt-get install -f -y -qq'")
        run_command(f"chroot {self.MOUNT_DIR} {TERMINAL} -c 'cd /tmp/debs && dpkg -i *.deb'")
        res = run_command_for_result(f"chroot {self.MOUNT_DIR} {TERMINAL} -c 'apt-get install -f -y -qq'")
        if res['returncode'] > 0:
            logger.error(res['output'])
            logger.error("Debian installation failed.")
        else:
            logger.info("Installed debian packages and resolved dependencies.")
        run_command(f"chroot {self.MOUNT_DIR} {TERMINAL} -c 'cd /tmp/debs && rm -rf *.deb'")
