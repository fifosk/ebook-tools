#!/usr/bin/env python3
"""
Add a XCUITest target to the InteractiveReader Xcode project.

Creates an ``InteractiveReaderUITests`` UI testing target linked to the
main InteractiveReader app target, with Debug/Release build configurations.

Usage:
    python scripts/ios_add_uitest_target.py          # modify project
    python scripts/ios_add_uitest_target.py --dry-run # preview only

This is a one-time operation.  The script creates a .backup before writing.
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

# ── Constants ──────────────────────────────────────────────────────────

PROJ_DIR = Path(__file__).resolve().parent.parent / "ios" / "InteractiveReader"
PBXPROJ = PROJ_DIR / "InteractiveReader.xcodeproj" / "project.pbxproj"

# Existing IDs from the project
IOS_APP_TARGET_ID = "6FDC3A102F914D000A1D9A1"  # InteractiveReader native target
PROJECT_OBJECT_ID = "6FDC3A002F914D000A1D9A1"  # PBXProject
PRODUCTS_GROUP_ID = "6FDC3A022F914D000A1D9A1"  # Products group
MAIN_GROUP_ID = "6FDC3A012F914D000A1D9A1"      # root group

DEVELOPMENT_TEAM = "3Y7288895K"

# ── Deterministic ID generation ────────────────────────────────────────

def _gen(seed: str) -> str:
    """24-char uppercase hex ID, deterministic from seed."""
    return hashlib.sha256(seed.encode()).hexdigest().upper()[:24]

# Pre-generate all IDs we need
UITEST_TARGET_ID         = _gen("uitest:target")
UITEST_PRODUCT_REF_ID    = _gen("uitest:product-ref")
UITEST_SOURCES_PHASE_ID  = _gen("uitest:sources-phase")
UITEST_FRAMEWORKS_PHASE_ID = _gen("uitest:frameworks-phase")
UITEST_DEPENDENCY_ID     = _gen("uitest:target-dependency")
UITEST_PROXY_ID          = _gen("uitest:container-proxy")
UITEST_GROUP_ID          = _gen("uitest:group")
UITEST_DEBUG_CONFIG_ID   = _gen("uitest:config-debug")
UITEST_RELEASE_CONFIG_ID = _gen("uitest:config-release")
UITEST_CONFIG_LIST_ID    = _gen("uitest:config-list")

# Build file IDs for each Swift file we'll add later (via ios_add_swift_files.py)
# For now the sources phase starts empty — files are added when Swift sources are created.


def add_uitest_target(content: str) -> str:
    """Insert all XCUITest target entries into the pbxproj content."""

    # Guard: don't add twice
    if "InteractiveReaderUITests" in content:
        print("InteractiveReaderUITests already exists in the project. Skipping.")
        return content

    # ── 1. PBXFileReference for the .xctest product ──────────────────
    ref_line = (
        f"\t\t{UITEST_PRODUCT_REF_ID} /* InteractiveReaderUITests.xctest */ = "
        f"{{isa = PBXFileReference; explicitFileType = wrapper.cfbundle; "
        f'includeInIndex = 0; path = InteractiveReaderUITests.xctest; '
        f'sourceTree = BUILT_PRODUCTS_DIR; }};\n'
    )
    anchor = "/* End PBXFileReference section */"
    content = content.replace(anchor, ref_line + anchor)

    # ── 2. PBXGroup for the test sources folder ──────────────────────
    group_block = (
        f"\t\t{UITEST_GROUP_ID} /* InteractiveReaderUITests */ = {{\n"
        f"\t\t\tisa = PBXGroup;\n"
        f"\t\t\tchildren = (\n"
        f"\t\t\t);\n"
        f"\t\t\tpath = InteractiveReaderUITests;\n"
        f'\t\t\tsourceTree = "<group>";\n'
        f"\t\t}};\n"
    )
    anchor = "/* End PBXGroup section */"
    content = content.replace(anchor, group_block + anchor)

    # Add the group as a child of the main group (next to InteractiveReader, NotificationServiceExtension)
    # Insert after the NotificationServiceExtension child in the main group
    pattern = rf"({re.escape(MAIN_GROUP_ID)}.*?children\s*=\s*\()"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        insert_pos = match.end()
        child_ref = f"\n\t\t\t\t{UITEST_GROUP_ID} /* InteractiveReaderUITests */,"
        content = content[:insert_pos] + child_ref + content[insert_pos:]

    # Add the .xctest product to the Products group
    products_pattern = rf"({re.escape(PRODUCTS_GROUP_ID)}.*?children\s*=\s*\()"
    match = re.search(products_pattern, content, re.DOTALL)
    if match:
        insert_pos = match.end()
        product_ref = f"\n\t\t\t\t{UITEST_PRODUCT_REF_ID} /* InteractiveReaderUITests.xctest */,"
        content = content[:insert_pos] + product_ref + content[insert_pos:]

    # ── 3. PBXContainerItemProxy ─────────────────────────────────────
    proxy_block = (
        f"\t\t{UITEST_PROXY_ID} /* PBXContainerItemProxy */ = {{\n"
        f"\t\t\tisa = PBXContainerItemProxy;\n"
        f"\t\t\tcontainerPortal = {PROJECT_OBJECT_ID} /* Project object */;\n"
        f"\t\t\tproxyType = 1;\n"
        f"\t\t\tremoteGlobalIDString = {IOS_APP_TARGET_ID};\n"
        f"\t\t\tremoteInfo = InteractiveReader;\n"
        f"\t\t}};\n"
    )
    anchor = "/* End PBXContainerItemProxy section */"
    content = content.replace(anchor, proxy_block + anchor)

    # ── 4. PBXTargetDependency ───────────────────────────────────────
    dep_block = (
        f"\t\t{UITEST_DEPENDENCY_ID} /* PBXTargetDependency */ = {{\n"
        f"\t\t\tisa = PBXTargetDependency;\n"
        f"\t\t\ttarget = '{IOS_APP_TARGET_ID}';\n"
        f"\t\t\ttargetProxy = {UITEST_PROXY_ID} /* PBXContainerItemProxy */;\n"
        f"\t\t}};\n"
    )
    anchor = "/* End PBXTargetDependency section */"
    content = content.replace(anchor, dep_block + anchor)

    # ── 5. PBXSourcesBuildPhase (empty — files added separately) ─────
    # Insert before "/* End PBXSourcesBuildPhase section */" if it exists,
    # otherwise after existing sources blocks.
    sources_block = (
        f"\t\t{UITEST_SOURCES_PHASE_ID} /* Sources */ = {{\n"
        f"\t\t\tisa = PBXSourcesBuildPhase;\n"
        f"\t\t\tbuildActionMask = 2147483647;\n"
        f"\t\t\tfiles = (\n"
        f"\t\t\t);\n"
        f"\t\t\trunOnlyForDeploymentPostprocessing = 0;\n"
        f"\t\t}};\n"
    )
    anchor = "/* End PBXSourcesBuildPhase section */"
    if anchor in content:
        content = content.replace(anchor, sources_block + anchor)
    else:
        # Fallback: insert after the last PBXSourcesBuildPhase block
        # Find all existing Sources blocks and insert after the last one
        last_sources = content.rfind("runOnlyForDeploymentPostprocessing = 0;\n\t\t};\n/* End PBX")
        if last_sources == -1:
            print("WARNING: Could not find PBXSourcesBuildPhase section")
        # We'll try the section end approach instead
        # The project uses /* Begin/End */ section markers

    # ── 6. PBXFrameworksBuildPhase (empty) ────────────────────────────
    frameworks_block = (
        f"\t\t{UITEST_FRAMEWORKS_PHASE_ID} /* Frameworks */ = {{\n"
        f"\t\t\tisa = PBXFrameworksBuildPhase;\n"
        f"\t\t\tbuildActionMask = 2147483647;\n"
        f"\t\t\tfiles = (\n"
        f"\t\t\t);\n"
        f"\t\t\trunOnlyForDeploymentPostprocessing = 0;\n"
        f"\t\t}};\n"
    )
    anchor = "/* End PBXFrameworksBuildPhase section */"
    content = content.replace(anchor, frameworks_block + anchor)

    # ── 7. PBXNativeTarget ───────────────────────────────────────────
    target_block = (
        f"\t\t{UITEST_TARGET_ID} /* InteractiveReaderUITests */ = {{\n"
        f"\t\t\tisa = PBXNativeTarget;\n"
        f'\t\t\tbuildConfigurationList = {UITEST_CONFIG_LIST_ID} /* Build configuration list for PBXNativeTarget "InteractiveReaderUITests" */;\n'
        f"\t\t\tbuildPhases = (\n"
        f"\t\t\t\t{UITEST_SOURCES_PHASE_ID} /* Sources */,\n"
        f"\t\t\t\t{UITEST_FRAMEWORKS_PHASE_ID} /* Frameworks */,\n"
        f"\t\t\t);\n"
        f"\t\t\tbuildRules = (\n"
        f"\t\t\t);\n"
        f"\t\t\tdependencies = (\n"
        f"\t\t\t\t{UITEST_DEPENDENCY_ID} /* PBXTargetDependency */,\n"
        f"\t\t\t);\n"
        f"\t\t\tname = InteractiveReaderUITests;\n"
        f"\t\t\tproductName = InteractiveReaderUITests;\n"
        f"\t\t\tproductReference = {UITEST_PRODUCT_REF_ID} /* InteractiveReaderUITests.xctest */;\n"
        f'\t\t\tproductType = "com.apple.product-type.bundle.ui-testing";\n'
        f"\t\t}};\n"
    )
    anchor = "/* End PBXNativeTarget section */"
    content = content.replace(anchor, target_block + anchor)

    # ── 8. Add target to PBXProject targets list ─────────────────────
    content = content.replace(
        f"\t\t\t\tNOTIFEXT006A0001 /* NotificationServiceExtension */,\n\t\t\t);",
        f"\t\t\t\tNOTIFEXT006A0001 /* NotificationServiceExtension */,\n"
        f"\t\t\t\t{UITEST_TARGET_ID} /* InteractiveReaderUITests */,\n\t\t\t);",
    )

    # ── 9. XCBuildConfiguration (Debug + Release) ────────────────────
    debug_config = (
        f"\t\t{UITEST_DEBUG_CONFIG_ID} /* Debug */ = {{\n"
        f"\t\t\tisa = XCBuildConfiguration;\n"
        f"\t\t\tbuildSettings = {{\n"
        f"\t\t\t\tCODE_SIGN_STYLE = Automatic;\n"
        f"\t\t\t\tCURRENT_PROJECT_VERSION = 1;\n"
        f"\t\t\t\tDEVELOPMENT_TEAM = {DEVELOPMENT_TEAM};\n"
        f"\t\t\t\tGENERATE_INFOPLIST_FILE = YES;\n"
        f"\t\t\t\tIPHONEOS_DEPLOYMENT_TARGET = 17.0;\n"
        f"\t\t\t\tMARKETING_VERSION = 1.0;\n"
        f'\t\t\t\tPRODUCT_BUNDLE_IDENTIFIER = com.example.InteractiveReader.UITests;\n'
        f'\t\t\t\tPRODUCT_NAME = "$(TARGET_NAME)";\n'
        f"\t\t\t\tSWIFT_EMIT_LOC_STRINGS = NO;\n"
        f"\t\t\t\tSWIFT_VERSION = 5.9;\n"
        f"\t\t\t\tTARGETED_DEVICE_FAMILY = \"1,2\";\n"
        f"\t\t\t\tTEST_TARGET_NAME = InteractiveReader;\n"
        f"\t\t\t}};\n"
        f"\t\t\tname = Debug;\n"
        f"\t\t}};\n"
    )
    release_config = (
        f"\t\t{UITEST_RELEASE_CONFIG_ID} /* Release */ = {{\n"
        f"\t\t\tisa = XCBuildConfiguration;\n"
        f"\t\t\tbuildSettings = {{\n"
        f"\t\t\t\tCODE_SIGN_STYLE = Automatic;\n"
        f"\t\t\t\tCURRENT_PROJECT_VERSION = 1;\n"
        f"\t\t\t\tDEVELOPMENT_TEAM = {DEVELOPMENT_TEAM};\n"
        f"\t\t\t\tGENERATE_INFOPLIST_FILE = YES;\n"
        f"\t\t\t\tIPHONEOS_DEPLOYMENT_TARGET = 17.0;\n"
        f"\t\t\t\tMARKETING_VERSION = 1.0;\n"
        f'\t\t\t\tPRODUCT_BUNDLE_IDENTIFIER = com.example.InteractiveReader.UITests;\n'
        f'\t\t\t\tPRODUCT_NAME = "$(TARGET_NAME)";\n'
        f"\t\t\t\tSWIFT_EMIT_LOC_STRINGS = NO;\n"
        f"\t\t\t\tSWIFT_VERSION = 5.9;\n"
        f"\t\t\t\tTARGETED_DEVICE_FAMILY = \"1,2\";\n"
        f"\t\t\t\tTEST_TARGET_NAME = InteractiveReader;\n"
        f"\t\t\t}};\n"
        f"\t\t\tname = Release;\n"
        f"\t\t}};\n"
    )
    anchor = "/* End XCBuildConfiguration section */"
    content = content.replace(anchor, debug_config + release_config + anchor)

    # ── 10. XCConfigurationList ──────────────────────────────────────
    config_list = (
        f'\t\t{UITEST_CONFIG_LIST_ID} /* Build configuration list for PBXNativeTarget "InteractiveReaderUITests" */ = {{\n'
        f"\t\t\tisa = XCConfigurationList;\n"
        f"\t\t\tbuildConfigurations = (\n"
        f"\t\t\t\t{UITEST_DEBUG_CONFIG_ID} /* Debug */,\n"
        f"\t\t\t\t{UITEST_RELEASE_CONFIG_ID} /* Release */,\n"
        f"\t\t\t);\n"
        f"\t\t\tdefaultConfigurationIsVisible = 0;\n"
        f"\t\t\tdefaultConfigurationName = Debug;\n"
        f"\t\t}};\n"
    )
    anchor = "/* End XCConfigurationList section */"
    content = content.replace(anchor, config_list + anchor)

    return content


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Add XCUITest target to the Xcode project.")
    parser.add_argument("--dry-run", action="store_true", help="Preview without modifying")
    parser.add_argument("--project", type=Path, default=PBXPROJ, help="Path to project.pbxproj")
    args = parser.parse_args()

    proj = args.project
    if not proj.exists():
        print(f"ERROR: {proj} not found", file=sys.stderr)
        sys.exit(1)

    content = proj.read_text(encoding="utf-8")
    original = content

    print(f"Project: {proj}")
    print(f"Adding InteractiveReaderUITests target...\n")

    content = add_uitest_target(content)

    if content == original:
        print("No changes made.")
        return

    if args.dry_run:
        print("Dry run — no changes written.")
        # Show a summary of what was added
        for label, uid in [
            ("Target", UITEST_TARGET_ID),
            ("Sources phase", UITEST_SOURCES_PHASE_ID),
            ("Frameworks phase", UITEST_FRAMEWORKS_PHASE_ID),
            ("Product ref", UITEST_PRODUCT_REF_ID),
            ("Group", UITEST_GROUP_ID),
            ("Debug config", UITEST_DEBUG_CONFIG_ID),
            ("Release config", UITEST_RELEASE_CONFIG_ID),
            ("Config list", UITEST_CONFIG_LIST_ID),
            ("Dependency", UITEST_DEPENDENCY_ID),
            ("Proxy", UITEST_PROXY_ID),
        ]:
            print(f"  {label}: {uid}")
        return

    backup = proj.with_suffix(".pbxproj.backup")
    backup.write_text(original, encoding="utf-8")
    print(f"Backup: {backup}")

    proj.write_text(content, encoding="utf-8")
    print(f"Updated: {proj}")
    print()
    print("Next steps:")
    print("  1. Create test files in ios/InteractiveReader/InteractiveReaderUITests/")
    print("  2. Add files to the project: python scripts/ios_add_swift_files.py ...")
    print("  3. Build: xcodebuild -project ... -scheme InteractiveReaderUITests build-for-testing")


if __name__ == "__main__":
    main()
