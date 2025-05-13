import os
import stat
import shlex
import shutil
import logging
import subprocess
from git import Repo
from constants import TERMINAL, HOST_FS_MOUNT

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger(__name__)

def check_if_root() -> bool:
    return os.geteuid() == 0

def check_and_append_line_in_file(file_path, line_to_check, append_if_missing=False):
    if not os.path.exists(file_path):
        logger.error(f"{file_path} does not exist.")
        exit(1)
    
    lines = []
    with open(file_path, "r") as file:
        lines = file.readlines()
    
    for line in lines:
        if line.strip() == line_to_check.strip():
            return True

    if append_if_missing:
        with open(file_path, "a") as file:
            file.write(f"\n{line_to_check}\n")
        return True

    return False

def run_command(command, check=True, get_object=False):
    logger.info(f'Running {command}')
    result = subprocess.run(command, shell=True, check=check, capture_output=True, text=True)
    return result.stdout.strip()

def run_command_for_result(command):
    logger.info(f'Running {command} for result')
    try:
        result = subprocess.check_output(command, shell=True, stderr=subprocess.DEVNULL)
        return {"output": result.decode("utf-8").strip(), "returncode": 0}
    except subprocess.CalledProcessError as e:
        return {"output": e.output.decode("utf-8", errors="ignore").strip(), "returncode": e.returncode}

def clone_repo(repo_url, clone_path, depth=None):
    if os.path.exists(clone_path):
        logger.info(f"Repository already exists at {clone_path}. Skipping clone.")
        return

    logger.info(f"Cloning {repo_url}")
    try:
        if depth:
            Repo.clone_from(repo_url, clone_path, depth=depth)
        else:
            Repo.clone_from(repo_url, clone_path)
    except Exception as e:
        logger.error(f"{e}")

def set_env(key, value):
    os.environ[str(key)] = str(value)

def cleanup_directory(dirname):
    try:
        if os.path.exists(dirname):
            shutil.rmtree(dirname)
    except Exception as e:
        logger.error(f"Error cleaning directory {dirname}: {e}")
        raise Exception(e)

def cleanup_file(file_path):
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        logger.error(f"Error cleaning file {file_path}: {e}")
        raise Exception(e)

def create_new_directory(dirname, delete_if_exists=True):
    try:
        if os.path.exists(dirname):
            # Check if the directory exists, if so delete it
            if delete_if_exists:
                cleanup_directory(dirname)
        # Create the destination directory
        os.makedirs(dirname, exist_ok=not delete_if_exists)
    except Exception as e:
        logger.error(f"Error creating directory {dirname}: {e}")
        exit(1)

def mount_img(IMG_PATH, MOUNT_DIR, MOUNT_HOST_FS=False):
    create_new_directory(MOUNT_DIR)
    run_command(f"mount {IMG_PATH} {MOUNT_DIR}")
    if MOUNT_HOST_FS:
        for direc in HOST_FS_MOUNT:
            run_command(f"mount --bind /{direc} {MOUNT_DIR}/{direc}")

def umount_dir(MOUNT_DIR, UMOUNT_HOST_FS=False):
    if UMOUNT_HOST_FS:
        for direc in HOST_FS_MOUNT:
            run_command(f"umount -l {MOUNT_DIR}/{direc}")
    run_command(f"umount -l {MOUNT_DIR}")

def get_quote_terminal():
    if not TERMINAL.startswith('/') or " " in TERMINAL or ";" in TERMINAL:
        raise ValueError("Invalid TERMINAL path")

    return shlex.quote(TERMINAL)

def move_files_with_ext(SOURCE_DIR, DEST_DIR, EXT):
    for filename in os.listdir(SOURCE_DIR):
        if filename.endswith(EXT):
            source_file = os.path.join(SOURCE_DIR, filename)
            destination_file = os.path.join(DEST_DIR, filename)

            shutil.move(source_file, destination_file)

def change_folder_perm_read_write(DIR):


    try:
        # Change permissions for the root folder itself
        current_permissions = os.stat(DIR).st_mode
        new_permissions = current_permissions

        if current_permissions & stat.S_IWUSR:
            new_permissions |= stat.S_IWOTH

        if current_permissions & stat.S_IXUSR:
            new_permissions |= stat.S_IXOTH

        os.chmod(DIR, new_permissions)

        for root, dirs, files in os.walk(DIR):
            for dir_ in dirs:
                dir_path = os.path.join(root, dir_)
                current_permissions = os.stat(dir_path).st_mode
                new_permissions = current_permissions

                if current_permissions & stat.S_IWUSR:
                    new_permissions |= stat.S_IWOTH
                if current_permissions & stat.S_IXUSR:
                    new_permissions |= stat.S_IXOTH

                os.chmod(dir_path, new_permissions)

            for file in files:
                file_path = os.path.join(root, file)
                current_permissions = os.stat(file_path).st_mode
                new_permissions = current_permissions

                if current_permissions & stat.S_IWUSR:
                    new_permissions |= stat.S_IWOTH
                if current_permissions & stat.S_IXUSR:
                    new_permissions |= stat.S_IXOTH

                os.chmod(file_path, new_permissions)

        logger.info(f"Permissions updated conditionally for all folders and files in {DIR}.")
    except Exception as e:
        logger.error(f"Error while changing permissions: {e}")
