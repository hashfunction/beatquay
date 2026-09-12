"""Independently validate selected Microsoft runtime originals against the stage."""
import hashlib
import json
from pathlib import Path, PureWindowsPath
import re

VC_NAMES = {'concrt140.dll', 'msvcp140.dll', 'msvcp140_1.dll', 'msvcp140_2.dll',
            'msvcp140_atomic_wait.dll', 'msvcp140_codecvt_ids.dll', 'vcruntime140.dll', 'vcruntime140_1.dll'}
TERMS = {
    'visualStudio': 'https://learn.microsoft.com/en-us/visualstudio/releases/2022/redistribution',
    'visualStudioLicense': 'https://visualstudio.microsoft.com/license-terms/vs2022-ga-proenterprise/',
    'universalCrt': 'https://learn.microsoft.com/en-us/cpp/windows/universal-crt-deployment?view=msvc-170',
}


def microsoft_name(name):
    return name.lower() in VC_NAMES or name.lower() == 'ucrtbase.dll' or bool(
        re.fullmatch(r'api-ms-win-[a-z0-9-]+\.dll', name, re.I))


def windows_path(value):
    if not isinstance(value, str) or any(x in value for x in ('\0', '..', ';')):
        raise ValueError('Invalid original runtime path')
    path = PureWindowsPath(value)
    if not path.is_absolute() or path.drive.startswith('\\'):
        raise ValueError('Runtime origin must use an absolute local Windows path')
    return path


def validate_metadata(record, selector, selector_sha256, files, source_commit):
    if (record.get('schemaVersion') != 1 or record.get('sourceCommit') != source_commit
            or record.get('selectionSha256') != selector_sha256
            or record.get('licenseClearanceClaimed') is not False or record.get('redistributionTerms') != TERMS
            or selector.get('schemaVersion') != 1 or selector.get('architecture') != 'x64'
            or selector.get('buildType') != 'RelWithDebInfo'):
        raise ValueError('Microsoft runtime origin source/configuration/terms mismatch')
    redist = windows_path(selector['msvcRedistRoot'])
    kits = windows_path(selector['windowsKitsRoot'])
    if not re.search(r'\\VC\\Redist\\MSVC\\[0-9.]+$', str(redist), re.I):
        raise ValueError('Unexpected Microsoft release redist root')
    if not str(kits).lower().endswith('\\windows kits\\10'):
        raise ValueError('Unexpected Windows SDK root')
    selected = selector.get('sourcePaths')
    if not isinstance(selected, list) or not selected: raise ValueError('Missing original runtime selection')
    by_name = {}
    for value in selected:
        path = windows_path(value); name = path.name.lower()
        if name in by_name or not microsoft_name(name): raise ValueError('Duplicate or unreviewed selected runtime')
        if name in VC_NAMES:
            if path.parent != redist / 'x64/Microsoft.VC143.CRT':
                raise ValueError('Microsoft runtime is outside the exact release CRT directory')
        else:
            try: relative = path.relative_to(kits).as_posix()
            except ValueError: raise ValueError('UCRT origin is outside the selected SDK')
            if not re.fullmatch(r'Redist/(?:10\.[0-9.]+/)?ucrt/DLLs/x64/[^/]+\.dll', relative, re.I):
                raise ValueError('UCRT origin is outside the release x64 SDK directory')
        by_name[name] = str(path)
    expected = {name.lower(): (name, value) for name, value in files.items()
                if microsoft_name(PureWindowsPath(name).name)}
    if any('/' in name or '\\' in name for name in expected) or set(expected) != set(by_name):
        raise ValueError('Microsoft origin selection does not cover the exact staged runtime set')
    entries = record.get('files')
    if not isinstance(entries, list): raise ValueError('Missing Microsoft origin file observations')
    seen = set()
    for entry in entries:
        name = entry.get('path', '').lower()
        if name in seen or name not in expected or str(windows_path(entry.get('sourcePath'))) != by_name[name]:
            raise ValueError('Unexpected or changed Microsoft runtime origin')
        seen.add(name); measured = expected[name][1]
        if (type(entry.get('bytes')) is not int or entry['bytes'] <= 0 or entry['bytes'] != measured['bytes']
                or entry.get('sha256') != measured['sha256']):
            raise ValueError('Microsoft original/stage hash or size mismatch')
        # Version/signature properties are observations, including explicit empty
        # values when an SDK forwarder lacks resources or a catalog is unavailable.
        if any(not isinstance(entry.get(key), str) for key in
               ('fileVersion', 'productVersion', 'companyName', 'signatureStatus', 'signerSubject')):
            raise ValueError('Missing Microsoft file version/signature observations')
    if seen != set(expected): raise ValueError('Incomplete Microsoft original observations')
    return entries


def verify(evidence_root, stage_files, source_commit, file_record):
    root = Path(evidence_root)
    selector_path = root / 'ms-runtime-selection.json'; record_path = root / 'ms-runtime-origins.json'
    selector = json.loads(selector_path.read_text(encoding='utf-8-sig'))
    record = json.loads(record_path.read_text(encoding='utf-8-sig'))
    selected_hash = file_record(selector_path)['sha256']
    entries = validate_metadata(record, selector, selected_hash, stage_files, source_commit)
    if file_record(selector['discoveryModule'])['sha256'] != selector['discoveryModuleSha256']:
        raise ValueError('Actual CMake runtime discovery module changed')
    for entry in entries:
        actual = file_record(entry['sourcePath'])
        if actual != {'bytes': entry['bytes'], 'sha256': entry['sha256']}:
            raise ValueError('Independent original runtime hash verification failed')
    if file_record(selector_path)['sha256'] != selected_hash:
        raise ValueError('Original runtime selector changed during independent verification')
    return record
