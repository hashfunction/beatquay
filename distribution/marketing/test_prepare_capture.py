"""Preparation remains fail-closed before network/filesystem mutations."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class PreparationTests(unittest.TestCase):
    def test_unbound_cli_does_not_create_inputs_or_binding_output(self):
        folder=Path(__file__).parent;program=folder/'prepare_capture.py'
        self.assertTrue(program.is_file(),'Capture preparation command is not implemented')
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve();output=root/'inputs';binding_output=root/'github-output'
            for arguments in ([str(program),'--output',str(output),'--qualified-source',str(root)],
                              [str(folder/'capture_checks.py'),'--binding-output',str(binding_output)]):
                result=subprocess.run([sys.executable,*arguments],text=True,capture_output=True)
                self.assertNotEqual(result.returncode,0)
                self.assertIn('reviewed successful',result.stderr)
                self.assertFalse(output.exists());self.assertFalse(binding_output.exists())


if __name__=='__main__':unittest.main()

class ArtifactMetadataTests(unittest.TestCase):
    def test_exact_artifact_and_refused_metadata_never_downloads(self):
        import io,json,zipfile
        from unittest.mock import patch
        import prepare_capture as subject
        bound={'workflow_run_id':'123','source_commit':'a'*40}
        zipped=io.BytesIO()
        with zipfile.ZipFile(zipped,'w') as archive:archive.writestr('original.json',b'{"real":true}')
        data=zipped.getvalue();original=dict(id=789,name='exact',expired=False,workflow_run=dict(id=123,head_sha='a'*40),size_in_bytes=len(data))
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve();calls=[]
            def download(args,stdout,**kwargs):calls.append(args);stdout.write(data)
            with patch.object(subject,'gh_json',return_value=original),patch.object(subject.subprocess,'run',side_effect=download):
                subject.artifact(789,'exact',root/'actual',10000,bound,{'original.json'})
            self.assertEqual((root/'actual/original.json').read_bytes(),b'{"real":true}');self.assertEqual(len(calls),1)
            for key,value in [('id',790),('expired',True),('name','foreign'),('size_in_bytes',True),('workflow_run',dict(id=124,head_sha='a'*40))]:
                changed=dict(original);changed[key]=value
                with patch.object(subject,'gh_json',return_value=changed),patch.object(subject.subprocess,'run') as runner,self.assertRaises(ValueError):
                    subject.artifact(789,'exact',root/'refused',10000,bound)
                runner.assert_not_called();self.assertFalse((root/'refused').exists())
            (root/'collision.zip').write_bytes(b'preserve')
            with patch.object(subject,'gh_json',return_value=original),self.assertRaises(FileExistsError):subject.artifact(789,'exact',root/'collision',10000,bound)
            self.assertEqual((root/'collision.zip').read_bytes(),b'preserve')
