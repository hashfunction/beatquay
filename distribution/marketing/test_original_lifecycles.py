"""Generated complete fixture exercises capture joins; never native evidence."""
import copy
import importlib.util
from pathlib import Path
import sys
import unittest

SOURCE=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(SOURCE/'cmake/msix'))
import test_store_workflow_evidence as fixtures


class OriginalLifecycleTests(unittest.TestCase):
    def setUp(self):
        path=Path(__file__).with_name('verify_inputs.py')
        self.assertTrue(path.is_file(),'Original whole-lifecycle capture verifier is not implemented')
        spec=importlib.util.spec_from_file_location('capture_inputs_subject',path)
        self.module=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.module)
        self.fixture=fixtures.LifecycleTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.bound=dict(source_commit=self.fixture.commit,workflow_run_id=self.fixture.run,workflow_run_attempt=self.fixture.attempt)
        self.original=self.fixture.verify()

    def verify(self,original=None,bound=None):
        return self.module.verify_original_lifecycles(self.fixture.root,self.fixture.records,SOURCE,
            self.bound if bound is None else bound,self.original if original is None else original,fixtures.subject)

    def test_complete_originals_and_stale_partial_export_summary_refused(self):
        self.assertEqual(self.verify(),self.original)
        for mode in ('qualification','store'):
            altered=copy.deepcopy(self.original);altered[mode]['projectVerification']['tempo']=112
            with self.subTest(mode=mode),self.assertRaises(ValueError):self.verify(altered)
        for field,value in [('workflow_run_attempt','2'),('workflow_run_id','1'),('source_commit','0'*40)]:
            changed=dict(self.bound);changed[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):self.verify(bound=changed)
        with self.assertRaises(ValueError):self.verify({'store':self.original['store']})

    def test_original_failed_and_disagreeing_embedded_receipts_refused(self):
        path=self.fixture.root/'msix-store-install/installation-qualification.json'
        original=path.read_bytes();row=fixtures.subject.json_bytes(original)
        row['project_export_workflow']['acceptance']=False
        path.write_text(__import__('json').dumps(row))
        with self.assertRaises(ValueError):self.verify()
        path.write_bytes(original)
        path=self.fixture.root/'msix-install/installation-qualification.json'
        path.write_bytes(self.fixture.originals['msix-install/installation-qualification.json'])
        with self.assertRaises(ValueError):self.verify()


if __name__=='__main__':unittest.main()
