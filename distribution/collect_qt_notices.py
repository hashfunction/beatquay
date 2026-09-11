#!/usr/bin/env python3
"""Validate and copy the exact source-pinned Qt notice bundle."""

import argparse
import hashlib
import json
import os
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
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(part in ("", ".", "..") for part in path.parts):
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
            if path.parts[0] not in ("LICENSES", "REUSE.toml") or (path.parts[0] == "REUSE.toml" and len(path.parts) != 1):
                raise ValueError(f"unexpected Qt notice input: {name}/{relative}")
            if type(record) is not dict or set(record) != FILE_KEYS or type(record["bytes"]) is not int or record["bytes"] <= 0:
                raise ValueError(f"malformed Qt notice record: {name}/{relative}")
            if not re.fullmatch(r"[0-9a-f]{64}", record["sha256"] or "") or not re.fullmatch(r"[0-9a-f]{40}", record["gitBlob"] or ""):
                raise ValueError(f"malformed Qt notice digest: {name}/{relative}")
            source = bundle.joinpath(name, *path.parts)
            if source.is_symlink() or not source.is_file():
                raise ValueError(f"Qt notice file is absent or not regular: {name}/{relative}")
            data = source.read_bytes()
            if len(data) != record["bytes"] or digest(data) != record["sha256"]:
                raise ValueError(f"Qt notice hash mismatch: {name}/{relative}")
            expected_files[f"{name}/{relative}"] = data
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
