import fnmatch

def extract_md5sum_from_files(dsc_path, filename_pattern=None):
    entries = []
    in_files_section = False

    with open(dsc_path, 'r') as dsc_file:
        for line in dsc_file:
            if line.startswith('Files:'):
                in_files_section = True
                continue
            
            if in_files_section and not line.startswith(' '):
                break
            
            if in_files_section and line.startswith(' '):
                parts = line.strip().split(maxsplit=2)
                if len(parts) == 3:
                    md5sum, size, filename = parts
                    if not filename_pattern or fnmatch.fnmatch(filename, filename_pattern):
                        entries.append({
                            'md5sum': md5sum,
                            'size': size,
                            'filename': filename
                        })
    
    return entries
