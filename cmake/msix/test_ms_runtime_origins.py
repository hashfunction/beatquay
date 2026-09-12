import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import ms_runtime_origins as origin


class MicrosoftOriginTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve(); self.commit = 'a' * 40
        self.redist = 'C:/Program Files/Microsoft Visual Studio/2022/Enterprise/VC/Redist/MSVC/14.44.35112'
        self.kits = 'C:/Program Files (x86)/Windows Kits/10'
        self.paths = [self.redist + '/x64/Microsoft.VC143.CRT/msvcp140.dll',
                      self.kits + '/Redist/10.0.26100.0/ucrt/DLLs/x64/ucrtbase.dll']
        self.selector = dict(schemaVersion=1, architecture='x64', buildType='RelWithDebInfo',
            msvcRedistRoot=self.redist, windowsKitsRoot=self.kits, sourcePaths=self.paths,
            discoveryModule='C:/CMake/Modules/InstallRequiredSystemLibraries.cmake',
            discoveryModuleSha256=hashlib.sha256(b'actual discovery fixture').hexdigest(), cmakeVersion='3.31.6')
        self.originals = {}; self.files = {}; entries = []
        for i, path in enumerate(self.paths):
            local = self.root / str(i); local.write_bytes(('original fixture ' + str(i)).encode())
            self.originals[path] = local; name = path.rsplit('/', 1)[1]
            measured = self.measure(path); self.files[name] = measured
            entries.append(dict(path=name,sourcePath=path,**measured,fileVersion='14.44.35112.0',
                productVersion='14.44',companyName='Microsoft Corporation',signatureStatus='Valid',signerSubject='fixture publisher'))
        module = self.root / 'module'; module.write_bytes(b'actual discovery fixture')
        self.originals[self.selector['discoveryModule']] = module
        self.record = dict(schemaVersion=1,sourceCommit=self.commit,selectionSha256='b'*64,files=entries,
                           licenseClearanceClaimed=False,redistributionTerms=origin.TERMS)

    def measure(self, path):
        path = self.originals.get(str(path), Path(path)); raw = path.read_bytes()
        return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}

    def validate(self):
        return origin.validate_metadata(self.record,self.selector,'b'*64,self.files,self.commit)

    def test_complete_exact_crt_and_versioned_sdk_origins(self):
        self.assertEqual(len(self.validate()), 2)
        self.record['files'][1]['fileVersion'] = ''
        self.record['files'][1]['signatureStatus'] = 'NotSigned'
        self.assertEqual(len(self.validate()), 2)  # observed metadata, not invented signature success

    def test_foreign_debug_wrong_architecture_and_neighbor_roots_rejected(self):
        for path in [self.redist+'/debug_nonredist/x64/Microsoft.VC143.DebugCRT/msvcp140.dll',
                     self.redist+'Fake/x64/Microsoft.VC143.CRT/msvcp140.dll',
                     self.redist+'/x86/Microsoft.VC143.CRT/msvcp140.dll',
                     self.kits+'/bin/10.0.26100.0/x64/ucrt/ucrtbase.dll',
                     self.kits+'/Redist/10.0.26100.0/ucrt/DLLs/x86/ucrtbase.dll']:
            index = 1 if 'ucrtbase' in path else 0
            before = self.selector['sourcePaths'][index]
            self.selector['sourcePaths'][index] = path
            with self.subTest(path=path), self.assertRaises(ValueError): self.validate()
            self.selector['sourcePaths'][index] = before

    def test_changed_hash_missing_duplicate_and_foreign_observation_rejected(self):
        original = copy.deepcopy(self.record)
        mutations = [lambda r:r['files'].pop(), lambda r:r['files'].append(r['files'][0]),
                     lambda r:r['files'][0].update(sha256='0'*64), lambda r:r['files'][0].update(bytes=True),
                     lambda r:r['files'][0].update(sourcePath='C:/foreign/msvcp140.dll'),
                     lambda r:r.update(sourceCommit='0'*40), lambda r:r.update(selectionSha256='0'*64),
                     lambda r:r.update(redistributionTerms={}), lambda r:r.update(licenseClearanceClaimed=True)]
        for mutation in mutations:
            self.record = copy.deepcopy(original); mutation(self.record)
            with self.assertRaises(ValueError): self.validate()

    def test_unlisted_staged_microsoft_runtime_is_rejected(self):
        self.files['vcruntime140.dll'] = dict(self.files['msvcp140.dll'])
        with self.assertRaisesRegex(ValueError,'exact staged'): self.validate()

    def test_independent_verifier_rereads_original_files_and_discovery_module(self):
        selected = self.root/'ms-runtime-selection.json'; selected.write_text(json.dumps(self.selector))
        self.record['selectionSha256'] = self.measure(selected)['sha256']
        receipt = self.root/'ms-runtime-origins.json'; receipt.write_text(json.dumps(self.record))
        calls=[]
        def read(path): calls.append(str(path)); return self.measure(path)
        origin.verify(self.root,self.files,self.commit,read)
        self.assertTrue(set(self.paths + [self.selector['discoveryModule']]).issubset(calls))
        self.originals[self.paths[0]].write_bytes(b'changed original after collection')
        with self.assertRaisesRegex(ValueError,'Independent original'): origin.verify(self.root,self.files,self.commit,read)


if __name__ == '__main__': unittest.main()
