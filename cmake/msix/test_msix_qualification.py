#!/usr/bin/env python3
"""Real filesystem and archive tests for BeatQuay's qualification package."""
import json
import hashlib
from pathlib import Path
import shutil
import struct
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import zlib
import msix_qualification as msix
REPOSITORY = Path(__file__).resolve().parents[2]

def png(size=16):
    raw=b''.join(b'\0'+bytes((20,80,100,255))*size for _ in range(size))
    def chunk(kind,data): return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',size,size,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b'')

class QualificationTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root=Path(temp.name).resolve(); self.release=self.root/'release'; self.source=self.root/'source'; self.evidence=self.root/'evidence'; self.commit='a'*40
        files={name:('stage:'+name).encode() for name in msix.REQUIRED_RELEASE_FILES}; files['manual.pdf']=b'ordinary complete stage file'
        files['msvcp140.dll']=b'exact original Microsoft fixture'
        for name,data in files.items():
            path=self.release/name; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(data)
        for name in msix.SOURCE_FILES:
            path=self.source/name; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(files.get(name,(REPOSITORY/name).read_bytes()))
        for folder in ('distribution/native-source','distribution/qt-notices'):
            shutil.copytree(REPOSITORY/folder,self.source/folder)
        self.artwork=self.source/'data/branding/beatquay-256.png'; self.artwork.parent.mkdir(parents=True,exist_ok=True); self.artwork.write_bytes(png())
        (self.evidence/'notices').mkdir(parents=True)
        shutil.copytree(self.source/'distribution/qt-notices/6.11.2',self.evidence/'notices/qt')
        for name in msix.EVIDENCE_FILES:
            path=self.evidence/name
            if not path.exists(): path.write_bytes(b'fixture')
        (self.evidence/'candidate-inputs.json').write_bytes((self.source/'distribution/candidate-inputs.json').read_bytes())
        self.seed_source_and_runtime_evidence(files['msvcp140.dll'])
        self.refresh_evidence(); self.inventory=self.root/'package-input.json'; self.refresh_inventory()

    def seed_source_and_runtime_evidence(self, runtime):
        native=msix.native_source; root=self.source/'distribution/native-source'
        release=native.load_release(root/'source-release.json')
        for name,data in native.original_notices(root).items():
            target=self.evidence/'notices/native'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        checked=[{k:x[k] for k in ('owner','file','bytes','sha256','sha512')} for x in release['archives'] if 'recipeSha512' in x]
        build=dict(schemaVersion=1,sourceCommit=self.commit,applicationSourceUrl=native.REPOSITORY+'/tree/'+self.commit,
            sourceReleaseManifest=native.record((root/'source-release.json').read_bytes()),
            originalNoticeManifest=native.record((root/'notice-manifest.json').read_bytes()),preparedArchiveCount=17,
            actualVcpkgSourceArchives=checked,qtBinaryInputsBound=True,compiledModulePinsBound=True,
            publicationVerified=False,correspondingSourceComplete=False,licenseClearanceClaimed=False)
        (self.evidence/'notices/native/build-source.json').write_text(json.dumps(build))
        (self.evidence/'qt-downloads.json').write_text(json.dumps(release['qtBinaryInputs']))
        (self.evidence/'dependency-downloads.json').write_text(json.dumps([{k:x[k] for k in ('file','bytes','sha256')} for x in release['archives'] if 'recipeSha512' in x]))
        for port,name in native.COPYRIGHT_FILES.items():
            target=self.evidence/'notices/vcpkg'/port/'copyright.txt';target.parent.mkdir(parents=True)
            target.write_bytes((root/'notices/vcpkg'/port/name).read_bytes())
        redist='C:/Program Files/Microsoft Visual Studio/2022/Enterprise/VC/Redist/MSVC/14.44.35112'
        original=redist+'/x64/Microsoft.VC143.CRT/msvcp140.dll';module='C:/CMake/Modules/InstallRequiredSystemLibraries.cmake'
        origin_file=self.root/'original-runtime.dll';origin_file.write_bytes(runtime)
        module_file=self.root/'discovery-module.cmake';module_file.write_bytes(b'real discovery fixture bytes')
        selected=dict(schemaVersion=1,sourcePaths=[original],architecture='x64',buildType='RelWithDebInfo',
            msvcRedistRoot=redist,windowsKitsRoot='C:/Program Files (x86)/Windows Kits/10',discoveryModule=module,
            discoveryModuleSha256=hashlib.sha256(module_file.read_bytes()).hexdigest(),cmakeVersion='3.31.6')
        selector_path=self.evidence/'ms-runtime-selection.json';selector_path.write_text(json.dumps(selected))
        origin=dict(schemaVersion=1,sourceCommit=self.commit,selectionSha256=hashlib.sha256(selector_path.read_bytes()).hexdigest(),
            files=[dict(path='msvcp140.dll',sourcePath=original,bytes=len(runtime),sha256=hashlib.sha256(runtime).hexdigest(),
                fileVersion='fixture-version',productVersion='fixture-product-version',companyName='Microsoft Corporation',
                signatureStatus='NotSigned',signerSubject='')],licenseClearanceClaimed=False,redistributionTerms=msix.ms_runtime_origins.TERMS)
        (self.evidence/'ms-runtime-origins.json').write_text(json.dumps(origin))
        # Only resolution of these two Windows-only source paths is redirected to
        # owned fixture files. The production verifier and all actual file reads,
        # hashes, stage comparisons and path predicates execute unchanged.
        reader=msix.file_record;mapping={original:origin_file,module:module_file}
        override=patch.object(msix,'file_record',lambda path:reader(mapping.get(str(path),path)))
        override.start();self.addCleanup(override.stop)
    def refresh_evidence(self):
        files=msix.inventory_tree(self.release)
        rows=[dict(path=name.replace('/','\\'),bytes=row['bytes'],sha256=row['sha256'].upper()) for name,row in files.items()]
        (self.evidence/'stage-inventory.json').write_text(json.dumps(rows))
        pe=[]
        for name,row in files.items():
            if name.lower().endswith(('.exe','.dll')):
                imports=['KERNEL32.dll']+(['beatsprig.exe'] if name in msix.ALLOWED_PLUGIN_DLLS else [])
                pe.append(dict(path=name,**row,imports=sorted(imports,key=str.casefold)))
        (self.evidence/'pe-imports.json').write_text(json.dumps(dict(schemaVersion=1,files=pe,unresolvedImports=[],ambiguousPackagedImports=[],apiSetResolutions=[],resolutionErrors=[],systemDirectory='C:\\Windows\\System32')))
        result=dict(source_commit=self.commit,workflow_run_id='123456',workflow_run_attempt='2',built=True,tests_passed=True,lifecycle_repeat_passed=True,installed_stage=True,native_render_smoke_passed=True,native_render_error_exit_passed=True,native_installed_starter_renders_passed=True,license_clearance=False)
        (self.evidence/'result.json').write_text(json.dumps(result))
    def refresh_inventory(self): self.inventory.write_text(json.dumps(msix.create_input_inventory(self.release,self.source,self.commit,self.evidence,self.artwork)))
    def stage(self): return msix.stage_release(self.release,self.artwork,self.root/'stage',self.commit,self.inventory,self.evidence,self.source)
    def test_complete_stage_binds_whole_input_notices_and_internal_host(self):
        record=self.stage(); self.assertEqual(record['identity']['executable'],'beatsprig.exe'); self.assertEqual(record['releaseInput'],msix.inventory_tree(self.release)); self.assertEqual(record['payload'],msix.inventory_tree(self.root/'stage'))
        self.assertEqual((self.root/'stage/licenses/BeatSprig/LICENSE.txt').read_bytes(),(self.source/'LICENSE.txt').read_bytes()); self.assertEqual((self.root/'stage/licenses/dependencies/qt/qtsvg/src/svg/LICENSE.XSVG.txt').read_bytes(),(self.source/'distribution/qt-notices/6.11.2/qtsvg/src/svg/LICENSE.XSVG.txt').read_bytes()); self.assertFalse(record['licenseClearanceClaimed']); self.assertFalse(record['correspondingSourceComplete'])
        self.assertEqual((self.root/'stage/licenses/BeatSprig/GPL-3.0.txt').read_bytes(),(self.source/'distribution/native-source/notices/app-submodules/ringbuffer/LICENSE.txt').read_bytes())
        for name in ('ms-runtime-origins.json','ms-runtime-selection.json'):
            self.assertEqual((self.root/'stage/licenses/Microsoft'/name).read_bytes(),(self.evidence/name).read_bytes())

    def test_stage_contains_every_published_original_notice(self):
        record = self.stage()
        published = json.loads((REPOSITORY / 'cmake/msix/fixtures/public-source-20260912/source-delivery-inputs.json').read_text())
        for name, original in published['originalNoticeMembers'].items():
            with self.subTest(notice=name):
                self.assertEqual(record['payload'].get(name),
                                 {key: original[key] for key in ('bytes', 'sha256')})

    def test_detailed_original_notices_and_origin_receipts_cannot_be_omitted(self):
        for name in ('notices/native/notices/app-submodules/ringbuffer/LICENSE.txt',
                     'notices/qt/qtsvg/src/svg/LICENSE.XSVG.txt',
                     'notices/vcpkg/libogg/copyright.txt','ms-runtime-origins.json',
                     'notices/native/build-source.json'):
            path=self.evidence/name;original=path.read_bytes();path.unlink()
            with self.subTest(name=name),self.assertRaises((OSError,ValueError)):self.stage()
            self.assertFalse((self.root/'stage').exists());path.write_bytes(original)

    def test_source_preparation_receipt_cannot_claim_published_delivery(self):
        path=self.evidence/'notices/native/build-source.json';record=json.loads(path.read_bytes())
        record['publicationVerified']=True;path.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError,'source receipt'):self.refresh_inventory()

    def test_changed_microsoft_original_is_rejected_before_package_output(self):
        (self.root/'original-runtime.dll').write_bytes(b'foreign runtime original')
        with self.assertRaisesRegex(ValueError,'Independent original'):self.stage()
        self.assertFalse((self.root/'stage').exists())
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
    def test_previous_host_import_is_rejected_after_rename(self):
        path=self.evidence/'pe-imports.json'; record=json.loads(path.read_text())
        next(row for row in record['files'] if row['path']=='plugins/kicker.dll')['imports']=['KERNEL32.dll','lmms.exe']
        path.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError,'internal host'): self.refresh_inventory()
    def test_consumer_helpers_are_bound_before_package_creation(self):
        names=('cmake/msix/consumer-workflow.ps1','cmake/msix/consumer-display.ps1','cmake/msix/consumer_files.py',
               'cmake/msix/qualify-msix-install.ps1','cmake/msix/first-run.ps1','tests/scripted/starter_render.py',
               'cmake/msix/qualification-bindings.ps1','cmake/msix/verify_record.py','cmake/msix/msix_qualification.py',
               'cmake/msix/prepare_inventory.py','cmake/msix/ms_runtime_origins.py')
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
        data=msix.create_manifest(); self.assertEqual(msix.validate_manifest(data),msix.QUALIFICATION_IDENTITY); self.assertIn(b'BeatSprig 1.0.1',data); self.assertIn(b'beatsprig.exe',data)
    def test_fixed_store_manifest_preserves_application_id_and_refuses_cross_mode(self):
        data=msix.create_manifest('store')
        identity=msix.validate_manifest(data,'store')
        self.assertEqual(identity['packageName'],'1659hashfunction.BeatQuay')
        self.assertEqual(identity['publisher'],'CN=B6A2631A-FD32-45CC-AE12-82466975F528')
        self.assertEqual(identity['applicationId'],'BeatQuay')
        self.assertEqual(identity['version'],'1.0.1.0')
        self.assertIn(b'<PublisherDisplayName>hashfunction</PublisherDisplayName>',data)
        for mode,wrong in [('qualification',data),('store',msix.create_manifest())]:
            with self.assertRaises(ValueError):msix.validate_manifest(wrong,mode)
        for mode in ('Store','','custom',None):
            with self.assertRaises(ValueError):msix.create_manifest(mode)
        for old,new in [(b'Id="BeatQuay"',b'Id="SomeMsaId"'),(b'1.0.1.0',b'1.0.2.0'),(b'hashfunction</PublisherDisplayName>',b'Trieflow LLC</PublisherDisplayName>')]:
            with self.assertRaises(ValueError):msix.validate_manifest(data.replace(old,new),'store')
    def test_store_mode_threads_through_package_and_installed_verifiers(self):
        record=msix.stage_release(self.release,self.artwork,self.root/'stage',self.commit,self.inventory,self.evidence,self.source,'store')
        self.assertEqual(record['identityMode'],'store');self.assertTrue(record['storeIdentityStaged'])
        self.assertFalse(record['qualificationIdentityOnly']);self.assertFalse(record['installationQualificationPassed'])
        self.assertFalse(record['signed']);self.assertFalse(record['publicRelease'])
        package=self.root/'store.msix'
        with zipfile.ZipFile(package,'w') as archive:
            for name in record['payload']:archive.write(self.root/'stage'/name,name.replace('+','%2B'))
            archive.writestr('[Content_Types].xml',b'types');archive.writestr('AppxBlockMap.xml',b'blocks')
        record['containerVerification']=msix.verify_msix(package,record['payload'],'store')
        record['unpackedVerification']=msix.verify_unpacked(self.root/'stage',record['payload'],'store')
        msix.verify_installed(self.root/'stage',record['payload'],'store')
        path=self.root/'record.json';path.write_text(json.dumps(record))
        self.assertTrue(msix.verify_record_inputs(package,path,self.release,self.artwork,self.commit,self.inventory,self.evidence,self.source,'store'))
        for action in (lambda:msix.verify_msix(package,record['payload']),lambda:msix.verify_installed(self.root/'stage',record['payload']),
                       lambda:msix.verify_record_inputs(package,path,self.release,self.artwork,self.commit,self.inventory,self.evidence,self.source)):
            with self.assertRaises(ValueError):action()
        for field in ('qualificationIdentityOnly','storeIdentityStaged','installationQualificationPassed','signed','publicRelease','licenseClearanceClaimed','correspondingSourceComplete'):
            original=record[field];record[field]=int(original);path.write_text(json.dumps(record))
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,'typed.*flags'):
                msix.verify_record_inputs(package,path,self.release,self.artwork,self.commit,self.inventory,self.evidence,self.source,'store')
            record[field]=original

    def test_both_sdk_build_routes_keep_exact_payload_and_distinct_unsigned_outputs(self):
        tool=self.root/'Windows Kits/10/bin/10.0.26100.0/x64/makeappx.exe'
        tool.parent.mkdir(parents=True);tool.write_bytes(b'owned SDK command seam')
        calls=[]
        def sdk(command):
            calls.append(command)
            package=Path(command[command.index('/p')+1]);folder=Path(command[command.index('/d')+1])
            if command[1]=='pack':
                with zipfile.ZipFile(package,'w') as archive:
                    for entry in sorted(folder.rglob('*')):
                        if entry.is_file():archive.write(entry,entry.relative_to(folder).as_posix().replace('+','%2B'))
                    archive.writestr('[Content_Types].xml',b'types');archive.writestr('AppxBlockMap.xml',b'blocks')
            elif command[1]=='unpack':
                from urllib.parse import unquote
                with zipfile.ZipFile(package) as archive:
                    for entry in archive.infolist():
                        target=folder/unquote(entry.filename);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(archive.read(entry))
            else:self.fail('Unexpected SDK command')
        for mode,filename in [('qualification','BeatSprig.Qualification_1.0.1.0_x64.msix'),('store','BeatSprig_1.0.1.0_x64.msix')]:
            output=self.root/('sdk-'+mode)
            msix.build_qualification(self.release,self.artwork,self.commit,tool,'10.0.26100.0',output,
                self.inventory,self.evidence,self.source,runner=sdk,identity_mode=mode)
            self.assertEqual({p.name for p in output.iterdir()},{filename,'package-record.json'})
            package=output/filename;record=json.loads((output/'package-record.json').read_bytes())
            self.assertEqual(record['identity'],msix.identity_for(mode));self.assertFalse(record['signed'])
            self.assertEqual(record['containerVerification']['package'],msix.file_record(package))
            with zipfile.ZipFile(package) as archive:
                self.assertNotIn('AppxSignature.p7x',archive.namelist())
                self.assertEqual(archive.read('beatsprig.exe'),(self.release/'beatsprig.exe').read_bytes())
                msix.validate_manifest(archive.read('AppxManifest.xml'),mode)
        self.assertEqual([command[1] for command in calls],['pack','unpack','pack','unpack'])
    def test_native_run_binding_rejects_missing_typed_or_other_attempt(self):
        path=self.evidence/'result.json';record=json.loads(path.read_bytes())
        record.update(workflow_run_id='123456',workflow_run_attempt='2');path.write_text(json.dumps(record));self.refresh_inventory()
        bound=json.loads(self.inventory.read_bytes());msix.validate_run_binding(bound,'123456','2')
        self.assertEqual(bound['workflowRunId'],'123456');self.assertEqual(bound['workflowRunAttempt'],'2')
        for run,attempt in [('123457','2'),('123456','1'),('','2'),('123456',2)]:
            with self.assertRaises(ValueError):msix.validate_run_binding(bound,run,attempt)
        for value in (None,False,1,'0','-1','1.0'):
            record['workflow_run_attempt']=value;path.write_text(json.dumps(record))
            with self.assertRaises(ValueError):self.refresh_inventory()
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
