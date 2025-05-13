import os
import sys
from helpers import logger

from generate_project_info_from_manifest import create_project_info_file

def generate_manifest_map(WORKSPACE_DIR, OUT_FILE='manifest_map.txt'):

    MANIFEST_MAP = {}

    out_file_path = os.path.join(WORKSPACE_DIR, OUT_FILE)

    create_project_info_file(WORKSPACE_DIR,
                            'le/product/manifest',
                            'LE.QCLINUX.1.0',
                            'AU_LINUX_EMBEDDED_LE.QCLINUX.1.0_TARGET_ALL.01.013.495',
                            None,
                            out_file_path)

    with open(out_file_path, 'r') as file:
        for line in file:
            parts = line.strip().split('\t')
            MANIFEST_MAP[parts[0].strip()] = parts[1].strip()

    return MANIFEST_MAP

def search_manifest_map_for_path(MANIFEST_MAP, SOURCE_DIR, path):
    if path:
        path = str(path).strip().replace(SOURCE_DIR, 'sources')
        if path in MANIFEST_MAP:
            return MANIFEST_MAP[path]
        else:
            path_parts = path.split('/')
            num_parts = len(path_parts)
            for key in MANIFEST_MAP.keys():
                key_parts = key.split('/')
                if all(part in path_parts for part in key_parts):
                    return MANIFEST_MAP[key]
    return None
