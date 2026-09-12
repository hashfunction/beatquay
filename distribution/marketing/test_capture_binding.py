"""Capture policy fixtures do not establish any Windows qualification."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

MODULE=Path(__file__).with_name('capture_checks.py')


class BindingTests(unittest.TestCase):
    def subject(self):
        self.assertTrue(MODULE.is_file(), 'Capture binding verifier is not implemented')
        spec=importlib.util.spec_from_file_location('capture_binding_subject',MODULE)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        return module

    def approved(self):
        return dict(schema_version=1,product='BeatSprig',qualified=dict(source_commit='a'*40,
            workflow_run_id='1',workflow_run_attempt='1',store_artifact_id=2,metadata_artifact_id=3,
            package=dict(bytes=100,sha256='b'*64),export_receipt=dict(bytes=101,sha256='c'*64)))

    def test_current_binding_stays_unbound_and_has_no_implicit_fallback(self):
        subject=self.subject()
        self.assertIsNone(json.loads(MODULE.with_name('binding.json').read_text())['qualified'])
        with self.assertRaisesRegex(ValueError,'reviewed successful'):subject.binding()

    def test_exact_typed_binding_and_refusals(self):
        subject=self.subject();valid=self.approved()
        self.assertEqual(subject.validate_binding(valid),valid['qualified'])
        for path,value in [('qualified',None),('schema_version',True),('product','BeatQuay'),
            ('qualified.source_commit','main'),('qualified.workflow_run_id',1),('qualified.workflow_run_attempt','0'),
            ('qualified.store_artifact_id',True),('qualified.metadata_artifact_id',0),('qualified.package.bytes',True),
            ('qualified.package.sha256','B'*64),('qualified.export_receipt.bytes',0),('qualified.unreviewed',True)]:
            changed=copy.deepcopy(valid);parts=path.split('.');target=changed
            for key in parts[:-1]:target=target[key]
            target[parts[-1]]=value
            with self.subTest(path=path),self.assertRaises(ValueError):subject.validate_binding(changed)

    def test_only_exact_successful_qualification_run_and_attempt(self):
        subject=self.subject();b=self.approved()['qualified']
        run=dict(id=1,run_attempt=1,head_sha='a'*40,conclusion='success',event='workflow_dispatch',
            path='.github/workflows/windows-candidate.yml',repository=dict(full_name='hashfunction/beatquay'))
        subject.verify_run(run,b)
        for key,value in [('id',True),('run_attempt',2),('head_sha','b'*40),('conclusion','failure'),
            ('event','push'),('path','.github/workflows/marketing-screenshots.yml'),('repository',dict(full_name='foreign/beatquay'))]:
            changed=copy.deepcopy(run);changed[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):subject.verify_run(changed,b)

    def test_artifact_paths_are_literal_regular_windows_safe_names(self):
        subject=self.subject()
        self.assertEqual(subject.relative_path('build-evidence/consumer/Evening Pulse.mmp'),'build-evidence/consumer/Evening Pulse.mmp')
        for value in ('../file','/file','a\\b','a//b','a/./b','a/../b','C:/file','a:stream','CON','x/NUL.txt','x.','x ',''):
            with self.subTest(value=value),self.assertRaises(ValueError):subject.relative_path(value)

    def test_complete_original_export_context_and_typed_flags(self):
        subject=self.subject();b=self.approved()['qualified']
        record=dict(schemaVersion=1,sourceCommit=b['source_commit'],workflowRunId='1',workflowRunAttempt='1',
            repository='hashfunction/beatquay',workflowEvent='workflow_dispatch',
            unsigned=True,storeIdentityInstalledAndVerified=True,bothCompleteInstalledLifecyclesVerified=True,
            exactCurrentNativeSourceDeliveryVerified=True,publicBinaryRelease=False,storeSubmitted=False,
            wackTested=False,physicalAudioVerified=False,output=dict(file=subject.PACKAGE_NAME,**b['package']))
        self.assertTrue(hasattr(subject,'verify_export_context'),'Export receipt context verifier is not implemented')
        subject.verify_export_context(record,b)
        for key in record:
            changed=copy.deepcopy(record)
            if type(changed[key]) is bool:changed[key]=int(changed[key])
            else:changed[key]=None
            with self.subTest(key=key),self.assertRaises(ValueError):subject.verify_export_context(changed,b)
        b['package']['bytes']=1;record['output']['bytes']=True
        with self.assertRaises(ValueError):subject.verify_export_context(record,b)


if __name__=='__main__':unittest.main()
