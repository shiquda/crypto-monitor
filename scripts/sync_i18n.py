import json
import re
from pathlib import Path


def get_project_root():
    # Assuming this script is in scripts/
    return Path(__file__).parent.parent


def scan_for_strings(root_dir: Path):
    """
    Scans .py files in the project for strings wrapped in _("...").
    Returns a set of found keys.
    """
    keys = set()
    # Regex to catch _("string") or _('string')
    pattern = re.compile(r'_\(["\'](.*?)["\']\)')

    # Directories to omit
    exclude_dirs = {
        ".git",
        "venv",
        ".venv",
        "env",
        ".env",
        "__pycache__",
        ".idea",
        ".vscode",
        "build",
        "dist",
        "scripts",
    }

    print(f"Scanning for translatable strings in {root_dir}...")

    count_files = 0
    for file_path in root_dir.rglob("*.py"):
        # Check if file is in excluded directory
        parts = file_path.relative_to(root_dir).parts
        if any(p in exclude_dirs for p in parts):
            continue

        count_files += 1
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
                matches = pattern.findall(content)
                for m in matches:
                    keys.add(m)
        except Exception as e:
            print(f"Error reading {file_path}: {e}")

    print(f"Scanned {count_files} Python files.")
    return keys


def sync_json_file(file_path: Path, found_keys: set, is_source=False):
    """
    Updates the JSON file.
    - Adds new keys from found_keys.
    - Reports obsolete keys (keys in json but not in code).
    - Sorts keys.
    """
    data = {}
    if file_path.exists():
        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: Could not parse {file_path}, starting fresh.")
            data = {}

    # Add new keys
    added_count = 0
    for k in found_keys:
        if k not in data:
            # If it's the source language, the value is the key itself.
            # If it's a target language, leave it empty.
            data[k] = k if is_source else ""
            added_count += 1

    # Check for obsolete keys
    existing_keys = set(data.keys())
    obsolete_keys = existing_keys - found_keys

    # Remove obsolete keys
    removed_count = 0
    for k in obsolete_keys:
        del data[k]
        removed_count += 1

    # Write back sorted
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False, sort_keys=True)

    lang_code = file_path.stem

    empty_keys = [k for k, v in data.items() if not v]

    msg = f"[{lang_code}] +{added_count} new"
    if removed_count:
        msg += f", -{removed_count} removed"
    if empty_keys:
        msg += f", {len(empty_keys)} empty values"
    print(msg)


def main():
    root = get_project_root()
    i18n_dir = root / "i18n"

    if not i18n_dir.exists():
        i18n_dir.mkdir()

    keys = scan_for_strings(root)
    print(f"Found {len(keys)} unique translatable strings in code.")

    if not keys:
        print("No keys found. Aborting sync.")
        return

    # 1. Sync en_US.json (Source) explicitly first
    en_path = i18n_dir / "en_US.json"
    sync_json_file(en_path, keys, is_source=True)

    # 2. Sync all other existing JSON files in i18n/
    # We automatically discover all json files
    for file_path in i18n_dir.glob("*.json"):
        if file_path.name == "en_US.json":
            continue
        sync_json_file(file_path, keys, is_source=False)

    print("\nSync completed.")


if __name__ == "__main__":
    main()
