import os
import glob
import shutil
import shlex
import tempfile
import subprocess
from helpers import logger, cleanup_directory

def build_vmlinuz(deb_dir, deb_file_regex, vmlinuz_filename, out_dir):
    vmlinuz_path = os.path.join(out_dir, vmlinuz_filename)
    if os.path.exists(vmlinuz_path):
        os.remove(vmlinuz_path)

    # Step 0: Check if the .deb file exists
    files = glob.glob(os.path.join(deb_dir, deb_file_regex))
    if len(files) == 0:
        logger.error(f"Error: No files matching {deb_file_regex} exist.")
        exit(1)

    # Step 1: Extract the .deb package to a temporary directory
    deb_file = files[0] # Assuming only one file matches the regex
    try:
        temp_dir = tempfile.mkdtemp()
        logger.info(f'Temp path for dtb extraction: {temp_dir}')
        subprocess.run(["dpkg-deb", '-x', deb_file, temp_dir], check=True)
    except Exception as e:
        logger.error(f"Error extracting .deb file: {e}")
        exit(1)

    # Step 2: Find the specific file within the temporary directory
    file_path = None
    for root, _, files in os.walk(temp_dir):
        for file in files:
            if file.startswith('vmlinuz') and file.endswith('qcom'):
                file_path = os.path.join(root, file)
                break

    # Step 3: Process the vmlinuz file
    if file_path:

        shutil.copy(file_path, vmlinuz_path)
        permissions = 0o644
        os.chmod(vmlinuz_path, permissions)

        logger.info(f"vmlinuz has been copied to {out_dir} as {vmlinuz_filename}")

    else:
        logger.error(f"{vmlinuz_filename} not found in {deb_file}")

    # Step 4: Clean up the temporary directory
    cleanup_directory(temp_dir)
