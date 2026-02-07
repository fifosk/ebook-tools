#!/usr/bin/env python3
"""
Add a tvOS XCUITest target to the InteractiveReader Xcode project.

Creates an ``InteractiveReaderTVUITests`` UI testing target linked to
the InteractiveReaderTV app target, sharing the same Swift source files
as the iOS UITest target but targeting tvOS.

Usage:
    python scripts/ios_add_tvos_uitest_target.py          # modify project
    python scripts/ios_add_tvos_uitest_target.py --dry-run # preview only

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
TVOS_APP_TARGET_ID = "5FBFACE368BC4A83A49DBC15"  # InteractiveReaderTV native target
PROJECT_OBJECT_ID = "6FDC3A002F914D000A1D9A1"    # PBXProject
PRODUCTS_GROUP_ID = "6FDC3A022F914D000A1D9A1"     # Products group
UITEST_GROUP_ID = "6DA59684CC951ACBC35DCC62"       # Existing InteractiveReaderUITests group

DEVELOPMENT_TEAM = "3Y7288895K"

# Existing UITest source file refs (shared with iOS UITest target)
EXISTING_SOURCE_FILEREFS = {
    "InteractiveReaderUITests.swift": "B1088DAB377D40179772EAF4",
    "TestHelpers.swift":             "62F3A559C4D959CD6E430283",
    "LoginTests.swift":              "BB0BCC912124F06CD7238F1D",
    "LibraryTests.swift":            "F637AD70397CB79A23D169A2",
    "PlaybackTests.swift":           "9DDDBC4E639F934903C0BB79",
    "JourneyRunner.swift":           "0B9D706F6022E09B1743CF52",
    "JourneyTests.swift":            "A87D28F7449E229F4AE82305",
}


def _gen(seed: str) -> str:
    """24-char uppercase hex ID, deterministic from seed."""
    return hashlib.sha256(seed.encode()).hexdigest().upper()[:24]


# Pre-generate IDs
TV_UITEST_TARGET_ID          = _gen("tv-uitest:target")
TV_UITEST_PRODUCT_REF_ID     = _gen("tv-uitest:product-ref")
TV_UITEST_SOURCES_PHASE_ID   = _gen("tv-uitest:sources-phase")
TV_UITEST_FRAMEWORKS_PHASE_ID = _gen("tv-uitest:frameworks-phase")
TV_UITEST_DEPENDENCY_ID      = _gen("tv-uitest:target-dependency")
TV_UITEST_PROXY_ID           = _gen("tv-uitest:container-proxy")
TV_UITEST_DEBUG_CONFIG_ID    = _gen("tv-uitest:config-debug")
TV_UITEST_RELEASE_CONFIG_ID  = _gen("tv-uitest:config-release")
TV_UITEST_CONFIG_LIST_ID     = _gen("tv-uitest:config-list")

# Build file IDs for each shared source (one per file)
TV_BUILD_FILE_IDS = {}
for fname in EXISTING_SOURCE_FILEREFS:
    TV_BUILD_FILE_IDS[fname] = _gen(f"tv-uitest:build:{fname}")


def add_tvos_uitest_target(content: str) -> str:
    """Insert tvOS UITest target entries into the pbxproj content."""

    if "InteractiveReaderTVUITests" in content:
        print("InteractiveReaderTVUITests already exists. Skipping.")
        return content

    # ── 1. PBXFileReference for .xctest product ──────────────────
    ref_line = (
        f"\t\t{TV_UITEST_PRODUCT_REF_ID} /* InteractiveReaderTVUITests.xctest */ = "
        f"{{isa = PBXFileReference; explicitFileType = wrapper.cfbundle; "
        f'includeInIndex = 0; path = InteractiveReaderTVUITests.xctest; '
        f'sourceTree = BUILT_PRODUCTS_DIR; }};\n'
    )
    anchor = "/* End PBXFileReference section */"
    content = content.replace(anchor, ref_line + anchor)

    # ── 2. PBXBuildFile entries (one per shared source file) ─────
    build_lines = ""
    for fname, fileref in EXISTING_SOURCE_FILEREFS.items():
        bid = TV_BUILD_FILE_IDS[fname]
        build_lines += (
            f"\t\t{bid} /* {fname} in Sources */ = "
            f"{{isa = PBXBuildFile; fileRef = {fileref} /* {fname} */; }};\n"
        )
    anchor = "/* End PBXBuildFile section */"
    content = content.replace(anchor, build_lines + anchor)

    # ── 3. Add .xctest to Products group ─────────────────────────
    products_pattern = rf"({re.escape(PRODUCTS_GROUP_ID)}.*?children\s*=\s*\()"
    match = re.search(products_pattern, content, re.DOTALL)
    if match:
        insert_pos = match.end()
        product_ref = f"\n\t\t\t\t{TV_UITEST_PRODUCT_REF_ID} /* InteractiveReaderTVUITests.xctest */,"
        content = content[:insert_pos] + product_ref + content[insert_pos:]

    # ── 4. PBXContainerItemProxy ─────────────────────────────────
    proxy_block = (
        f"\t\t{TV_UITEST_PROXY_ID} /* PBXContainerItemProxy */ = {{\n"
        f"\t\t\tisa = PBXContainerItemProxy;\n"
        f"\t\t\tcontainerPortal = {PROJECT_OBJECT_ID} /* Project object */;\n"
        f"\t\t\tproxyType = 1;\n"
        f"\t\t\tremoteGlobalIDString = {TVOS_APP_TARGET_ID};\n"
        f"\t\t\tremoteInfo = InteractiveReaderTV;\n"
        f"\t\t}};\n"
    )
    anchor = "/* End PBXContainerItemProxy section */"
    content = content.replace(anchor, proxy_block + anchor)

    # ── 5. PBXTargetDependency ───────────────────────────────────
    dep_block = (
        f"\t\t{TV_UITEST_DEPENDENCY_ID} /* PBXTargetDependency */ = {{\n"
        f"\t\t\tisa = PBXTargetDependency;\n"
        f"\t\t\ttarget = '{TVOS_APP_TARGET_ID}';\n"
        f"\t\t\ttargetProxy = {TV_UITEST_PROXY_ID} /* PBXContainerItemProxy */;\n"
        f"\t\t}};\n"
    )
    anchor = "/* End PBXTargetDependency section */"
    content = content.replace(anchor, dep_block + anchor)

    # ── 6. PBXSourcesBuildPhase ──────────────────────────────────
    files_list = ""
    for fname in EXISTING_SOURCE_FILEREFS:
        bid = TV_BUILD_FILE_IDS[fname]
        files_list += f"\t\t\t\t{bid} /* {fname} in Sources */,\n"

    sources_block = (
        f"\t\t{TV_UITEST_SOURCES_PHASE_ID} /* Sources */ = {{\n"
        f"\t\t\tisa = PBXSourcesBuildPhase;\n"
        f"\t\t\tbuildActionMask = 2147483647;\n"
        f"\t\t\tfiles = (\n"
        f"{files_list}"
        f"\t\t\t);\n"
        f"\t\t\trunOnlyForDeploymentPostprocessing = 0;\n"
        f"\t\t}};\n"
    )
    anchor = "/* End PBXSourcesBuildPhase section */"
    content = content.replace(anchor, sources_block + anchor)

    # ── 7. PBXFrameworksBuildPhase ────────────────────────────────
    frameworks_block = (
        f"\t\t{TV_UITEST_FRAMEWORKS_PHASE_ID} /* Frameworks */ = {{\n"
        f"\t\t\tisa = PBXFrameworksBuildPhase;\n"
        f"\t\t\tbuildActionMask = 2147483647;\n"
        f"\t\t\tfiles = (\n"
        f"\t\t\t);\n"
        f"\t\t\trunOnlyForDeploymentPostprocessing = 0;\n"
        f"\t\t}};\n"
    )
    anchor = "/* End PBXFrameworksBuildPhase section */"
    content = content.replace(anchor, frameworks_block + anchor)

    # ── 8. PBXNativeTarget ───────────────────────────────────────
    target_block = (
        f"\t\t{TV_UITEST_TARGET_ID} /* InteractiveReaderTVUITests */ = {{\n"
        f"\t\t\tisa = PBXNativeTarget;\n"
        f'\t\t\tbuildConfigurationList = {TV_UITEST_CONFIG_LIST_ID} /* Build configuration list for PBXNativeTarget "InteractiveReaderTVUITests" */;\n'
        f"\t\t\tbuildPhases = (\n"
        f"\t\t\t\t{TV_UITEST_SOURCES_PHASE_ID} /* Sources */,\n"
        f"\t\t\t\t{TV_UITEST_FRAMEWORKS_PHASE_ID} /* Frameworks */,\n"
        f"\t\t\t);\n"
        f"\t\t\tbuildRules = (\n"
        f"\t\t\t);\n"
        f"\t\t\tdependencies = (\n"
        f"\t\t\t\t{TV_UITEST_DEPENDENCY_ID} /* PBXTargetDependency */,\n"
        f"\t\t\t);\n"
        f"\t\t\tname = InteractiveReaderTVUITests;\n"
        f"\t\t\tproductName = InteractiveReaderTVUITests;\n"
        f"\t\t\tproductReference = {TV_UITEST_PRODUCT_REF_ID} /* InteractiveReaderTVUITests.xctest */;\n"
        f'\t\t\tproductType = "com.apple.product-type.bundle.ui-testing";\n'
        f"\t\t}};\n"
    )
    anchor = "/* End PBXNativeTarget section */"
    content = content.replace(anchor, target_block + anchor)

    # ── 9. Add target to PBXProject targets list ─────────────────
    # Insert after InteractiveReaderUITests in the targets list
    content = content.replace(
        "0C515E7D8CF3CAD1F3DB6896 /* InteractiveReaderUITests */,\n\t\t\t);",
        f"0C515E7D8CF3CAD1F3DB6896 /* InteractiveReaderUITests */,\n"
        f"\t\t\t\t{TV_UITEST_TARGET_ID} /* InteractiveReaderTVUITests */,\n\t\t\t);",
    )

    # ── 10. XCBuildConfiguration (Debug + Release) ────────────────
    debug_config = (
        f"\t\t{TV_UITEST_DEBUG_CONFIG_ID} /* Debug */ = {{\n"
        f"\t\t\tisa = XCBuildConfiguration;\n"
        f"\t\t\tbuildSettings = {{\n"
        f"\t\t\t\tCODE_SIGN_STYLE = Automatic;\n"
        f"\t\t\t\tCURRENT_PROJECT_VERSION = 1;\n"
        f"\t\t\t\tDEVELOPMENT_TEAM = {DEVELOPMENT_TEAM};\n"
        f"\t\t\t\tGENERATE_INFOPLIST_FILE = YES;\n"
        f"\t\t\t\tMARKETING_VERSION = 1.0;\n"
        f'\t\t\t\tPRODUCT_BUNDLE_IDENTIFIER = com.example.InteractiveReader.TVUITests;\n'
        f'\t\t\t\tPRODUCT_NAME = "$(TARGET_NAME)";\n'
        f"\t\t\t\tSDKROOT = appletvos;\n"
        f"\t\t\t\tSUPPORTED_PLATFORMS = \"appletvsimulator appletvos\";\n"
        f"\t\t\t\tSWIFT_EMIT_LOC_STRINGS = NO;\n"
        f"\t\t\t\tSWIFT_VERSION = 5.9;\n"
        f"\t\t\t\tTARGETED_DEVICE_FAMILY = 3;\n"
        f"\t\t\t\tTEST_TARGET_NAME = InteractiveReaderTV;\n"
        f"\t\t\t\tTVOS_DEPLOYMENT_TARGET = 17.0;\n"
        f"\t\t\t}};\n"
        f"\t\t\tname = Debug;\n"
        f"\t\t}};\n"
    )
    release_config = (
        f"\t\t{TV_UITEST_RELEASE_CONFIG_ID} /* Release */ = {{\n"
        f"\t\t\tisa = XCBuildConfiguration;\n"
        f"\t\t\tbuildSettings = {{\n"
        f"\t\t\t\tCODE_SIGN_STYLE = Automatic;\n"
        f"\t\t\t\tCURRENT_PROJECT_VERSION = 1;\n"
        f"\t\t\t\tDEVELOPMENT_TEAM = {DEVELOPMENT_TEAM};\n"
        f"\t\t\t\tGENERATE_INFOPLIST_FILE = YES;\n"
        f"\t\t\t\tMARKETING_VERSION = 1.0;\n"
        f'\t\t\t\tPRODUCT_BUNDLE_IDENTIFIER = com.example.InteractiveReader.TVUITests;\n'
        f'\t\t\t\tPRODUCT_NAME = "$(TARGET_NAME)";\n'
        f"\t\t\t\tSDKROOT = appletvos;\n"
        f"\t\t\t\tSUPPORTED_PLATFORMS = \"appletvsimulator appletvos\";\n"
        f"\t\t\t\tSWIFT_EMIT_LOC_STRINGS = NO;\n"
        f"\t\t\t\tSWIFT_VERSION = 5.9;\n"
        f"\t\t\t\tTARGETED_DEVICE_FAMILY = 3;\n"
        f"\t\t\t\tTEST_TARGET_NAME = InteractiveReaderTV;\n"
        f"\t\t\t\tTVOS_DEPLOYMENT_TARGET = 17.0;\n"
        f"\t\t\t}};\n"
        f"\t\t\tname = Release;\n"
        f"\t\t}};\n"
    )
    anchor = "/* End XCBuildConfiguration section */"
    content = content.replace(anchor, debug_config + release_config + anchor)

    # ── 11. XCConfigurationList ──────────────────────────────────
    config_list = (
        f'\t\t{TV_UITEST_CONFIG_LIST_ID} /* Build configuration list for PBXNativeTarget "InteractiveReaderTVUITests" */ = {{\n'
        f"\t\t\tisa = XCConfigurationList;\n"
        f"\t\t\tbuildConfigurations = (\n"
        f"\t\t\t\t{TV_UITEST_DEBUG_CONFIG_ID} /* Debug */,\n"
        f"\t\t\t\t{TV_UITEST_RELEASE_CONFIG_ID} /* Release */,\n"
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

    parser = argparse.ArgumentParser(description="Add tvOS XCUITest target to the Xcode project.")
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
    print(f"Adding InteractiveReaderTVUITests target...\n")

    content = add_tvos_uitest_target(content)

    if content == original:
        print("No changes made.")
        return

    if args.dry_run:
        print("Dry run — no changes written.")
        for label, uid in [
            ("Target", TV_UITEST_TARGET_ID),
            ("Sources phase", TV_UITEST_SOURCES_PHASE_ID),
            ("Frameworks phase", TV_UITEST_FRAMEWORKS_PHASE_ID),
            ("Product ref", TV_UITEST_PRODUCT_REF_ID),
            ("Debug config", TV_UITEST_DEBUG_CONFIG_ID),
            ("Release config", TV_UITEST_RELEASE_CONFIG_ID),
            ("Config list", TV_UITEST_CONFIG_LIST_ID),
            ("Dependency", TV_UITEST_DEPENDENCY_ID),
            ("Proxy", TV_UITEST_PROXY_ID),
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
    print("  1. Create scheme: InteractiveReaderTVUITests")
    print("  2. Build: xcodebuild -project ... -scheme InteractiveReaderTVUITests -destination 'platform=tvOS Simulator,name=Apple TV' test")


if __name__ == "__main__":
    main()
