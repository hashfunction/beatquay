"""Verify the reviewed native sources/notices and prepare source-bound evidence.

The 17 archive URLs are a publication plan. This tool does not publish assets or
promote local source possession into a public corresponding-source claim.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from collect_qt_notices import load_and_validate as qt_originals

HERE = Path(__file__).resolve().parent
OWNERS = {'vcpkg', 'qtbase', 'qtsvg', 'qttools', 'hiir', 'ringbuffer', 'fftw3', 'libogg',
          'libflac', 'libsamplerate', 'libsndfile', 'mpg123', 'mp3lame', 'opus', 'libvorbis', 'portaudio', 'zlib'}
REPOSITORY = 'https://github.com/hashfunction/beatquay'
DELIVERY_FILES = ('notice-manifest.json', 'source-release.json', 'COMBINED-LICENSE.md', 'GPL-3.0.txt', 'SOURCE.md')
COPYRIGHT_FILES = {'fftw3':'COPYING','libogg':'COPYING','libflac':'COPYING.Xiph','libsamplerate':'COPYING',
    'libsndfile':'COPYING','mpg123':'COPYING','mp3lame':'COPYING','opus':'COPYING','libvorbis':'COPYING',
    'portaudio':'LICENSE.txt','zlib':'LICENSE'}


def read_regular(path):
    path = Path(path)
    for ancestor in (path, *path.parents):
        if ancestor.is_symlink() or getattr(ancestor.lstat(), 'st_file_attributes', 0) & 0x400:
            raise ValueError('Native source/notice reparse point refused')
    if not path.is_file(): raise ValueError('Native source/notice must be a regular file')
    return path.read_bytes()


def record(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def relative(value):
    if (not isinstance(value, str) or not value or value.startswith('/') or '\\' in value or ':' in value
            or any(x in ('', '.', '..') for x in value.split('/')) or re.search(r'[\x00-\x1f\x7f]', value)):
        raise ValueError('Unsafe native source/notice relative path')
    return value


def load_release(path):
    data = json.loads(read_regular(path))
    if (data.get('schemaVersion') != 1 or data.get('product') != 'BeatSprig' or data.get('version') != '1.0.1'
            or data.get('repository') != REPOSITORY or data.get('proposedTag') != 'beatsprig-native-source-1.0.1'
            or data.get('deliveryStatus') != 'prepared-unpublished' or data.get('correspondingSourceComplete') is not False):
        raise ValueError('Native source release identity/preparation state mismatch')
    files = data.get('archives', [])
    if (len(files) != 17 or {x.get('owner') for x in files} != OWNERS
            or len({x.get('file') for x in files}) != 17):
        raise ValueError('Native source archives must cover the exact 17 owners once')
    for item in files:
        name = relative(item['file'])
        if '/' in name or not name.endswith(('.tar.gz', '.tar.bz2')):
            raise ValueError('Unexpected native source archive name')
        if (type(item.get('bytes')) is not int or item['bytes'] <= 0
                or not re.fullmatch('[0-9a-f]{64}', item.get('sha256', ''))
                or not re.fullmatch('[0-9a-f]{128}', item.get('sha512', ''))
                or item.get('proposedDownloadUrl') != REPOSITORY + '/releases/download/' + data['proposedTag'] + '/' + name):
            raise ValueError('Native source archive digest/length/URL mismatch')
        if item.get('recipeSha512', item['sha512']) != item['sha512']:
            raise ValueError('Native source SHA512 differs from original recipe')
        if any(not re.fullmatch('[0-9a-f]{40}', item[key]) for key in ('commit','tree') if key in item):
            raise ValueError('Native source immutable revision is malformed')
        stage = item.get('stageFiles')
        if not isinstance(stage, list) or len(stage) != len(set(stage)):
            raise ValueError('Native source runtime mapping is malformed')
        for name in stage:
            if relative(name) != name.lower() or not name.endswith(('.dll', '.exe')):
                raise ValueError('Native source runtime mapping is malformed')
    return data


def verify_archives(release, directory, owners=None):
    checked = []
    for item in release['archives']:
        if owners is not None and item['owner'] not in owners: continue
        path = Path(directory) / item['file']
        for ancestor in (path, *path.parents):
            if ancestor.is_symlink() or getattr(ancestor.lstat(), 'st_file_attributes', 0) & 0x400:
                raise ValueError('Source archive reparse point refused')
        if not path.is_file(): raise ValueError('Original source archive is absent')
        sha256 = hashlib.sha256(); sha512 = hashlib.sha512(); size = 0
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                size += len(chunk); sha256.update(chunk); sha512.update(chunk)
                if size > item['bytes']: raise ValueError('Source archive exceeds its exact size')
        if size != item['bytes'] or sha256.hexdigest() != item['sha256'] or sha512.hexdigest() != item['sha512']:
            raise ValueError('Source archive hash/size differs: ' + item['owner'])
        checked.append({'owner': item['owner'], 'file': item['file'], 'bytes': size,
                        'sha256': sha256.hexdigest(), 'sha512': sha512.hexdigest()})
    return checked


def stage_owners(release, files, verified_microsoft):
    """Every staged PE needs a mapped source or an independently proved redist."""
    mapping = {name: ['application'] for name in ('beatsprig.exe', 'plugins/audiofileprocessor.dll',
               'plugins/kicker.dll', 'plugins/tripleoscillator.dll')}
    for item in release['archives']:
        for name in item['stageFiles']: mapping.setdefault(name, []).append(item['owner'])
    for item in verified_microsoft:
        name = relative(item['path']).lower()
        if name in mapping: raise ValueError('Conflicting native source owner and Microsoft origin')
        mapping[name] = ['microsoft-verified-redist']
    result = {}
    for name in files:
        if not name.lower().endswith(('.dll', '.exe')): continue
        if name.lower() not in mapping: raise ValueError('Unreviewed staged PE source owner: ' + name)
        result[name] = sorted(mapping[name.lower()])
    return result


def original_notices(root):
    root = Path(root)
    manifest = json.loads(read_regular(root / 'notice-manifest.json'))
    inventory = manifest.get('originalFiles')
    if manifest.get('schemaVersion') != 1 or not isinstance(inventory, dict) or len(inventory) != 51:
        raise ValueError('Original native notice inventory is incomplete')
    result = {}
    for name, item in inventory.items():
        name = relative(name)
        if not name.startswith('notices/'): raise ValueError('Notice is outside original notice directory')
        data = read_regular(root / name)
        if record(data) != {key: item[key] for key in ('bytes', 'sha256')}:
            raise ValueError('Original native notice hash mismatch: ' + name)
        result[name] = data
    actual = {p.relative_to(root).as_posix() for p in (root / 'notices').rglob('*') if p.is_file() or p.is_symlink()}
    if actual != set(result): raise ValueError('Missing or unexpected original native notice')
    for name in DELIVERY_FILES: result[name] = read_regular(root / name)
    if result['GPL-3.0.txt'] != result['notices/app-submodules/ringbuffer/LICENSE.txt']:
        raise ValueError('Combined GPLv3 legal text differs from preserved original')
    return result


def validate_current_inputs(source, evidence, release):
    source = Path(source); evidence = Path(evidence)
    lock = json.loads(read_regular(source / 'distribution/candidate-inputs.json'))
    qnotice = json.loads(read_regular(source / 'distribution/qt-notices/6.11.2/manifest.json'))
    owners = {x['owner']: x for x in release['archives']}
    if lock['vcpkg']['commit'] != owners['vcpkg']['commit'] or lock['qt']['version'] != '6.11.2':
        raise ValueError('Current dependency pins differ from source release')
    if set(lock['qt']['archives']) != {'qtbase','qtsvg','qttools'} or {x['name'] for x in qnotice['modules']} != {'qtbase','qtsvg','qttools'}:
        raise ValueError('Current Qt module set differs from source release')
    for module in qnotice['modules']:
        if module['commit'] != owners[module['name']]['commit']:
            raise ValueError('Current Qt notice/source revision differs')
    for module in ('hiir', 'ringbuffer'):
        archive = owners[module]
        actual = [x for x in lock['submodules'] if x['path'] == archive['modulePath']]
        if len(actual) != 1 or actual[0]['commit'] != archive['commit'] or actual[0]['tree'] != archive['tree']:
            raise ValueError('Current compiled module source differs')
    def downloads(name):
        rows = json.loads(read_regular(evidence / name))
        if len({x['file'] for x in rows}) != len(rows): raise ValueError('Duplicate downloaded source/binary evidence')
        return {x['file']: {'bytes': x['bytes'], 'sha256': x['sha256'].lower()} for x in rows}
    qt = downloads('qt-downloads.json')
    expected_qt = {x['file']: {'bytes': x['bytes'], 'sha256': x['sha256'].lower()} for x in release['qtBinaryInputs']}
    if qt != expected_qt: raise ValueError('Actual Qt binary inputs differ from reviewed source mapping')
    actual_sources = downloads('dependency-downloads.json')
    for archive in release['archives']:
        if 'recipeSha512' in archive and actual_sources.get(archive['file']) != {k: archive[k] for k in ('bytes', 'sha256')}:
            raise ValueError('Actual vcpkg source download differs from source release')


def validate_build_result(evidence, source_commit):
    result = json.loads(read_regular(Path(evidence) / 'result.json'))
    if result.get('source_commit') != source_commit or result.get('built') is not True:
        raise ValueError('Source collection differs from the actual successful native build')


def collect(source, evidence, downloads, output, source_commit):
    source = Path(source); evidence = Path(evidence); output = Path(output)
    if not re.fullmatch('[0-9a-f]{40}', source_commit): raise ValueError('Exact current public source commit required')
    if os.path.lexists(output): raise ValueError('Native notice output exists')
    validate_build_result(evidence, source_commit)
    root = source / 'distribution/native-source'
    release = load_release(root / 'source-release.json')
    files = original_notices(root)
    validate_current_inputs(source, evidence, release)
    owners = {x['owner'] for x in release['archives'] if 'recipeSha512' in x}
    checked = verify_archives(release, downloads, owners)
    build = {'schemaVersion': 1, 'sourceCommit': source_commit,
        'applicationSourceUrl': REPOSITORY + '/tree/' + source_commit,
        'sourceReleaseManifest': record(read_regular(root / 'source-release.json')),
        'originalNoticeManifest': record(read_regular(root / 'notice-manifest.json')),
        'preparedArchiveCount': 17, 'actualVcpkgSourceArchives': checked,
        'qtBinaryInputsBound': True, 'compiledModulePinsBound': True,
        'publicationVerified': False, 'correspondingSourceComplete': False, 'licenseClearanceClaimed': False}
    files['build-source.json'] = (json.dumps(build, indent=2, sort_keys=True) + '\n').encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix='.native-notices-', dir=output.parent))
    try:
        for name, data in files.items():
            dest = temporary / name; dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open('xb') as stream: stream.write(data)
        temporary.replace(output)
    except Exception:
        shutil.rmtree(temporary); raise
    return build


def verify_evidence(source, evidence, source_commit):
    """Reread original notices and bind the collection to current build inputs."""
    source = Path(source); evidence = Path(evidence)
    validate_build_result(evidence, source_commit)
    root = source / 'distribution/native-source'; copied = evidence / 'notices/native'
    release = load_release(root / 'source-release.json')
    validate_current_inputs(source, evidence, release)
    originals = original_notices(root)
    for name, data in originals.items():
        if read_regular(copied / name) != data: raise ValueError('Copied original native notice differs from source')
    actual = {p.relative_to(copied).as_posix() for p in copied.rglob('*') if p.is_file() or p.is_symlink()}
    if actual != set(originals) | {'build-source.json'}: raise ValueError('Native notice/source evidence set is incomplete or unexpected')
    expected_qt = qt_originals(source / 'distribution/qt-notices', '6.11.2', ['qtbase','qtsvg','qttools'])
    qt_root = evidence / 'notices/qt'
    for name, data in expected_qt.items():
        if read_regular(qt_root / name) != data: raise ValueError('Copied Qt original notice differs from source')
    if {p.relative_to(qt_root).as_posix() for p in qt_root.rglob('*') if p.is_file() or p.is_symlink()} != set(expected_qt):
        raise ValueError('Copied Qt original notice set differs from source')
    for port, name in COPYRIGHT_FILES.items():
        if read_regular(evidence / 'notices/vcpkg' / port / 'copyright.txt') != originals['notices/vcpkg/' + port + '/' + name]:
            raise ValueError('Actual copied vcpkg copyright differs from its verified original')
    build = json.loads(read_regular(copied / 'build-source.json'))
    expected_archives = [{k: x[k] for k in ('owner', 'file', 'bytes', 'sha256', 'sha512')}
                         for x in release['archives'] if 'recipeSha512' in x]
    if (build.get('schemaVersion') != 1 or build.get('sourceCommit') != source_commit
            or build.get('applicationSourceUrl') != REPOSITORY + '/tree/' + source_commit
            or build.get('sourceReleaseManifest') != record(read_regular(root / 'source-release.json'))
            or build.get('originalNoticeManifest') != record(read_regular(root / 'notice-manifest.json'))
            or build.get('actualVcpkgSourceArchives') != expected_archives
            or build.get('preparedArchiveCount') != 17 or build.get('qtBinaryInputsBound') is not True
            or build.get('compiledModulePinsBound') is not True
            or any(build.get(k) is not False for k in ('publicationVerified', 'correspondingSourceComplete', 'licenseClearanceClaimed'))):
        raise ValueError('Current native source receipt differs from exact source/download evidence')
    return build


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest='action', required=True)
    verify = actions.add_parser('verify-archives')
    verify.add_argument('--manifest', type=Path, default=HERE / 'native-source/source-release.json')
    verify.add_argument('--archives', type=Path, required=True)
    live = actions.add_parser('collect')
    for name in ('source', 'evidence', 'downloads', 'output', 'source-commit'): live.add_argument('--' + name, required=True)
    args = parser.parse_args()
    if args.action == 'verify-archives':
        result = {'verifiedArchives': verify_archives(load_release(args.manifest), args.archives),
                  'publicationVerified': False, 'correspondingSourceComplete': False}
    else: result = collect(args.source, args.evidence, args.downloads, args.output, args.source_commit)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
