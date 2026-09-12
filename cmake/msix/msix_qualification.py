#!/usr/bin/env python3
"""Build and independently verify a disposable BeatQuay qualification MSIX.

Copyright 2026 Trieflow LLC. MIT licensed. Derived from PixelQuay qualification
source b7672df853a9e182ed1b081c03ab800dc3dbc778 and ReticleQuay;
retained notices: PIPELINE-MIT.txt and RETICLEQUAY-MIT.txt.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
from pathlib import PurePosixPath
from pathlib import PureWindowsPath
import re
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import unicodedata
from urllib.parse import unquote
import xml.etree.ElementTree as ET
import zipfile
import zlib


APPX_NS = "http://schemas.microsoft.com/appx/manifest/foundation/windows10"
UAP_NS = "http://schemas.microsoft.com/appx/manifest/uap/windows10"
RESCAP_NS = "http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities"
ET.register_namespace("", APPX_NS)
ET.register_namespace("uap", UAP_NS)
ET.register_namespace("rescap", RESCAP_NS)

QUALIFICATION_IDENTITY = {
    "packageName": "Trieflow.BeatQuay.Qualification",
    "publisher": "CN=BeatQuay-CI-Qualification",
    "version": "1.0.0.0",
    "architecture": "x64",
    "applicationId": "BeatQuay",
    "executable": "lmms.exe",
    "deviceFamily": "Windows.Desktop",
    "minVersion": "10.0.19041.0",
    "maxVersionTested": "10.0.26100.0",
    "capability": "runFullTrust",
}
REQUIRED_RELEASE_FILES = (
    "lmms.exe", "Qt6Core.dll", "Qt6Gui.dll", "Qt6Widgets.dll", "Qt6Svg.dll", "Qt6Xml.dll",
    "platforms/qwindows.dll", "iconengines/qsvgicon.dll", "imageformats/qsvg.dll",
    "plugins/audiofileprocessor.dll", "plugins/kicker.dll", "plugins/tripleoscillator.dll",
    "data/projects/templates/BeatQuay-Drum-Grid.mpt",
    "data/projects/templates/BeatQuay-Bassline-Sketch.mpt",
    "data/projects/templates/BEATQUAY-PROVENANCE.md",
    "data/projects/templates/CC0-1.0.txt",
)
RUNTIME = {
    "executable": "lmms.exe", "qtCore": "Qt6Core.dll", "qtGui": "Qt6Gui.dll",
    "qtWidgets": "Qt6Widgets.dll", "qtSvg": "Qt6Svg.dll", "qtXml": "Qt6Xml.dll",
    "platformPlugin": "platforms/qwindows.dll",
}
ALLOWED_PLUGIN_DLLS = {"plugins/audiofileprocessor.dll", "plugins/kicker.dll", "plugins/tripleoscillator.dll"}
ALLOWED_PROJECT_FILES = {name for name in REQUIRED_RELEASE_FILES if name.startswith("data/projects/")}
DEBUG_CRT = {
    "concrt140d.dll", "msvcp140_1d.dll", "msvcp140_2d.dll", "msvcp140d_atomic_wait.dll",
    "msvcp140d_codecvt_ids.dll", "msvcp140d.dll", "ucrtbased.dll", "vcruntime140_1d.dll",
    "vcruntime140d.dll",
}
SOURCE_FILES = (
    "LICENSE.txt", "README.md", "doc/AUTHORS", "doc/UPSTREAM_README.md", "vcpkg.json",
    "distribution/candidate-inputs.json", "distribution/product-identity.md",
    "distribution/msix-qualification.md",
    "distribution/starter-inputs.json", "distribution/starter-arrangements.md",
    "distribution/generate_starters.py", "data/projects/templates/BeatQuay-Drum-Grid.mpt",
    "data/projects/templates/BeatQuay-Bassline-Sketch.mpt",
    "data/projects/templates/BEATQUAY-PROVENANCE.md", "data/projects/templates/CC0-1.0.txt",
    "cmake/msix/PIPELINE-MIT.txt", "cmake/msix/RETICLEQUAY-MIT.txt",
    "cmake/msix/collect-pe-imports.ps1", "cmake/msix/api-set-resolution.ps1",
    "cmake/msix/api-set-resolver.cs",
    "cmake/msix/qualify-msix-install.ps1", "cmake/msix/first-run.ps1",
    "cmake/msix/consumer-workflow.ps1", "cmake/msix/consumer-display.ps1",
    "cmake/msix/consumer_files.py", "tests/scripted/starter_render.py",
    "data/branding/CMakeLists.txt", "data/branding/README.md", "data/branding/generate.py",
    "data/branding/beatquay.svg", "data/branding/beatquay.ico",
    "cmake/modules/BeatQuayIdentity.cmake", "cmake/modules/BeatQuayRuntime.cmake",
    "cmake/nsis/lmms.VisualElementsManifest.xml", "cmake/nsis/lmms.rc.in",
    "include/BeatQuayIdentity.h.in", "src/core/ConfigManager.cpp", "src/core/main.cpp",
    "src/gui/GuiApplication.cpp", "src/gui/MainWindow.cpp", "src/gui/modals/AboutDialog.cpp",
    "src/gui/modals/SetupDialog.cpp", "src/gui/modals/about_dialog.ui",
)
EVIDENCE_FILES = (
    "stage-inventory.json", "vcpkg-installed-status.txt", "qt-downloads.json",
    "dependency-downloads.json", "candidate-inputs.json", "configure-flags.txt", "submodules.txt",
    "render-smoke.json", "starter-render.json", "result.json", "pe-imports.json",
)
PACKAGE_METADATA = {"[Content_Types].xml", "AppxBlockMap.xml", "AppxMetadata/CodeIntegrity.cat"}
PACKAGE_INPUT_RECORD = "build-evidence/package-input.json"


def _canonical_json(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _digest(stream):
    hasher = hashlib.sha256()
    size = 0
    while block := stream.read(1024 * 1024):
        hasher.update(block)
        size += len(block)
    return {"bytes": size, "sha256": hasher.hexdigest()}


def _reject_link(path):
    path = Path(path)
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
        raise ValueError(f"Symlink/reparse point refused: {path}")
    return info


def _regular_stream(path):
    path = Path(path)
    before = _reject_link(path)
    if not stat.S_ISREG(before.st_mode):
        raise ValueError(f"Expected regular file: {path}")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    stream = os.fdopen(fd, "rb")
    after = os.fstat(fd)
    if not stat.S_ISREG(after.st_mode) or (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
        stream.close()
        raise ValueError(f"File identity changed while opening: {path}")
    return stream


def _checked_path(value):
    if not isinstance(value, str) or not value or "\\" in value or ":" in value or value.startswith("/"):
        raise ValueError(f"Unsafe Windows path: {value!r}")
    parts = value.split("/")
    if any(
        not part
        or part in (".", "..")
        or part.endswith((".", " "))
        or re.search(r'[<>"|?*\x00-\x1f\x7f]', part)
        or re.fullmatch(r"(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?", part, re.I)
        for part in parts
    ):
        raise ValueError(f"Unsafe Windows path: {value!r}")
    return value


def _register_path(value, seen):
    _checked_path(value)
    parts = value.split("/")
    for count in range(1, len(parts) + 1):
        prefix = "/".join(parts[:count])
        key = unicodedata.normalize("NFC", prefix).casefold()
        if ("file", key) in seen:
            raise ValueError(f"File/directory or case/Unicode alias: {value}")
        prior = seen.get(("component", key))
        if prior is not None and prior != prefix:
            raise ValueError(f"Case/Unicode path alias: {value}")
        if count == len(parts) and ("directory", key) in seen:
            raise ValueError(f"File/directory path alias: {value}")
        seen[("component", key)] = prefix
        seen[("file" if count == len(parts) else "directory", key)] = prefix


def inventory_tree(root):
    root = Path(root).resolve(strict=True)
    for parent in root.parents:
        _reject_link(parent)
    root_info = _reject_link(root)
    if not stat.S_ISDIR(root_info.st_mode):
        raise ValueError(f"Expected directory: {root}")
    result = {}
    seen = {}

    def walk(directory):
        for path in sorted(directory.iterdir(), key=lambda item: item.name):
            info = _reject_link(path)
            relative = path.relative_to(root).as_posix()
            _checked_path(relative)
            if stat.S_ISDIR(info.st_mode):
                walk(path)
            elif stat.S_ISREG(info.st_mode):
                _register_path(relative, seen)
                with _regular_stream(path) as stream:
                    result[relative] = _digest(stream)
            else:
                raise ValueError(f"Special file refused: {relative}")

    walk(root)
    if not result:
        raise ValueError("Empty tree refused")
    return result


def _load_json(path, label):
    try:
        with _regular_stream(path) as stream:
            raw = stream.read(16 * 1024 * 1024 + 1)
        if len(raw) > 16 * 1024 * 1024:
            raise ValueError(f"Oversized {label}")
        return json.loads(raw.decode("utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Invalid {label}: {error}") from error


def file_record(path):
    with _regular_stream(path) as stream:
        return _digest(stream)


def source_inputs(source_root, artwork):
    source_root, artwork = Path(source_root), Path(artwork)
    result = {name: file_record(source_root / name) for name in SOURCE_FILES}
    try:
        artwork_relative = artwork.resolve(strict=True).relative_to(source_root.resolve(strict=True)).as_posix()
    except (OSError, ValueError) as error:
        raise ValueError("Artwork must be a regular source-owned file") from error
    if artwork_relative != "data/branding/beatquay-256.png":
        raise ValueError("Unexpected BeatQuay package artwork source")
    result[artwork_relative] = file_record(artwork)
    return result


def _inventory_rows(path):
    rows = _load_json(path, "same-run stage inventory")
    if not isinstance(rows, list) or not rows:
        raise ValueError("Stage inventory must be a nonempty list")
    result, seen = {}, set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"path", "bytes", "sha256"}:
            raise ValueError("Invalid stage inventory row")
        relative = _checked_path(row["path"].replace("\\", "/"))
        key = unicodedata.normalize("NFC", relative).casefold()
        if key in seen or type(row["bytes"]) is not int or row["bytes"] <= 0 or not re.fullmatch(r"[0-9A-Fa-f]{64}", row["sha256"]):
            raise ValueError("Duplicate or invalid stage inventory row")
        seen.add(key)
        result[relative] = {"bytes": row["bytes"], "sha256": row["sha256"].lower()}
    return result


def _validate_pe_imports(release, path, files):
    record = _load_json(path, "PE import evidence")
    if not isinstance(record, dict) or record.get("schemaVersion") != 1 or not isinstance(record.get("files"), list):
        raise ValueError("Invalid PE import evidence")
    pe_paths = {name for name in files if name.lower().endswith((".exe", ".dll"))}
    seen = set()
    for row in record["files"]:
        if not isinstance(row, dict) or set(row) != {"path", "bytes", "sha256", "imports"}:
            raise ValueError("Invalid PE import evidence row")
        relative = _checked_path(row["path"].replace("\\", "/"))
        if relative in seen or relative not in pe_paths or {"bytes": row["bytes"], "sha256": str(row["sha256"]).lower()} != files[relative]:
            raise ValueError("PE evidence does not bind the exact stage binary")
        seen.add(relative)
        imports = row["imports"]
        if not isinstance(imports, list):
            raise ValueError("PE imports must be a sorted unique list")
        for name in imports:
            if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_.+\-]+\.(?:dll|exe)", name, re.I | re.ASCII):
                raise ValueError("Invalid imported module name")
        # ASCII casefold produces the collector's lowercase ASCII keys, which
        # it sorts ordinally. Reject repeated names, including case aliases.
        import_keys = [name.casefold() for name in imports]
        if import_keys != sorted(set(import_keys)):
            raise ValueError("PE imports must be a sorted unique list")
    if seen != pe_paths:
        raise ValueError("PE import evidence must cover every staged executable and DLL")
    by_path = {row["path"].replace("\\", "/"): row for row in record["files"]}
    for plugin in ALLOWED_PLUGIN_DLLS:
        if "lmms.exe" not in {name.lower() for name in by_path[plugin]["imports"]}:
            raise ValueError(f"Plugin does not bind the required internal host: {plugin}")
    if record.get("unresolvedImports") != [] or record.get("ambiguousPackagedImports") != [] or record.get("resolutionErrors") != []:
        raise ValueError("Unresolved or ambiguous PE imports remain")
    _validate_api_set_resolutions(record, pe_paths)
    return record


def _validate_api_set_resolutions(record, pe_paths):
    packaged = {PurePosixPath(name).name.casefold() for name in pe_paths}
    required = {
        name.casefold() for row in record["files"] for name in row["imports"]
        if re.fullmatch(r"(?:api|ext)-[a-z0-9-]+-l[0-9]+-[0-9]+-[0-9]+\.dll", name, re.I)
        and name.casefold() not in packaged
    }
    entries = record.get("apiSetResolutions")
    system_value = record.get("systemDirectory")
    if not isinstance(system_value, str):
        raise ValueError("Invalid API-set System32 directory")
    system = PureWindowsPath(system_value)
    if not isinstance(entries, list) or not system.is_absolute() or system.name.casefold() != "system32" or ".." in system.parts:
        raise ValueError("Invalid API-set resolution evidence or System32 directory")
    fields = {"contract", "apiSetImplemented", "loaderFlags", "hostPath", "hostBytes", "hostSha256",
              "signatureStatus", "signerSubject", "signerIssuer", "signerThumbprint", "signerCommonName", "signerOrganization"}
    seen = set()
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != fields:
            raise ValueError("Invalid API-set host evidence")
        contract = entry["contract"]
        if not isinstance(contract, str) or contract not in required or contract in seen:
            raise ValueError("Unexpected or duplicate API-set contract evidence")
        seen.add(contract)
        host = PureWindowsPath(entry["hostPath"]) if isinstance(entry["hostPath"], str) else PureWindowsPath()
        if (not host.is_absolute() or host.parent != system or ".." in host.parts
                or type(entry["hostBytes"]) is not int or entry["hostBytes"] <= 0
                or not isinstance(entry["hostSha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", entry["hostSha256"])
                or entry["apiSetImplemented"] is not True or type(entry["loaderFlags"]) is not int or entry["loaderFlags"] != 2048
                or entry["signatureStatus"] != "Valid" or entry["signerOrganization"] != "Microsoft Corporation"
                or entry["signerCommonName"] not in {"Microsoft Windows Publisher", "Microsoft Corporation", "Microsoft Windows"}
                or any(not isinstance(entry[key], str) or not entry[key] for key in ("signerSubject", "signerIssuer", "signerThumbprint"))
                or not re.fullmatch(r"[0-9a-f]{40}", entry["signerThumbprint"])):
            raise ValueError("Invalid API-set System32 host provenance")
    if seen != required:
        raise ValueError("API-set evidence must cover every nonpackaged contract import")


def create_input_inventory(release, source_root, source_commit, evidence_root, artwork):
    if not re.fullmatch(r"[0-9a-f]{40}", source_commit or ""):
        raise ValueError("Exact source commit required")
    release = Path(release)
    files = inventory_tree(release)
    for name in REQUIRED_RELEASE_FILES:
        if name not in files or files[name]["bytes"] == 0:
            raise ValueError(f"Missing runtime/resource/notice: {name}")
    if {name.casefold() for name in files if Path(name).name.casefold() in DEBUG_CRT}:
        raise ValueError("Debug CRT is forbidden from qualification stage")
    if {name for name in files if name.startswith("plugins/") and name.lower().endswith(".dll")} != ALLOWED_PLUGIN_DLLS:
        raise ValueError("Installed plugin DLL set differs from the exact three approved instruments")
    if {name for name in files if name.startswith("data/projects/")} != ALLOWED_PROJECT_FILES:
        raise ValueError("Installed project/template set differs from the exact approved four files")
    sources = source_inputs(source_root, artwork)
    for relative in ALLOWED_PROJECT_FILES:
        if files[relative] != sources[relative]:
            raise ValueError(f"Installed starter/provenance differs from source: {relative}")
    evidence_root = Path(evidence_root)
    evidence = {name: file_record(evidence_root / name) for name in EVIDENCE_FILES}
    if evidence["candidate-inputs.json"] != sources["distribution/candidate-inputs.json"]:
        raise ValueError("Preserved candidate inputs differ from the exact source input")
    notices = inventory_tree(evidence_root / "notices")
    evidence.update({"notices/" + name: value for name, value in notices.items()})
    if not any(name.startswith("notices/qt/") for name in evidence) or not any(name.endswith("/copyright.txt") for name in evidence):
        raise ValueError("Exact Qt and vcpkg notice inputs are required")
    if _inventory_rows(evidence_root / "stage-inventory.json") != files:
        raise ValueError("Same-run stage inventory differs from actual stage")
    pe = _validate_pe_imports(release, evidence_root / "pe-imports.json", files)
    result = _load_json(evidence_root / "result.json", "native result")
    required_true = ("built", "tests_passed", "lifecycle_repeat_passed", "installed_stage", "native_render_smoke_passed", "native_render_error_exit_passed", "native_installed_starter_renders_passed")
    if result.get("source_commit") != source_commit or any(result.get(name) is not True for name in required_true):
        raise ValueError("Native result does not bind successful same-run build/render evidence")
    return dict(
        schemaVersion=1,
        sourceCommit=source_commit,
        files=files,
        sourceInputs=sources,
        evidenceInputs=evidence,
        runtime=dict(RUNTIME),
        peImports=file_record(evidence_root / "pe-imports.json"),
        buildProvenance=dict(
            qt="Exact Qt binary downloads and source-pinned module notice manifests/files are bound as evidence",
            vcpkg="Pinned vcpkg input, installed status, downloads and copied copyright files are bound",
            imports="Every staged PE is recorded; all three instrument DLLs import lmms.exe",
            inventoryIsLicenseClearance=False,
            correspondingSourceComplete=False,
        ),
    )


def validate_input_evidence(release, inventory, source_root, source_commit, evidence_root, artwork):
    recorded = _load_json(inventory, "same-run stage inventory")
    measured = create_input_inventory(release, source_root, source_commit, evidence_root, artwork)
    if recorded != measured:
        raise ValueError("Full stage inventory or source metadata differs from current source-bound inputs")
    return recorded


def create_manifest():
    identity = QUALIFICATION_IDENTITY
    package = ET.Element(f"{{{APPX_NS}}}Package", {"IgnorableNamespaces": "uap rescap"})
    ET.SubElement(
        package,
        f"{{{APPX_NS}}}Identity",
        {
            "Name": identity["packageName"],
            "Publisher": identity["publisher"],
            "Version": identity["version"],
            "ProcessorArchitecture": identity["architecture"],
        },
    )
    properties = ET.SubElement(package, f"{{{APPX_NS}}}Properties")
    for name, value in (
        ("DisplayName", "BeatQuay 1.0.0"),
        ("PublisherDisplayName", "Trieflow LLC"),
        ("Description", "BeatQuay qualification package"),
        ("Logo", r"Assets\StoreLogo.png"),
    ):
        ET.SubElement(properties, f"{{{APPX_NS}}}{name}").text = value
    resources = ET.SubElement(package, f"{{{APPX_NS}}}Resources")
    ET.SubElement(resources, f"{{{APPX_NS}}}Resource", {"Language": "en-US"})
    dependencies = ET.SubElement(package, f"{{{APPX_NS}}}Dependencies")
    ET.SubElement(
        dependencies,
        f"{{{APPX_NS}}}TargetDeviceFamily",
        {
            "Name": identity["deviceFamily"],
            "MinVersion": identity["minVersion"],
            "MaxVersionTested": identity["maxVersionTested"],
        },
    )
    applications = ET.SubElement(package, f"{{{APPX_NS}}}Applications")
    application = ET.SubElement(
        applications,
        f"{{{APPX_NS}}}Application",
        {
            "Id": identity["applicationId"],
            "Executable": identity["executable"],
            "EntryPoint": "Windows.FullTrustApplication",
        },
    )
    ET.SubElement(
        application,
        f"{{{UAP_NS}}}VisualElements",
        {
            "DisplayName": "BeatQuay 1.0.0",
            "Description": "BeatQuay qualification package",
            "BackgroundColor": "#142e38",
            "Square150x150Logo": r"Assets\Square150x150Logo.png",
            "Square44x44Logo": r"Assets\Square44x44Logo.png",
        },
    )
    capabilities = ET.SubElement(package, f"{{{APPX_NS}}}Capabilities")
    ET.SubElement(capabilities, f"{{{RESCAP_NS}}}Capability", {"Name": identity["capability"]})
    ET.indent(package, space="  ")
    return ET.tostring(package, encoding="utf-8", xml_declaration=True)


def _one(parent, tag, label):
    items = parent.findall(tag)
    if len(items) != 1:
        raise ValueError(f"Manifest requires exactly one {label}")
    return items[0]


def validate_manifest(data):
    try:
        root = ET.fromstring(data)
    except ET.ParseError as error:
        raise ValueError(f"Invalid manifest XML: {error}") from error
    if root.tag != f"{{{APPX_NS}}}Package" or root.attrib != {"IgnorableNamespaces": "uap rescap"}:
        raise ValueError("Invalid manifest package root")
    expected_children = [
        f"{{{APPX_NS}}}Identity",
        f"{{{APPX_NS}}}Properties",
        f"{{{APPX_NS}}}Resources",
        f"{{{APPX_NS}}}Dependencies",
        f"{{{APPX_NS}}}Applications",
        f"{{{APPX_NS}}}Capabilities",
    ]
    if [child.tag for child in root] != expected_children:
        raise ValueError("Unexpected manifest sections or extensions")
    identity_node = _one(root, f"{{{APPX_NS}}}Identity", "identity")
    identity = QUALIFICATION_IDENTITY
    if identity_node.attrib != {
        "Name": identity["packageName"],
        "Publisher": identity["publisher"],
        "Version": identity["version"],
        "ProcessorArchitecture": identity["architecture"],
    }:
        raise ValueError("Unexpected qualification identity")
    properties = _one(root, f"{{{APPX_NS}}}Properties", "properties")
    expected_properties = {
        "DisplayName": "BeatQuay 1.0.0",
        "PublisherDisplayName": "Trieflow LLC",
        "Description": "BeatQuay qualification package",
        "Logo": r"Assets\StoreLogo.png",
    }
    if (
        len(properties) != len(expected_properties)
        or {child.tag.rsplit("}", 1)[-1]: child.text for child in properties} != expected_properties
        or any(child.attrib or len(child) for child in properties)
    ):
        raise ValueError("Unexpected manifest properties")
    resources = _one(root, f"{{{APPX_NS}}}Resources", "resources")
    resource = _one(resources, f"{{{APPX_NS}}}Resource", "resource")
    if len(resources) != 1 or resource.attrib != {"Language": "en-US"} or len(resource):
        raise ValueError("Unexpected manifest resources")
    dependencies = _one(root, f"{{{APPX_NS}}}Dependencies", "dependencies")
    family = _one(dependencies, f"{{{APPX_NS}}}TargetDeviceFamily", "target device family")
    if (
        len(dependencies) != 1
        or family.attrib
        != {
            "Name": identity["deviceFamily"],
            "MinVersion": identity["minVersion"],
            "MaxVersionTested": identity["maxVersionTested"],
        }
        or len(family)
    ):
        raise ValueError("Unexpected target device family")
    applications = _one(root, f"{{{APPX_NS}}}Applications", "applications")
    application = _one(applications, f"{{{APPX_NS}}}Application", "application")
    if len(applications) != 1 or application.attrib != {
        "Id": identity["applicationId"],
        "Executable": identity["executable"],
        "EntryPoint": "Windows.FullTrustApplication",
    }:
        raise ValueError("Unexpected manifest executable/application")
    visual = _one(application, f"{{{UAP_NS}}}VisualElements", "visual elements")
    if (
        len(application) != 1
        or visual.attrib
        != {
            "DisplayName": "BeatQuay 1.0.0",
            "Description": "BeatQuay qualification package",
            "BackgroundColor": "#142e38",
            "Square150x150Logo": r"Assets\Square150x150Logo.png",
            "Square44x44Logo": r"Assets\Square44x44Logo.png",
        }
        or len(visual)
    ):
        raise ValueError("Unexpected manifest visual elements")
    capabilities = _one(root, f"{{{APPX_NS}}}Capabilities", "capabilities")
    capability = _one(capabilities, f"{{{RESCAP_NS}}}Capability", "capability")
    if len(capabilities) != 1 or capability.attrib != {"Name": identity["capability"]} or len(capability):
        raise ValueError("Unexpected manifest capabilities")
    return dict(identity)


def _png_chunks(data):
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("Artwork is not PNG")
    position = 8
    while position < len(data):
        if position + 12 > len(data):
            raise ValueError("Truncated PNG")
        length = struct.unpack(">I", data[position : position + 4])[0]
        kind = data[position + 4 : position + 8]
        body = data[position + 8 : position + 8 + length]
        crc = data[position + 8 + length : position + 12 + length]
        if len(body) != length or len(crc) != 4 or zlib.crc32(kind + body) & 0xFFFFFFFF != struct.unpack(">I", crc)[0]:
            raise ValueError("Invalid PNG chunk")
        position += 12 + length
        yield kind, body
        if kind == b"IEND":
            if position != len(data):
                raise ValueError("Trailing PNG data")
            return
    raise ValueError("PNG is missing IEND")


def png_dimensions(data):
    chunks = list(_png_chunks(data))
    if not chunks or chunks[0][0] != b"IHDR" or len(chunks[0][1]) != 13:
        raise ValueError("PNG is missing IHDR")
    return struct.unpack(">II", chunks[0][1][:8])


def _decode_rgba_png(data):
    chunks = list(_png_chunks(data))
    if chunks[0][0] != b"IHDR":
        raise ValueError("PNG is missing IHDR")
    width, height, depth, color, compression, filtering, interlace = struct.unpack(">IIBBBBB", chunks[0][1])
    if not (
        0 < width <= 4096
        and 0 < height <= 4096
        and depth == 8
        and color == 6
        and compression == filtering == interlace == 0
    ):
        raise ValueError("Artwork must be bounded noninterlaced 8-bit RGBA PNG")
    compressed = b"".join(body for kind, body in chunks if kind == b"IDAT")
    try:
        raw = zlib.decompress(compressed)
    except zlib.error as error:
        raise ValueError(f"Invalid compressed PNG: {error}") from error
    stride = width * 4
    if len(raw) != (stride + 1) * height:
        raise ValueError("Unexpected PNG data size")
    rows = []
    prior = bytearray(stride)
    for row_number in range(height):
        start = row_number * (stride + 1)
        filter_type = raw[start]
        encoded = raw[start + 1 : start + stride + 1]
        if filter_type > 4:
            raise ValueError("Unsupported PNG filter")
        row = bytearray(stride)
        for index, value in enumerate(encoded):
            left = row[index - 4] if index >= 4 else 0
            up = prior[index]
            upper_left = prior[index - 4] if index >= 4 else 0
            if filter_type == 0:
                prediction = 0
            elif filter_type == 1:
                prediction = left
            elif filter_type == 2:
                prediction = up
            elif filter_type == 3:
                prediction = (left + up) // 2
            else:
                candidate = left + up - upper_left
                dl, du, dul = abs(candidate - left), abs(candidate - up), abs(candidate - upper_left)
                prediction = left if dl <= du and dl <= dul else up if du <= dul else upper_left
            row[index] = (value + prediction) & 0xFF
        rows.append(bytes(row))
        prior = row
    return width, height, rows


def _chunk(kind, body):
    return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)


def resize_png(data, target):
    if target not in (44, 50, 150):
        raise ValueError("Unreviewed qualification asset size")
    width, height, rows = _decode_rgba_png(data)
    output = bytearray()
    for y in range(target):
        source_row = rows[min(height - 1, y * height // target)]
        output.append(0)
        for x in range(target):
            start = min(width - 1, x * width // target) * 4
            output.extend(source_row[start : start + 4])
    header = struct.pack(">IIBBBBB", target, target, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", header)
        + _chunk(b"IDAT", zlib.compress(bytes(output), 9))
        + _chunk(b"IEND", b"")
    )


def _write_new(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as output:
        output.write(data)
        output.flush()
        os.fsync(output.fileno())


def stage_release(release, artwork, stage, source_commit, inventory, evidence_root, source_root):
    release, artwork, stage = Path(release), Path(artwork), Path(stage)
    if not re.fullmatch(r"[0-9a-f]{40}", source_commit or ""):
        raise ValueError("Exact 40-character source commit is required")
    if os.path.lexists(stage):
        raise ValueError(f"Stage already exists and will not be replaced: {stage}")
    input_inventory = inventory_tree(release)
    for relative in REQUIRED_RELEASE_FILES:
        if relative not in input_inventory:
            raise ValueError(f"Required release file missing: {relative}")
    if "AppxManifest.xml" in input_inventory or any(name.casefold().startswith(("assets/", "licenses/")) for name in input_inventory):
        raise ValueError("Release collides with qualification-owned manifest/assets/licenses")
    input_record = validate_input_evidence(release, inventory, source_root, source_commit, evidence_root, artwork)
    with _regular_stream(artwork) as stream:
        artwork_data = stream.read()
    artwork_record = {"bytes": len(artwork_data), "sha256": hashlib.sha256(artwork_data).hexdigest()}
    assets = {}
    stage.mkdir(parents=False)
    try:
        for relative in sorted(input_inventory):
            target = stage / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            with _regular_stream(release / relative) as source, target.open("xb") as output:
                shutil.copyfileobj(source, output, 1024 * 1024)
        license_sources = {
            "licenses/BeatQuay/LICENSE.txt": Path(source_root) / "LICENSE.txt",
            "licenses/BeatQuay/AUTHORS.txt": Path(source_root) / "doc/AUTHORS",
            "licenses/pipeline/PIPELINE-MIT.txt": Path(source_root) / "cmake/msix/PIPELINE-MIT.txt",
            "licenses/pipeline/RETICLEQUAY-MIT.txt": Path(source_root) / "cmake/msix/RETICLEQUAY-MIT.txt",
            "licenses/templates/CC0-1.0.txt": Path(source_root) / "data/projects/templates/CC0-1.0.txt",
            "licenses/templates/BEATQUAY-PROVENANCE.md": Path(source_root) / "data/projects/templates/BEATQUAY-PROVENANCE.md",
        }
        for relative, source_path in license_sources.items():
            (stage / relative).parent.mkdir(parents=True, exist_ok=True)
            with _regular_stream(source_path) as source, (stage / relative).open("xb") as output:
                shutil.copyfileobj(source, output, 1024 * 1024)
        for relative in inventory_tree(Path(evidence_root) / "notices"):
            target = stage / "licenses/dependencies" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            with _regular_stream(Path(evidence_root) / "notices" / relative) as source, target.open("xb") as output:
                shutil.copyfileobj(source, output, 1024 * 1024)
        for name, size in (("StoreLogo.png", 50), ("Square44x44Logo.png", 44), ("Square150x150Logo.png", 150)):
            data = resize_png(artwork_data, size)
            relative = f"Assets/{name}"
            _write_new(stage / relative, data)
            assets[relative] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "pixels": [size, size]}
        manifest = create_manifest()
        validate_manifest(manifest)
        _write_new(stage / "AppxManifest.xml", manifest)
        if inventory_tree(release) != input_inventory:
            raise ValueError("Release input changed while staging")
        payload = inventory_tree(stage)
        for relative, record in input_inventory.items():
            if payload.get(relative) != record:
                raise ValueError(f"Staged release differs from input: {relative}")
        return {
            "schemaVersion": 1,
            "sourceCommit": source_commit,
            "qualificationIdentityOnly": True,
            "identity": dict(QUALIFICATION_IDENTITY),
            "releaseInput": input_inventory,
            "payload": payload,
            "inputInventory": file_record(inventory),
            "evidenceInputs": input_record["evidenceInputs"],
            "sourceInputs": input_record["sourceInputs"],
            "runtime": dict(RUNTIME),
            "buildProvenance": input_record["buildProvenance"],
            "peImports": input_record["peImports"],
            "artworkSource": artwork_record,
            "assets": assets,
            "licenseClearanceClaimed": False,
            "correspondingSourceComplete": False,
            "publicRelease": False,
            "signed": False,
            "installationQualificationPassed": False,
        }
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def _decode_opc_path(value):
    # MakeAppx stores OPC URI names in the ZIP, e.g. libc++.dll becomes
    # libc%2B%2B.dll. Decode once before payload/hash and alias comparison.
    # Escaped separators cannot change the archive's directory hierarchy.
    if re.search(r"%(?![0-9A-Fa-f]{2})|%(?:2f|5c)", value, re.I):
        raise ValueError(f"Malformed or hierarchy-changing OPC path: {value!r}")
    return _checked_path(unquote(value, encoding="utf-8", errors="strict"))


def verify_msix(path, expected):
    if not isinstance(expected, dict) or "AppxManifest.xml" not in expected:
        raise ValueError("Invalid expected package payload")
    allowed_directories = {
        str(parent)
        for name in set(expected) | PACKAGE_METADATA
        for parent in PurePosixPath(name).parents
        if str(parent) != "."
    }
    seen = {}
    actual = {}
    metadata = set()
    directories = set()
    manifest_data = None
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            name = _decode_opc_path(info.filename.rstrip("/") if info.is_dir() else info.filename)
            mode = info.external_attr >> 16
            if info.flag_bits & 1:
                raise ValueError(f"Encrypted package entry: {info.filename}")
            if info.is_dir():
                key = unicodedata.normalize("NFC", name).casefold()
                if stat.S_IFMT(mode) not in (0, stat.S_IFDIR) or name not in allowed_directories or key in directories:
                    raise ValueError(f"Unexpected/special package directory: {info.filename}")
                directories.add(key)
                continue
            _register_path(name, seen)
            if stat.S_IFMT(mode) not in (0, stat.S_IFREG):
                raise ValueError(f"Special package entry: {name}")
            if name in PACKAGE_METADATA:
                if info.file_size > 32 * 1024 * 1024:
                    raise ValueError(f"Oversized package metadata: {name}")
                metadata.add(name)
                continue
            record = expected.get(name)
            if not record or info.file_size != record["bytes"]:
                raise ValueError(f"Unexpected package entry or size: {name}")
            with archive.open(info) as stream:
                measured = _digest(stream)
            if measured != record:
                raise ValueError(f"Package hash mismatch: {name}")
            actual[name] = measured
            if name == "AppxManifest.xml":
                manifest_data = archive.read(info)
    if set(actual) != set(expected):
        raise ValueError("Package payload is missing expected files")
    if not {"[Content_Types].xml", "AppxBlockMap.xml"}.issubset(metadata):
        raise ValueError("Package metadata is incomplete")
    validate_manifest(manifest_data)
    with _regular_stream(path) as stream:
        package = _digest(stream)
    return {"verifiedPayloadFiles": len(actual), "metadata": sorted(metadata), "package": package}


def verify_unpacked(root, expected):
    actual = inventory_tree(root)
    for metadata in PACKAGE_METADATA:
        actual.pop(metadata, None)
    if actual != expected:
        raise ValueError("SDK-unpacked payload differs from staged payload")
    validate_manifest((Path(root) / "AppxManifest.xml").read_bytes())
    return {"verifiedPayloadFiles": len(actual)}


def verify_installed(root, expected):
    actual = inventory_tree(root)
    for metadata in PACKAGE_METADATA | {"AppxSignature.p7x"}:
        actual.pop(metadata, None)
    if actual != expected:
        raise ValueError("Installed package has missing, altered or extra payload files")
    validate_manifest((Path(root) / "AppxManifest.xml").read_bytes())
    return {"verifiedPayloadFiles": len(actual)}


def verify_record_inputs(package, record_path, release, artwork, source_commit, inventory, evidence_root, source_root):
    record = _load_json(record_path, "qualification record")
    # Recreate the package boundary from current source/stage/receipt rather than
    # trusting a coherent replacement of the package and its own recorded hashes.
    with tempfile.TemporaryDirectory(prefix="beatquay-record-") as temporary:
        expected = stage_release(
            release, artwork, Path(temporary).resolve() / "stage", source_commit, inventory, evidence_root, source_root
        )
    if any(record.get(key) != value for key, value in expected.items()):
        raise ValueError("Package record no longer matches source-bound qualification inputs")
    actual = verify_msix(package, expected["payload"])
    if record.get("containerVerification") != actual:
        raise ValueError("Package record differs from independent container verification")
    unpacked = record.get("unpackedVerification")
    if (
        not isinstance(unpacked, dict)
        or set(unpacked) != {"verifiedPayloadFiles"}
        or type(unpacked["verifiedPayloadFiles"]) is not int
        or unpacked["verifiedPayloadFiles"] != len(expected["payload"])
    ):
        raise ValueError("Package record lacks exact source-bound SDK unpack evidence")
    return True


def _tool_record(path, sdk_version):
    path = Path(path)
    if not path.is_absolute() or path.name.casefold() != "makeappx.exe":
        raise ValueError("Absolute MakeAppx.exe path is required")
    if sdk_version != "10.0.26100.0":
        raise ValueError("Exact Windows SDK version is required")
    normalized = [part.casefold() for part in path.parts]
    expected_tail = ["windows kits", "10", "bin", sdk_version.casefold(), "x64", "makeappx.exe"]
    if normalized[-6:] != expected_tail:
        raise ValueError("MakeAppx SDK path must end with Windows Kits/10/bin/<exact-version>/x64/makeappx.exe")
    with _regular_stream(path) as stream:
        record = _digest(stream)
    record.update({"path": str(path), "sdkVersion": sdk_version})
    return record


def _run(command):
    subprocess.run(command, check=True, shell=False, timeout=900)


def build_qualification(
    release, artwork, source_commit, makeappx, sdk_version, output, inventory, evidence_root, source_root, runner=_run
):
    output = Path(output).absolute()
    if os.path.lexists(output):
        raise ValueError(f"Output already exists and will not be replaced: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".beatquay-msix-", dir=output.parent))
    try:
        tool = _tool_record(makeappx, sdk_version)
        stage = temporary / "stage"
        record = stage_release(release, artwork, stage, source_commit, inventory, evidence_root, source_root)
        package = temporary / "BeatQuay.Qualification_1.0.0.0_x64.msix"
        unpacked = temporary / "unpacked"
        commands = [
            [str(makeappx), "pack", "/d", str(stage), "/p", str(package), "/v", "/h", "SHA256"],
            [str(makeappx), "unpack", "/p", str(package), "/d", str(unpacked), "/v"],
        ]
        for command in commands:
            if _tool_record(makeappx, sdk_version) != tool:
                raise ValueError("MakeAppx changed during qualification build")
            runner(command)
            if inventory_tree(stage) != record["payload"]:
                raise ValueError("Package stage changed during SDK execution")
        container = verify_msix(package, record["payload"])
        unpacked_result = verify_unpacked(unpacked, record["payload"])
        if _tool_record(makeappx, sdk_version) != tool:
            raise ValueError("MakeAppx changed during qualification build")
        record.update(
            {
                "makeAppx": tool,
                "containerVerification": container,
                "unpackedVerification": unpacked_result,
            }
        )
        output.mkdir()
        try:
            with _regular_stream(package) as source, (output / package.name).open("xb") as destination:
                shutil.copyfileobj(source, destination, 1024 * 1024)
            _write_new(output / "package-record.json", _canonical_json(record))
        except Exception:
            # This directory was created by this invocation; retain it as explicit incomplete evidence.
            _write_new(output / "INCOMPLETE.txt", b"Packaging output is incomplete and must not be consumed.\n")
            raise
        shutil.rmtree(temporary)
        return output
    except Exception as error:
        raise ValueError(f"Qualification packaging failed; evidence retained at {temporary}: {error}") from error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--artwork", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--makeappx", type=Path, required=True)
    parser.add_argument("--sdk-version", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != "win32" or os.environ.get("CI") != "true":
        parser.error("Qualification package builds require disposable Windows CI")
    try:
        actual = subprocess.run(
            ["git", "-C", str(args.source_root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout.strip()
        if actual != args.source_commit:
            raise ValueError(f"Source commit mismatch: expected {args.source_commit}, found {actual}")
        dirty = subprocess.run(
            ["git", "-C", str(args.source_root), "status", "--porcelain", "--untracked-files=all"],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout.strip()
        if dirty:
            raise ValueError("Source checkout must be clean so the recorded commit identifies every packaging input")
        print(
            build_qualification(
                args.release,
                args.artwork,
                args.source_commit,
                args.makeappx,
                args.sdk_version,
                args.output,
                args.inventory,
                args.evidence_root,
                args.source_root,
            )
        )
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        parser.exit(1, str(error) + "\n")


if __name__ == "__main__":
    main()
