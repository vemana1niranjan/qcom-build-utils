import os
import glob
import shlex
import tempfile
import subprocess
from helpers import logger, cleanup_directory, check_if_root

def build_dtb(deb_dir, deb_file_regex, combined_dtb_filename, out_dir):
    if not check_if_root():
        logger.error('Please run this script as root user.')
        exit(1)

    combined_dtb_bin_path = os.path.join(out_dir, 'dtb.bin')
    if os.path.exists(combined_dtb_bin_path):
        os.remove(combined_dtb_bin_path)

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
        if combined_dtb_filename in files:
            file_path = os.path.join(root, combined_dtb_filename)
            break
    
    # Step 3: Process the combined-dtb.dtb file
    if file_path:
        # Step 4: Use a hardcoded block size
        block_size = 65536

        try:
            # Step 5: Create the VFAT partition
            create_vfat_partition_cmd = f"mkfs.vfat -C {combined_dtb_bin_path} {block_size}"
            subprocess.run(shlex.split(create_vfat_partition_cmd), check=True)

            # Step 6: Copy the combined-dtb.dtb to the VFAT partition
            copy_combine_dtb_cmd = f"mcopy -i {combined_dtb_bin_path} -vsmpQ {file_path} ::/"
            subprocess.run(shlex.split(copy_combine_dtb_cmd), check=True)

            logger.info(f"{combined_dtb_filename} has been copied to {combined_dtb_bin_path} as dtb.bin")
        except Exception as e:
            logger.error(f"Error processing file {file_path}")
            logger.error(f"Resulted in error: {e}")

    else:
        logger.error(f"{combined_dtb_filename} not found in {deb_file}")

    # Step 7: Clean up the temporary directory
    cleanup_directory(temp_dir)
