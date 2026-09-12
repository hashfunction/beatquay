"""Real archive/source/SDK files in a generated package fixture, not Windows proof."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest
import zipfile

SOURCE=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(SOURCE/'cmake/msix'))
import test_export_store_package as fixtures


class OriginalPackageTests(unittest.TestCase):
    def setUp(self):
        path=Path(__file__).with_name('verify_inputs.py')
        spec=importlib.util.spec_from_file_location('capture_package_subject',path)
        self.module=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.module)
        self.assertTrue(hasattr(self.module,'verify_original_packages'),'Original package capture verifier is not implemented')
        self.fixture=fixtures.PackageBoundaryTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.original=self.fixture.verify();self.root=self.fixture.fixture.evidence
        self.bound=dict(source_commit=self.fixture.fixture.commit,workflow_run_id=self.fixture.context['workflowRunId'],
                        workflow_run_attempt=self.fixture.context['workflowRunAttempt'])
        self.ready=dict(packageRecord=self.original['records']['store'],originalPackageInputs=self.original['files'],
                        originalSdkTools=self.original['tools'])

    def verify(self,ready=None):
        return self.module.verify_original_packages(self.fixture.source,self.root,self.fixture.packages['store'],
            self.ready if ready is None else ready,self.bound,fixtures.subject.package,fixtures.subject.evidence)

    def test_full_original_package_source_helpers_payload_and_sdk(self):
        self.assertEqual(self.verify(),self.original['records'])
        for path in (self.fixture.sign,self.fixture.source/'cmake/msix/consumer-workflow.ps1',self.root/'msix-package-record.json'):
            data=path.read_bytes();path.write_bytes(data+b'changed')
            with self.subTest(path=str(path)),self.assertRaises(ValueError):self.verify()
            path.write_bytes(data)

    def test_partial_or_stale_records_and_signed_container_refused(self):
        self.verify()
        for field,value in [('originalPackageInputs',{}),('originalSdkTools',{}),('packageRecord',{})]:
            altered=copy.deepcopy(self.ready);altered[field]=value
            with self.subTest(field=field),self.assertRaises((ValueError,KeyError)):self.verify(altered)
        self.bound['workflow_run_attempt']='1'
        with self.assertRaises(ValueError):self.verify()
        self.bound['workflow_run_attempt']=self.fixture.context['workflowRunAttempt']
        with zipfile.ZipFile(self.fixture.packages['store'],'a') as archive:archive.writestr('AppxSignature.p7x',b'signature')
        with self.assertRaises(ValueError):self.verify()


if __name__=='__main__':unittest.main()
