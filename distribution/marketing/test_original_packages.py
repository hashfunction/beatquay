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

    def remove_notices_omitted_by_original_artifact(self):
        # The real metadata artifact uploads these suffixes, not all notice
        # originals. The generated package fixture contains the real source
        # notice tree and puts every original into the actual ZIP payload.
        retained = {'.json', '.txt', '.xml', '.log', '.png'}
        removed = []
        for relative in self.original['records']['store']['evidenceInputs']:
            path = self.root / relative
            if relative.startswith('notices/') and path.suffix not in retained:
                path.unlink(); removed.append(relative)
        self.assertIn('notices/native/COMBINED-LICENSE.md', removed)
        self.assertGreater(len(removed), 1)
        return removed

    def test_original_artifact_omissions_use_exact_packaged_notice_bytes(self):
        removed = self.remove_notices_omitted_by_original_artifact()
        self.assertEqual(self.verify(), self.original['records'])
        self.assertTrue(all(not (self.root / name).exists() for name in removed))

    def test_present_notice_tamper_and_missing_non_notice_still_refused(self):
        notice = self.root / 'notices/native/COMBINED-LICENSE.md'
        original = notice.read_bytes(); notice.write_bytes(original + b'changed')
        with self.assertRaises(ValueError): self.verify()
        notice.write_bytes(original)
        self.remove_notices_omitted_by_original_artifact()
        (self.root / 'candidate-inputs.json').unlink()
        with self.assertRaises((ValueError, FileNotFoundError)): self.verify()

    def test_omitted_notice_requires_unchanged_actual_store_payload(self):
        self.remove_notices_omitted_by_original_artifact()
        package = self.fixture.packages['store']; changed = package.with_suffix('.changed')
        target = 'licenses/dependencies/native/COMBINED-LICENSE.md'
        with zipfile.ZipFile(package) as original, zipfile.ZipFile(changed, 'w') as output:
            self.assertIn(target, original.namelist())
            for entry in original.infolist():
                data = original.read(entry)
                output.writestr(entry, data + b'changed' if entry.filename == target else data)
        changed.replace(package)
        with self.assertRaises(ValueError): self.verify()

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
