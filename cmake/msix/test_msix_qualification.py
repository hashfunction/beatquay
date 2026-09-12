#!/usr/bin/env python3
"""Real filesystem and archive tests for BeatQuay's qualification package."""
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zipfile
import zlib
import msix_qualification as msix

def png(size=16):
    raw=b''.join(b'\0'+bytes((20,80,100,255))*size for _ in range(size))
    def chunk(kind,data): return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',size,size,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b'')

class QualificationTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root=Path(temp.name); self.release=self.root/'release'; self.source=self.root/'source'; self.evidence=self.root/'evidence'; self.commit='a'*40
        files={name:('stage:'+name).encode() for name in msix.REQUIRED_RELEASE_FILES}; files['manual.pdf']=b'ordinary complete stage file'
        for name,data in files.items():
            path=self.release/name; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(data)
        for name in msix.SOURCE_FILES:
            path=self.source/name; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(files.get(name,('source:'+name).encode()))
        self.artwork=self.source/'data/branding/beatquay-256.png'; self.artwork.parent.mkdir(parents=True,exist_ok=True); self.artwork.write_bytes(png())
        (self.evidence/'notices/qt').mkdir(parents=True); (self.evidence/'notices/qt/LGPL-3.0-only.txt').write_bytes(b'Qt license')
        (self.evidence/'notices/zlib').mkdir(); (self.evidence/'notices/zlib/copyright.txt').write_bytes(b'zlib notice')
        for name in msix.EVIDENCE_FILES:
            path=self.evidence/name
            if not path.exists(): path.write_bytes(b'fixture')
        (self.evidence/'candidate-inputs.json').write_bytes((self.source/'distribution/candidate-inputs.json').read_bytes())
        self.refresh_evidence(); self.inventory=self.root/'package-input.json'; self.refresh_inventory()
    def refresh_evidence(self):
        files=msix.inventory_tree(self.release)
        rows=[dict(path=name.replace('/','\\'),bytes=row['bytes'],sha256=row['sha256'].upper()) for name,row in files.items()]
        (self.evidence/'stage-inventory.json').write_text(json.dumps(rows))
        pe=[]
        for name,row in files.items():
            if name.lower().endswith(('.exe','.dll')):
                imports=['KERNEL32.dll']+(['lmms.exe'] if name in msix.ALLOWED_PLUGIN_DLLS else [])
                pe.append(dict(path=name,**row,imports=sorted(imports,key=str.casefold)))
        (self.evidence/'pe-imports.json').write_text(json.dumps(dict(schemaVersion=1,files=pe,unresolvedImports=[],ambiguousPackagedImports=[],apiSetResolutions=[],resolutionErrors=[],systemDirectory='C:\\Windows\\System32')))
        result=dict(source_commit=self.commit,built=True,tests_passed=True,lifecycle_repeat_passed=True,installed_stage=True,native_render_smoke_passed=True,native_render_error_exit_passed=True,native_installed_starter_renders_passed=True,license_clearance=False)
        (self.evidence/'result.json').write_text(json.dumps(result))
    def refresh_inventory(self): self.inventory.write_text(json.dumps(msix.create_input_inventory(self.release,self.source,self.commit,self.evidence,self.artwork)))
    def stage(self): return msix.stage_release(self.release,self.artwork,self.root/'stage',self.commit,self.inventory,self.evidence,self.source)
    def test_complete_stage_binds_whole_input_notices_and_internal_host(self):
        record=self.stage(); self.assertEqual(record['identity']['executable'],'lmms.exe'); self.assertEqual(record['releaseInput'],msix.inventory_tree(self.release)); self.assertEqual(record['payload'],msix.inventory_tree(self.root/'stage'))
        self.assertEqual((self.root/'stage/licenses/BeatQuay/LICENSE.txt').read_bytes(),(self.source/'LICENSE.txt').read_bytes()); self.assertEqual((self.root/'stage/licenses/dependencies/qt/LGPL-3.0-only.txt').read_bytes(),b'Qt license'); self.assertFalse(record['licenseClearanceClaimed']); self.assertFalse(record['correspondingSourceComplete'])
    def test_exact_plugins_projects_and_no_debug_crt(self):
        for name in ('plugins/unknown.dll','data/projects/demo.mmp','msvcp140d.dll'):
            with self.subTest(name=name):
                path=self.release/name; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(b'bad'); self.refresh_evidence()
                with self.assertRaises(ValueError): msix.create_input_inventory(self.release,self.source,self.commit,self.evidence,self.artwork)
                path.unlink()
        missing=self.release/'plugins/kicker.dll'; data=missing.read_bytes(); missing.unlink(); self.refresh_evidence()
        with self.assertRaises(ValueError): msix.create_input_inventory(self.release,self.source,self.commit,self.evidence,self.artwork)
        missing.write_bytes(data)
    def test_plugin_host_import_and_complete_pe_coverage_are_required(self):
        record=json.loads((self.evidence/'pe-imports.json').read_text()); record['files']=[r for r in record['files'] if r['path']!='plugins/kicker.dll']; (self.evidence/'pe-imports.json').write_text(json.dumps(record))
        with self.assertRaises(ValueError): self.refresh_inventory()
        self.refresh_evidence(); record=json.loads((self.evidence/'pe-imports.json').read_text()); next(r for r in record['files'] if r['path']=='plugins/kicker.dll')['imports']=['KERNEL32.dll']; (self.evidence/'pe-imports.json').write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError,'internal host'): self.refresh_inventory()
    def test_source_notice_artwork_and_same_run_stage_are_revalidated(self):
        self.source.joinpath('LICENSE.txt').write_bytes(b'changed')
        with self.assertRaises(ValueError): self.stage()
        self.source.joinpath('LICENSE.txt').write_bytes(b'source:LICENSE.txt'); self.release.joinpath('manual.pdf').write_bytes(b'changed')
        with self.assertRaises(ValueError): self.stage()
    def test_consumer_helpers_are_bound_before_package_creation(self):
        names=('cmake/msix/consumer-workflow.ps1','cmake/msix/consumer-display.ps1','cmake/msix/consumer_files.py',
               'cmake/msix/qualify-msix-install.ps1','cmake/msix/first-run.ps1','tests/scripted/starter_render.py')
        for name in names:
            path=self.source/name; path.parent.mkdir(parents=True,exist_ok=True)
            if not path.exists(): path.write_bytes(b'original consumer helper')
        self.refresh_inventory()
        for name in names:
            path=self.source/name; original=path.read_bytes(); path.write_bytes(b'changed verifier or UI driver')
            with self.subTest(name=name), self.assertRaises(ValueError): self.stage()
            path.write_bytes(original)
    def test_api_set_receipt_requires_exact_coverage_and_host_provenance(self):
        path=self.evidence/'pe-imports.json'
        record=json.loads(path.read_text())
        contract='api-ms-win-core-winrt-l1-1-0.dll'
        next(row for row in record['files'] if row['path']=='Qt6Core.dll')['imports'].insert(0,contract)
        host=dict(contract=contract,apiSetImplemented=True,loaderFlags=2048,
            hostPath='C:\\Windows\\System32\\combase.dll',hostBytes=1234,hostSha256='b'*64,
            signatureStatus='Valid',signerSubject='CN=Microsoft Windows Publisher, O=Microsoft Corporation',
            signerIssuer='CN=Microsoft Windows Production PCA 2011',signerThumbprint='c'*40,
            signerCommonName='Microsoft Windows Publisher',signerOrganization='Microsoft Corporation')
        record['apiSetResolutions']=[host]
        path.write_text(json.dumps(record)); self.refresh_inventory()
        corruptions=[[],[host,host],[dict(host,contract='api-ms-win-other-l1-1-0.dll')]]
        corruptions.extend([[dict(host,**{field:value})] for field,value in (
            ('hostPath','C:\\Windows\\System32Fake\\combase.dll'),('hostPath','C:\\Windows\\System32\\nested\\combase.dll'),
            ('hostPath','C:\\Windows\\System32\\..\\combase.dll'),('hostBytes',True),('hostSha256','invalid'),
            ('apiSetImplemented',False),('loaderFlags',0),('signatureStatus','NotSigned'),
            ('signerOrganization','Other'),('signerCommonName','Other'),('signerThumbprint',''))])
        for entries in corruptions:
            with self.subTest(entries=entries):
                record['apiSetResolutions']=entries; path.write_text(json.dumps(record))
                with self.assertRaisesRegex(ValueError,'API.set'): self.refresh_inventory()
    def test_api_set_receipt_cannot_claim_an_unimported_contract(self):
        path=self.evidence/'pe-imports.json'; record=json.loads(path.read_text())
        record['apiSetResolutions']=[dict(contract='api-ms-win-core-winrt-l1-1-0.dll')]
        path.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError,'API.set'): self.refresh_inventory()
    def test_resolution_failure_diagnostics_cannot_be_hidden_by_empty_unresolved_list(self):
        path=self.evidence/'pe-imports.json'; record=json.loads(path.read_text())
        record['resolutionErrors']=[dict(file='Qt6Core.dll',importName='missing.dll',error='not found')]
        path.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError,'Unresolved'): self.refresh_inventory()
    def test_output_collision_and_release_links_are_refused(self):
        (self.root/'stage').mkdir()
        with self.assertRaises(ValueError): self.stage()
        (self.root/'stage').rmdir(); target=self.release/'manual.pdf'; target.unlink(); target.symlink_to(self.source/'LICENSE.txt')
        with self.assertRaises(ValueError): self.refresh_inventory()
    def test_manifest_uses_disposable_identity_and_exact_display(self):
        data=msix.create_manifest(); self.assertEqual(msix.validate_manifest(data),msix.QUALIFICATION_IDENTITY); self.assertIn(b'BeatQuay 1.0.0',data); self.assertIn(b'lmms.exe',data)
    def test_opc_decoding_and_exact_container_payload(self):
        record=self.stage(); package=self.root/'fixture.msix'
        with zipfile.ZipFile(package,'w') as archive:
            for name in record['payload']: archive.write(self.root/'stage'/name,name.replace('+','%2B'))
            archive.writestr('[Content_Types].xml',b'types'); archive.writestr('AppxBlockMap.xml',b'blocks')
        verified=msix.verify_msix(package,record['payload']); self.assertEqual(verified['verifiedPayloadFiles'],len(record['payload']))
        with zipfile.ZipFile(package,'a') as archive: archive.writestr('extra.txt',b'bad')
        with self.assertRaises(ValueError): msix.verify_msix(package,record['payload'])
    def test_record_requires_exact_typed_sdk_unpack_count(self):
        record=self.stage(); package=self.root/'fixture.msix'
        with zipfile.ZipFile(package,'w') as archive:
            for name in record['payload']: archive.write(self.root/'stage'/name,name.replace('+','%2B'))
            archive.writestr('[Content_Types].xml',b'types'); archive.writestr('AppxBlockMap.xml',b'blocks')
        record['containerVerification']=msix.verify_msix(package,record['payload'])
        record['unpackedVerification']={'verifiedPayloadFiles':len(record['payload'])}
        path=self.root/'record.json'; path.write_text(json.dumps(record))
        self.assertTrue(msix.verify_record_inputs(package,path,self.release,self.artwork,self.commit,self.inventory,self.evidence,self.source))
        for bad in (0, True, '1', 1.0, len(record['payload'])+1, {'verifiedPayloadFiles':len(record['payload']),'extra':0}):
            with self.subTest(bad=bad):
                record['unpackedVerification']=bad if isinstance(bad,dict) else {'verifiedPayloadFiles':bad}
                path.write_text(json.dumps(record))
                with self.assertRaisesRegex(ValueError,'exact source-bound SDK unpack evidence'):
                    msix.verify_record_inputs(package,path,self.release,self.artwork,self.commit,self.inventory,self.evidence,self.source)
    def test_producer_and_install_verifier_share_the_package_input_path(self):
        directory=Path(msix.__file__).resolve().parent
        self.assertIn('Path(PACKAGE_INPUT_RECORD)',(directory/'prepare_inventory.py').read_text())
        self.assertIn('source / PACKAGE_INPUT_RECORD',(directory/'verify_record.py').read_text())
        self.assertEqual(msix.PACKAGE_INPUT_RECORD,'build-evidence/package-input.json')
    def test_workflow_dispatches_qualifier_and_uploads_metadata_only(self):
        workflow=(Path(msix.__file__).resolve().parents[2]/'.github/workflows/windows-candidate.yml').read_text()
        self.assertIn('./distribution/qualify-candidate.ps1',workflow)
        upload=workflow.split('name: Preserve metadata only',1)[1]
        for forbidden in ('*.msix','*.exe','*.dll','stage/**'):
            self.assertNotIn(forbidden,upload)
        for required in ('build-evidence/**/*.json','build-evidence/**/*.txt','build-evidence/**/*.xml','build-evidence/**/*.log','build-evidence/**/*.png'):
            self.assertIn(required,upload)
if __name__=='__main__': unittest.main()
