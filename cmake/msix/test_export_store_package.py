"""Real file/Git/package policy tests; generated fixtures are not Windows acceptance."""
import copy
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import unquote
import zipfile

import export_store_package as subject
import test_msix_qualification as package_fixture

SOURCE=Path(__file__).resolve().parents[2]


def environment(commit):
    return dict(CI='true',GITHUB_ACTIONS='true',GITHUB_REPOSITORY='hashfunction/beatquay',
        GITHUB_EVENT_NAME='workflow_dispatch',BEATSPRIG_EXPORT_STORE_PACKAGE='true',GITHUB_SHA=commit,
        GITHUB_RUN_ID='123456',GITHUB_RUN_ATTEMPT='2')


class ContextTests(unittest.TestCase):
    def test_workflow_opt_in_and_exact_two_artifact_paths(self):
        workflow=(SOURCE/'.github/workflows/windows-candidate.yml').read_text()
        inputs=workflow.split('  workflow_dispatch:',1)[1].split('  push:',1)[0]
        self.assertIn('export_store_package:',inputs);self.assertIn('default: false',inputs)
        block=workflow.split('      - name: Preserve exact reviewed unsigned Store export',1)[1]
        self.assertIn("if: success() && github.event_name == 'workflow_dispatch' && inputs.export_store_package == true",block)
        paths=block.split('path: |',1)[1].split('retention-days:',1)[0].split()
        self.assertEqual(paths,['build-evidence/store-export/'+subject.OUTPUT_PACKAGE,'build-evidence/store-export/'+subject.OUTPUT_RECEIPT])
        self.assertIn('if-no-files-found: error',block)

    def test_exact_explicit_dispatch_platform_source_repository_and_attempt(self):
        commit='a'*40;env=environment(commit)
        self.assertEqual(subject.workflow_context(commit,env,'win32')['workflowRunAttempt'],'2')
        for key,value in [('CI','false'),('GITHUB_ACTIONS',False),('GITHUB_REPOSITORY','foreign/repo'),
            ('GITHUB_EVENT_NAME','push'),('BEATSPRIG_EXPORT_STORE_PACKAGE','false'),('GITHUB_SHA','b'*40),
            ('GITHUB_RUN_ID','0'),('GITHUB_RUN_ATTEMPT',2),('GITHUB_RUN_ATTEMPT','')]:
            changed=dict(env);changed[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):subject.workflow_context(commit,changed,'win32')
        with self.assertRaises(ValueError):subject.workflow_context(commit,env,'linux')
        with self.assertRaises(ValueError):subject.workflow_context('main',env,'win32')

    def test_actual_git_tree_dirty_tracked_untracked_and_wrong_reviewed_commit(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve()
            def git(*args):return subprocess.run(['git','-C',str(root),*args],capture_output=True,text=True,check=True).stdout.strip()
            git('init','-q');git('config','user.name','Export fixture');git('config','user.email','fixture@example.invalid')
            (root/'source.txt').write_text('original');git('add','.');git('commit','-qm','Owned fixture')
            commit=git('rev-parse','HEAD');tree=git('show','-s','--format=%T','HEAD')
            self.assertEqual(subject.local_source(root,commit),dict(commit=commit,tree=tree))
            with self.assertRaisesRegex(ValueError,'reviewed'):subject.local_source(root,'0'*40)
            (root/'source.txt').write_text('changed')
            with self.assertRaisesRegex(ValueError,'Dirty'):subject.local_source(root,commit)
            git('restore','source.txt');(root/'untracked.txt').write_text('new')
            with self.assertRaisesRegex(ValueError,'Dirty'):subject.local_source(root,commit)


class OwnedOutputTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve()
    def test_exact_two_files_and_unchanged_cleanup(self):
        owned=subject.OwnedOutput(self.root/'export')
        owned.write(subject.OUTPUT_PACKAGE,[b'exact unsigned bytes']);owned.write(subject.OUTPUT_RECEIPT,[b'{}'])
        owned.verify();owned.cleanup();self.assertFalse(owned.path.exists())
    def test_existing_directory_file_and_link_never_replaced(self):
        directory=self.root/'existing';directory.mkdir();(directory/'foreign').write_bytes(b'keep')
        with self.assertRaises(FileExistsError):subject.OwnedOutput(directory)
        self.assertEqual((directory/'foreign').read_bytes(),b'keep')
        path=self.root/'file';path.write_bytes(b'keep')
        with self.assertRaises(FileExistsError):subject.OwnedOutput(path)
        if os.name!='nt':
            alias=self.root/'alias';alias.symlink_to(directory,target_is_directory=True)
            with self.assertRaises((ValueError,FileExistsError)):subject.OwnedOutput(alias)
    def test_foreign_file_or_mutated_owned_bytes_preserve_entire_output(self):
        for kind in ('foreign','changed','replaced'):
            owned=subject.OwnedOutput(self.root/kind);owned.write(subject.OUTPUT_PACKAGE,[b'original'])
            if kind=='foreign':(owned.path/'foreign').write_bytes(b'keep')
            elif kind=='changed':(owned.path/subject.OUTPUT_PACKAGE).write_bytes(b'changed')
            else:
                (owned.path/subject.OUTPUT_PACKAGE).rename(owned.path/'saved-original')
                (owned.path/subject.OUTPUT_PACKAGE).write_bytes(b'original')
                (owned.path/'saved-original').unlink()
            with self.subTest(kind=kind),self.assertRaises(ValueError):owned.cleanup()
            self.assertTrue((owned.path/subject.OUTPUT_PACKAGE).exists())
    def test_replaced_directory_is_refused_before_any_new_write(self):
        owned=subject.OwnedOutput(self.root/'export')
        owned.path.rename(self.root/'original-export');owned.path.mkdir()
        with self.assertRaisesRegex(ValueError,'replaced'):owned.write(subject.OUTPUT_PACKAGE,[b'original'])
        self.assertEqual(list(owned.path.iterdir()),[])

    def test_partial_copy_failure_cleans_only_exact_written_owned_bytes(self):
        owned=subject.OwnedOutput(self.root/'partial')
        def chunks():yield b'partial original';raise OSError('copy failed')
        with self.assertRaisesRegex(OSError,'copy failed'):owned.write(subject.OUTPUT_PACKAGE,chunks())
        self.assertEqual((owned.path/subject.OUTPUT_PACKAGE).read_bytes(),b'partial original')
        owned.cleanup();self.assertFalse(owned.path.exists())


class PackageBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.fixture=package_fixture.QualificationTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        f=self.fixture;self.source=f.source
        # Move the actual controlled native-stage fixture to production paths.
        shutil.move(f.release,f.source/'stage');f.release=f.source/'stage'
        shutil.move(f.evidence,f.source/'build-evidence');f.evidence=f.source/'build-evidence'
        shutil.move(f.inventory,f.evidence/'package-input.json');f.inventory=f.evidence/'package-input.json'
        f.refresh_inventory()
        self.context=subject.workflow_context(f.commit,environment(f.commit),'win32')
        tool=f.root/'Windows Kits/10/bin/10.0.26100.0/x64/makeappx.exe'
        tool.parent.mkdir(parents=True);tool.write_bytes(b'exact SDK fixture')
        self.sign=tool.with_name('signtool.exe');self.sign.write_bytes(b'exact signing fixture')
        self.packages={}
        def sdk(command):
            package=Path(command[command.index('/p')+1]);folder=Path(command[command.index('/d')+1])
            if command[1]=='pack':
                with zipfile.ZipFile(package,'w') as archive:
                    for entry in sorted(folder.rglob('*')):
                        if entry.is_file():archive.write(entry,entry.relative_to(folder).as_posix().replace('+','%2B'))
                    archive.writestr('[Content_Types].xml',b'types');archive.writestr('AppxBlockMap.xml',b'blocks')
            elif command[1]=='unpack':
                with zipfile.ZipFile(package) as archive:
                    for entry in archive.infolist():
                        target=folder/unquote(entry.filename);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(archive.read(entry))
            else:raise AssertionError('Unexpected SDK command')
        for mode,(name,folder) in subject.MODES.items():
            output=f.root/('package-'+mode)
            subject.package.build_qualification(f.release,f.artwork,f.commit,tool,'10.0.26100.0',output,f.inventory,f.evidence,f.source,runner=sdk,identity_mode=mode)
            shutil.copyfile(output/'package-record.json',f.evidence/name)
            self.packages[mode]=output/subject.package.package_filename(mode)
            directory=f.evidence/folder;directory.mkdir()
            (directory/'installation-qualification.json').write_text(json.dumps(dict(signtool=dict(path=str(self.sign),sdk_version='10.0.26100.0',**subject.package.file_record(self.sign)))))
    def verify(self):return subject.verify_packages(self.source,self.fixture.evidence,self.packages,self.context)
    def test_real_source_native_original_dll_sdk_and_two_unsigned_containers(self):
        result=self.verify();self.assertEqual(set(result['records']),{'qualification','store'})
        self.assertEqual(result['records']['store']['identity'],subject.package.identity_for('store'))
        self.assertNotEqual(result['files']['unsigned-store'],result['files']['unsigned-qualification'])
    def test_changed_private_record_tool_original_dll_signed_archive_and_stale_attempt(self):
        self.verify()
        for path in (self.packages['store'].parent/'package-record.json',self.sign,self.fixture.root/'original-runtime.dll'):
            data=path.read_bytes();path.write_bytes(data+b'changed')
            with self.subTest(path=path.name),self.assertRaises(ValueError):self.verify()
            path.write_bytes(data)
        old=self.context['workflowRunAttempt'];self.context['workflowRunAttempt']='1'
        with self.assertRaises(ValueError):self.verify()
        self.context['workflowRunAttempt']=old
        with zipfile.ZipFile(self.packages['store'],'a') as archive:archive.writestr('AppxSignature.p7x',b'signed')
        with self.assertRaises(ValueError):self.verify()
    def test_orchestration_repeats_all_local_gates_and_exports_exact_original_bytes(self):
        original=self.verify();calls=[]
        real=subject.verify_packages
        def packages(*args):calls.append('packages');return real(*args)
        def lifecycle(*args):calls.append('lifecycles');return {'generatedUnitSeamOnly':True}
        def local(*args):calls.append('source');return dict(commit=self.fixture.commit,tree='b'*40)
        with patch.object(subject,'verify_packages',packages),patch.object(subject.evidence,'verify_lifecycles',lifecycle),\
             patch.object(subject,'local_source',local),patch.object(subject.publication,'verify_public_tree',return_value={'publicUnitSeamOnly':True}),\
             patch.object(subject.publication,'verify_publication',return_value={'sourceUnitSeamOnly':True}):
            result=subject.export(self.source,self.packages,self.fixture.commit,environ=environment(self.fixture.commit),platform='win32')
        out=self.fixture.evidence/'store-export'
        self.assertEqual(set(x.name for x in out.iterdir()),{subject.OUTPUT_PACKAGE,subject.OUTPUT_RECEIPT})
        self.assertEqual((out/subject.OUTPUT_PACKAGE).read_bytes(),self.packages['store'].read_bytes())
        self.assertEqual(subject.evidence.load(out/subject.OUTPUT_RECEIPT),result)
        self.assertEqual(calls,['source','packages','lifecycles','packages','lifecycles','source','packages','lifecycles','source'])
        self.assertEqual(result['originalPackageInputs'],original['files'])
        self.assertFalse(result['physicalAudioVerified']);self.assertFalse(result['storeSubmitted'])
    def test_failure_before_or_after_copy_never_exports_or_erases_changed_data(self):
        # Other verifier seams have independent actual-source/UI/file tests.
        for phase in ('before','after','foreign'):
            out=self.fixture.evidence/'store-export';count=0
            def lifecycle(*args):
                nonlocal count
                count+=1
                if phase=='before' and count==2:raise ValueError('changed original evidence')
                if phase in ('after','foreign') and count==3:
                    if phase=='foreign':(out/'foreign.txt').write_bytes(b'preserve')
                    raise ValueError('changed original evidence')
                return {'generatedUnitSeamOnly':True}
            with patch.object(subject,'local_source',return_value=dict(commit=self.fixture.commit,tree='b'*40)),\
                 patch.object(subject.evidence,'verify_lifecycles',lifecycle),\
                 patch.object(subject.publication,'verify_public_tree',return_value={}),\
                 patch.object(subject.publication,'verify_publication',return_value={}),\
                 patch('sys.stderr',new_callable=io.StringIO),self.subTest(phase=phase),self.assertRaisesRegex(ValueError,'changed original evidence'):
                subject.export(self.source,self.packages,self.fixture.commit,environ=environment(self.fixture.commit),platform='win32')
            if phase=='foreign':
                self.assertEqual((out/'foreign.txt').read_bytes(),b'preserve')
                self.assertTrue((out/subject.OUTPUT_PACKAGE).exists())
            else:self.assertFalse(out.exists())


if __name__=='__main__':unittest.main()
