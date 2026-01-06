import os
import re
import json

def get_project_root():
    # Assuming this script is in scripts/
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def scan_for_strings(root_dir):
    """
    Scans .py files in the project for strings wrapped in _("...").
    Returns a set of found keys.
    """
    keys = set()
    # Simple regex to catch _("string") or _('string')
    # Use non-greedy match .*? to handle cases correctly
    pattern = re.compile(r'_\(["\'](.*?)["\']\)')
    
    dirs_to_scan = ['core', 'ui', 'config']
    files_to_scan = ['main.py']
    
    # 1. Scan explicit files
    for f_name in files_to_scan:
        f_path = os.path.join(root_dir, f_name)
        if os.path.exists(f_path):
            with open(f_path, 'r', encoding='utf-8') as f:
                content = f.read()
                matches = pattern.findall(content)
                for m in matches:
                    keys.add(m)
    
    # 2. Scan directories
    for d_name in dirs_to_scan:
        d_path = os.path.join(root_dir, d_name)
        for root, _, files in os.walk(d_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        matches = pattern.findall(content)
                        for m in matches:
                            keys.add(m)
    
    return keys

def sync_json_file(file_path, found_keys, is_source=False):
    """
    Updates the JSON file.
    - Adds new keys from found_keys.
    - Removes keys not in found_keys (optional, commented out for safety).
    - Sorts keys.
    """
    data = {}
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: Could not parse {file_path}, starting fresh.")
            data = {}

    # Add new keys
    added_count = 0
    for k in found_keys:
        if k not in data:
            # If it's the source language (en_US), the value is the key itself.
            # If it's a target language (zh_CN), leave it empty or use existing value.
            data[k] = k if is_source else ""
            added_count += 1
            
    # Optional: Clean up obsolete keys (keys in json but not in code)
    # This is dangerous if you have dynamic keys, so maybe just warn?
    # For now, let's just keep them to be safe, or we can uncomment below.
    # removed_count = 0
    # keys_to_remove = [k for k in data.keys() if k not in found_keys]
    # for k in keys_to_remove:
    #    del data[k]
    #    removed_count += 1

    # Write back sorted
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False, sort_keys=True)
    
    print(f"Updated {os.path.basename(file_path)}: +{added_count} new keys.")

def main():
    root = get_project_root()
    i18n_dir = os.path.join(root, 'i18n')
    
    if not os.path.exists(i18n_dir):
        os.makedirs(i18n_dir)
        
    print(f"Scanning project root: {root}")
    keys = scan_for_strings(root)
    print(f"Found {len(keys)} unique translatable strings.")
    
    # Sync en_US.json (Source)
    en_path = os.path.join(i18n_dir, 'en_US.json')
    sync_json_file(en_path, keys, is_source=True)
    
    # Sync zh_CN.json (Target)
    zh_path = os.path.join(i18n_dir, 'zh_CN.json')
    sync_json_file(zh_path, keys, is_source=False)
    
    print("Done. Check i18n/ folder.")

if __name__ == "__main__":
    main()
