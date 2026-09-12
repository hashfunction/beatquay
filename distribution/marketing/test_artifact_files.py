"""Bounded extraction uses actual ZIPs and exclusive local output paths."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile


class ArtifactTests(unittest.TestCase):
    def setUp(self):
        path=Path(__file__).with_name('artifact_files.py')
        self.assertTrue(path.is_file(),'Bounded artifact extraction is not implemented')
        spec=importlib.util.spec_from_file_location('marketing_artifacts_subject',path)
        self.subject=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.subject)
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name).resolve()

    def archive(self,names):
        path=self.root/'input.zip'
        with zipfile.ZipFile(path,'w') as out:
            for name,body in names:out.writestr(name,body)
        return path

    def test_exact_regular_contents_and_original_bytes(self):
        archive=self.archive([('file.json',b'original'),('nested/note.mmp',b'music')])
        self.subject.extract(archive,self.root/'out',1000,{'file.json','nested/note.mmp'})
        self.assertEqual((self.root/'out/file.json').read_bytes(),b'original')
        with self.assertRaises(FileExistsError):self.subject.extract(archive,self.root/'out',1000)
        self.assertEqual((self.root/'out/nested/note.mmp').read_bytes(),b'music')

    def test_bad_inventory_fails_before_any_output_creation(self):
        cases=[[('../escape',b'x')],[('FILE',b'x'),('file',b'y')],[('x/',b'')],[('x',b'a'*1001)],
               [('extra.cer',b'certificate')],[('NUL.txt',b'x')]]
        for index,rows in enumerate(cases):
            archive=self.archive(rows);output=self.root/str(index)
            exact={'file.json'} if index==4 else None
            with self.subTest(index=index),self.assertRaises(ValueError):self.subject.extract(archive,output,1000,exact)
            self.assertFalse(output.exists())
        link=zipfile.ZipInfo('link');link.create_system=3;link.external_attr=0o120777<<16
        archive=self.archive([(link,b'outside')])
        with self.assertRaises(ValueError):self.subject.extract(archive,self.root/'link',1000)
        self.assertFalse((self.root/'link').exists())

    def test_reparse_ancestor_and_invalid_byte_bound_refused(self):
        archive=self.archive([('file',b'original')]);target=self.root/'target';target.mkdir()
        alias=self.root/'alias';alias.symlink_to(target,target_is_directory=True)
        with self.assertRaises(ValueError):self.subject.extract(archive,alias/'out',1000)
        for bound in (True,0,-1):
            with self.assertRaises(ValueError):self.subject.extract(archive,self.root/'out',bound)


if __name__=='__main__':unittest.main()
