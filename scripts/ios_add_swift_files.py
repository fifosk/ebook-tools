#!/usr/bin/env python3
"""
Add Swift source files to the InteractiveReader Xcode project.

Adds new .swift files to both the iOS (InteractiveReader) and tvOS
(InteractiveReaderTV) targets, including:
  - PBXFileReference entry
  - PBXBuildFile entries (one per target)
  - PBXGroup membership (in the appropriate folder group)
  - PBXSourcesBuildPhase membership (in both targets)

Usage:
    python scripts/ios_add_swift_files.py <relative_path> [<relative_path> ...]

Paths are relative to the InteractiveReader/ source root, e.g.:
    python scripts/ios_add_swift_files.py \
        Features/Music/AppleMusicPickerView.swift \
        Services/MusicKitCoordinator.swift \
        Services/MusicSearchService.swift

The script automatically resolves the correct PBXGroup based on the
directory portion of the path.

Requirements:
    pip install pbxproj

If the pbxproj library fails (it sometimes has issues with certain build
phase IDs), the script falls back to direct text insertion with careful
anchor-based edits.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
from pathlib import Path

# --- Constants ---

PROJ_DIR = Path(__file__).resolve().parent.parent / "ios" / "InteractiveReader"
PBXPROJ = PROJ_DIR / "InteractiveReader.xcodeproj" / "project.pbxproj"

# Target names
IOS_TARGET = "InteractiveReader"
TVOS_TARGET = "InteractiveReaderTV"

# Known Sources build phase IDs (from project.pbxproj)
IOS_SOURCES_PHASE = "6FDC3A112F914D000A1D9A1"
TVOS_SOURCES_PHASE = "CBE58951F4AB41F8BEA08E64"

# Known group IDs mapped by directory path under InteractiveReader/
# If your directory isn't listed, the script will search for it.
KNOWN_GROUPS = {
    "App": "6FDC3A042F914D000A1D9A1",
    "Features": "6FDC3A052F914D000A1D9A1",
    "Features/JobLoader": "6FDC3A062F914D000A1D9A1",
    "Features/InteractivePlayer": "6FDC3A072F914D000A1D9A1",
    "Features/Auth": "1B35D2C80F014B58809F6996",
    "Features/Library": "1BC179E753F14AFCA4C06B67",
    "Features/Playback": "399FA7B84B6D428481E553DB",
    "Features/Playback/Shared": "E8D30580E9744E8D922DDF7D",
    "Features/Shared": "C0A1B2C3D4E5F60718293A4E",
    "Features/Jobs": "C8D9E0F1A2B3C4D5E6F70810",
    "Models": "6FDC3A082F914D000A1D9A1",
    "Services": "6FDC3A092F914D000A1D9A1",
    "Utilities": "6FDC3A0A2F914D000A1D9A1",
    "Resources": "6FDC3A0B2F914D000A1D9A1",
    "Supporting": "6FDC3A0E2F914D000A1D9A1",
}


def generate_id(seed: str, length: int = 24) -> str:
    """Generate a deterministic hex ID from a seed string."""
    h = hashlib.sha256(seed.encode()).hexdigest().upper()
    return h[:length]


def file_already_in_project(content: str, filename: str) -> bool:
    """Check if a filename already has a PBXFileReference."""
    pattern = rf'/\*\s*{re.escape(filename)}\s*\*/'
    return bool(re.search(pattern, content))


def find_group_id(content: str, group_name: str) -> str | None:
    """Search for a PBXGroup with the given path name and return its ID."""
    # Match pattern: <ID> /* <name> */ = { ... path = <name>; ...
    # Or: <ID> = { ... path = <name>; ...
    pattern = rf'(\w+)\s*(?:/\*[^*]*\*/\s*)?=\s*\{{[^}}]*?path\s*=\s*{re.escape(group_name)}\s*;'
    match = re.search(pattern, content)
    if match:
        return match.group(1).strip("'\"")
    return None


def find_last_entry_in_section(content: str, section_id: str) -> int | None:
    """Find the position just before the closing ')' of a build phase's files list."""
    # Find the section by its ID
    id_pattern = re.escape(section_id.strip("'\""))
    # Match the quoted or unquoted form, with optional /* comment */
    section_re = rf"['\"]?{id_pattern}['\"]?\s*(?:/\*[^*]*\*/\s*)?=\s*\{{"
    match = re.search(section_re, content)
    if not match:
        return None

    # Find the 'files = (' within this section
    start = match.start()
    files_match = re.search(r'files\s*=\s*\(', content[start:])
    if not files_match:
        return None

    files_start = start + files_match.end()
    # Find the matching closing ')'
    depth = 1
    pos = files_start
    while pos < len(content) and depth > 0:
        if content[pos] == '(':
            depth += 1
        elif content[pos] == ')':
            depth -= 1
        pos += 1

    # pos is now just after the closing ')'
    # We want to insert before the closing ')'
    closing_paren = pos - 1

    # Find the last line before the closing paren
    last_newline = content.rfind('\n', files_start, closing_paren)
    if last_newline == -1:
        return closing_paren
    return last_newline + 1


def find_group_children_end(content: str, group_id: str) -> int | None:
    """Find the position to insert a new child into a PBXGroup's children list."""
    id_pattern = re.escape(group_id.strip("'\""))
    group_re = rf"['\"]?{id_pattern}['\"]?\s*(?:/\*[^*]*\*/\s*)?=\s*\{{"
    match = re.search(group_re, content)
    if not match:
        return None

    start = match.start()
    children_match = re.search(r'children\s*=\s*\(', content[start:])
    if not children_match:
        return None

    children_start = start + children_match.end()
    depth = 1
    pos = children_start
    while pos < len(content) and depth > 0:
        if content[pos] == '(':
            depth += 1
        elif content[pos] == ')':
            depth -= 1
        pos += 1

    closing_paren = pos - 1
    last_newline = content.rfind('\n', children_start, closing_paren)
    if last_newline == -1:
        return closing_paren
    return last_newline + 1


def add_file_to_project(content: str, relative_path: str, dry_run: bool = False) -> str:
    """
    Add a single Swift file to the pbxproj content.

    relative_path: path relative to InteractiveReader/ source root,
                   e.g. "Services/MusicKitCoordinator.swift"
    """
    filename = os.path.basename(relative_path)
    dir_path = os.path.dirname(relative_path)

    if file_already_in_project(content, filename):
        print(f"  SKIP: {filename} already in project")
        return content

    # Generate deterministic IDs
    file_ref_id = generate_id(f"fileref:{relative_path}")
    build_ios_id = generate_id(f"build:ios:{relative_path}")
    build_tvos_id = generate_id(f"build:tvos:{relative_path}")

    # Verify IDs are unique
    for uid in [file_ref_id, build_ios_id, build_tvos_id]:
        if uid in content:
            # Add extra entropy
            uid_new = generate_id(f"extra:{uid}:{relative_path}")
            if uid == file_ref_id:
                file_ref_id = uid_new
            elif uid == build_ios_id:
                build_ios_id = uid_new
            else:
                build_tvos_id = uid_new

    # The sourceTree-relative path
    source_path = f"InteractiveReader/{relative_path}"

    # 1. Add PBXFileReference
    file_ref_line = f'\t\t{file_ref_id} /* {filename} */ = {{isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = {source_path}; sourceTree = SOURCE_ROOT; }};\n'

    # Insert after last PBXFileReference entry (before "/* End PBXFileReference section */")
    end_fileref = content.find("/* End PBXFileReference section */")
    if end_fileref == -1:
        print(f"  ERROR: Cannot find PBXFileReference section end")
        return content
    content = content[:end_fileref] + file_ref_line + content[end_fileref:]

    # 2. Add PBXBuildFile entries (two: one for iOS, one for tvOS)
    build_ios_line = f'\t\t{build_ios_id} /* {filename} in Sources */ = {{isa = PBXBuildFile; fileRef = {file_ref_id} /* {filename} */; }};\n'
    build_tvos_line = f'\t\t{build_tvos_id} /* {filename} in Sources */ = {{isa = PBXBuildFile; fileRef = {file_ref_id} /* {filename} */; }};\n'

    end_buildfile = content.find("/* End PBXBuildFile section */")
    if end_buildfile == -1:
        print(f"  ERROR: Cannot find PBXBuildFile section end")
        return content
    content = content[:end_buildfile] + build_ios_line + build_tvos_line + content[end_buildfile:]

    # 3. Add to PBXGroup
    group_id = KNOWN_GROUPS.get(dir_path)
    if not group_id:
        # Try to find by searching the last path component
        last_dir = os.path.basename(dir_path) if dir_path else None
        if last_dir:
            group_id = find_group_id(content, last_dir)
        if not group_id:
            # Fall back to parent directory group
            parent_path = os.path.dirname(dir_path)
            while parent_path and not group_id:
                group_id = KNOWN_GROUPS.get(parent_path)
                if not group_id:
                    parent_name = os.path.basename(parent_path)
                    if parent_name:
                        group_id = find_group_id(content, parent_name)
                parent_path = os.path.dirname(parent_path)
            if group_id:
                print(f"  NOTE: No group for '{dir_path}', using parent group: {group_id}")
            else:
                print(f"  WARNING: No group found for '{dir_path}'")
                print(f"  You'll need to manually add {filename} to a group in Xcode")
        else:
            print(f"  Found group for '{dir_path}': {group_id}")

    if group_id:
        child_line = f'\t\t\t\t{file_ref_id} /* {filename} */,\n'
        insert_pos = find_group_children_end(content, group_id)
        if insert_pos:
            content = content[:insert_pos] + child_line + content[insert_pos:]
        else:
            print(f"  WARNING: Could not find children list for group {group_id}")

    # 4. Add to iOS Sources build phase
    ios_source_line = f'\t\t\t\t{build_ios_id} /* {filename} in Sources */,\n'
    insert_pos = find_last_entry_in_section(content, IOS_SOURCES_PHASE)
    if insert_pos:
        content = content[:insert_pos] + ios_source_line + content[insert_pos:]
    else:
        print(f"  WARNING: Could not find iOS Sources build phase")

    # 5. Add to tvOS Sources build phase
    tvos_source_line = f'\t\t\t\t{build_tvos_id} /* {filename} in Sources */,\n'
    insert_pos = find_last_entry_in_section(content, TVOS_SOURCES_PHASE)
    if insert_pos:
        content = content[:insert_pos] + tvos_source_line + content[insert_pos:]
    else:
        print(f"  WARNING: Could not find tvOS Sources build phase")

    print(f"  ADDED: {filename}")
    print(f"         FileRef: {file_ref_id}")
    print(f"         iOS Build: {build_ios_id}")
    print(f"         tvOS Build: {build_tvos_id}")
    if group_id:
        print(f"         Group: {group_id} ({dir_path})")

    return content


def main():
    parser = argparse.ArgumentParser(
        description="Add Swift files to the InteractiveReader Xcode project.",
        epilog="Paths are relative to InteractiveReader/ source root.",
    )
    parser.add_argument(
        "files",
        nargs="+",
        help="Swift file paths relative to InteractiveReader/ (e.g. Services/Foo.swift)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done without modifying the project file",
    )
    parser.add_argument(
        "--project",
        type=Path,
        default=PBXPROJ,
        help=f"Path to project.pbxproj (default: {PBXPROJ})",
    )
    args = parser.parse_args()

    proj_path = args.project
    if not proj_path.exists():
        print(f"ERROR: Project file not found: {proj_path}", file=sys.stderr)
        sys.exit(1)

    content = proj_path.read_text(encoding="utf-8")
    original = content

    print(f"Project: {proj_path}")
    print(f"Adding {len(args.files)} file(s)...\n")

    for filepath in args.files:
        # Normalize path
        filepath = filepath.strip("/")
        if not filepath.endswith(".swift"):
            print(f"  SKIP: {filepath} (not a .swift file)")
            continue
        print(f"Processing: {filepath}")
        content = add_file_to_project(content, filepath, dry_run=args.dry_run)
        print()

    if content == original:
        print("No changes made.")
        return

    if args.dry_run:
        print("Dry run — no changes written.")
        return

    # Write backup
    backup_path = proj_path.with_suffix(".pbxproj.backup")
    backup_path.write_text(original, encoding="utf-8")
    print(f"Backup saved: {backup_path}")

    # Write updated project
    proj_path.write_text(content, encoding="utf-8")
    print(f"Project updated: {proj_path}")
    print("\nVerify with: xcodebuild -project ... -scheme InteractiveReader build")


if __name__ == "__main__":
    main()
