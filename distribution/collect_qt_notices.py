#!/usr/bin/env python3
"""Validate and copy the exact source-pinned Qt notice bundle."""

import argparse
import hashlib
import json
import os
import posixpath
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile


HERE = Path(__file__).resolve().parent
EXPECTED_KEYS = {
    "schemaVersion", "version", "authoritativeHost", "retrievedAt",
    "correspondingSourceComplete", "scope", "modules",
}
MODULE_KEYS = {"name", "role", "repository", "tag", "tagObject", "commit", "files"}
FILE_KEYS = {"bytes", "sha256", "gitBlob"}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def checked_relative(value):
    if not isinstance(value, str) or not value or "\\" in value or ":" in value or re.search(r'[\x00-\x1f\x7f]', value):
        raise ValueError(f"unsafe notice path: {value}")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ("", ".", "..") for part in value.split('/')):
        raise ValueError(f"unsafe notice path: {value}")
    return path


def load_and_validate(bundle_root, version, requested_modules):
    bundle = Path(bundle_root) / version
    manifest_path = bundle / "manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError("exact Qt notice manifest is absent")
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    if set(manifest) != EXPECTED_KEYS or manifest["schemaVersion"] != 1 or manifest["version"] != version:
        raise ValueError("Qt notice manifest schema/version mismatch")
    if manifest["authoritativeHost"] != "https://code.qt.io" or manifest["correspondingSourceComplete"] is not False:
        raise ValueError("Qt notice provenance/closure flags are invalid")
    if len(requested_modules) != len(set(requested_modules)):
        raise ValueError("duplicate Qt module request")

    expected_files = {"manifest.json": manifest_bytes}
    modules = manifest["modules"]
    if type(modules) is not list or not modules:
        raise ValueError("Qt notice modules are absent")
    names = []
    for module in modules:
        if type(module) is not dict or set(module) != MODULE_KEYS:
            raise ValueError("Qt notice module schema mismatch")
        name = module["name"]
        if not re.fullmatch(r"qt[a-z0-9]+", name or "") or module["role"] not in ("runtime", "build-only"):
            raise ValueError("Qt notice module identity is invalid")
        if module["repository"] != f"https://code.qt.io/qt/{name}.git" or module["tag"] != "v" + version:
            raise ValueError("Qt notice module source does not match its version")
        if not re.fullmatch(r"[0-9a-f]{40}", module["tagObject"] or "") or not re.fullmatch(r"[0-9a-f]{40}", module["commit"] or ""):
            raise ValueError("Qt notice module revision is invalid")
        names.append(name)
        files = module["files"]
        if type(files) is not dict or not files:
            raise ValueError("Qt notice module file inventory is absent")
        for relative, record in files.items():
            path = checked_relative(relative)
            if not (path.parts[0] == "LICENSES" or relative == "REUSE.toml"
                    or path.name == "qt_attribution.json"
                    or re.search(r'(^|[.\-_])(LICENSE|LICENCE|COPYING|COPYRIGHT|AUTHORS|NOTICE)([.\-_]|$)', path.name, re.I)
                    or path.name == 'LGPL-2.1-or-later.txt'
                    or relative in ('src/gui/CMakeLists.txt', 'src/corelib/CMakeLists.txt', 'src/plugins/platforms/windows/CMakeLists.txt')):
                raise ValueError(f"unexpected Qt notice input: {name}/{relative}")
            if type(record) is not dict or set(record) != FILE_KEYS or type(record["bytes"]) is not int or record["bytes"] <= 0:
                raise ValueError(f"malformed Qt notice record: {name}/{relative}")
            if not re.fullmatch(r"[0-9a-f]{64}", record["sha256"] or "") or not re.fullmatch(r"[0-9a-f]{40}", record["gitBlob"] or ""):
                raise ValueError(f"malformed Qt notice digest: {name}/{relative}")
            source = bundle.joinpath(name, *path.parts)
            for parent in (source.parent, *source.parent.parents):
                if parent.is_symlink():
                    raise ValueError(f"Qt notice parent is a symlink: {name}/{relative}")
                if parent == bundle.parent: break
            if source.is_symlink() or not source.is_file():
                raise ValueError(f"Qt notice file is absent or not regular: {name}/{relative}")
            data = source.read_bytes()
            if len(data) != record["bytes"] or digest(data) != record["sha256"]:
                raise ValueError(f"Qt notice hash mismatch: {name}/{relative}")
            if hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() != record['gitBlob']:
                raise ValueError(f"Qt notice Git blob mismatch: {name}/{relative}")
            expected_files[f"{name}/{relative}"] = data
        attributions = [relative for relative in files if relative.endswith('/qt_attribution.json')]
        if len(attributions) != {'qtbase': 76, 'qtsvg': 1, 'qttools': 2}.get(name):
            raise ValueError(f"Qt original attribution inventory is incomplete: {name}")
        for relative in attributions:
            # Five original upstream JSON files contain literal control characters.
            # Parse as data for reference validation; preserve their exact bytes.
            raw = expected_files[f'{name}/{relative}']
            entries = json.loads(raw, strict=False)
            entries = entries if isinstance(entries, list) else [entries]
            for entry in entries:
                if not isinstance(entry, dict) or not isinstance(entry.get('Id'), str):
                    raise ValueError('Invalid original Qt attribution data')
                for key in ('LicenseFile', 'LicenseFiles', 'CopyrightFile'):
                    values = entry.get(key, [])
                    values = [values] if isinstance(values, str) else values
                    if not isinstance(values, list): raise ValueError('Invalid attribution file reference')
                    for value in values:
                        if not isinstance(value, str) or value.startswith('/') or '\\' in value or ':' in value:
                            raise ValueError('Unsafe attribution file reference')
                        target = str(checked_relative(posixpath.normpath(posixpath.join(posixpath.dirname(relative), value))))
                        if target not in files:
                            raise ValueError(f"Missing referenced Qt original notice: {name}/{target}")
    if len(names) != len(set(names)) or set(names) != set(requested_modules):
        raise ValueError("requested Qt modules differ from the exact notice bundle")

    actual_files = {
        path.relative_to(bundle).as_posix()
        for path in bundle.rglob("*")
        if path.is_file() or path.is_symlink()
    }
    if actual_files != set(expected_files):
        raise ValueError("Qt notice bundle contains missing or extra inputs")
    return expected_files


def collect(bundle_root, version, modules, output):
    output = Path(output)
    if os.path.lexists(output):
        raise FileExistsError(f"Qt notice output exists and will not be replaced: {output}")
    files = load_and_validate(bundle_root, version, modules)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".qt-notices-", dir=output.parent))
    try:
        for relative, data in files.items():
            destination = temporary.joinpath(*PurePosixPath(relative).parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("xb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        temporary.replace(output)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-root", type=Path, default=HERE / "qt-notices")
    parser.add_argument("--version", required=True)
    parser.add_argument("--module", action="append", required=True, dest="modules")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        collect(args.bundle_root, args.version, args.modules, args.output)
    except (FileExistsError, OSError, ValueError, json.JSONDecodeError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
