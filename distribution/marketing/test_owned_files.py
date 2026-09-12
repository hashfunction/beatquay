"""Real file cleanup boundary: only the exact created and sealed tree is removed."""
import tempfile
import unittest
from pathlib import Path
import owned_files as files

class OwnedFilesTests(unittest.TestCase):
 def test_exclusive_and_changed_tree(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder).resolve()/'demo';record=files.create(root,'demo')
   with self.assertRaises(Exception):files.create(root,'demo')
   (root/'Evening Pulse').mkdir();(root/'Evening Pulse/Evening Pulse.mmp').write_bytes(b'original')
   seal=files.seal(record)
   with self.assertRaises(Exception):files.cleanup(record,seal,False)
   (root/'Evening Pulse/Evening Pulse.mmp').write_bytes(b'changed')
   with self.assertRaises(Exception):files.cleanup(record,seal,True)
   self.assertTrue(root.exists())
   (root/'Evening Pulse/Evening Pulse.mmp').write_bytes(b'original')
   seal=files.seal(record);files.cleanup(record,seal,True);self.assertFalse(root.exists())
 def test_foreign_and_symlink_preserved(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder).resolve()/'demo';record=files.create(root,'demo')
   (root/'foreign.txt').write_text('preserve')
   with self.assertRaises(Exception):files.seal(record)
   (root/'foreign.txt').unlink();outside=Path(folder).resolve()/'outside';outside.write_text('safe')
   (root/'.beatquay-profile-initial.xml').symlink_to(outside)
   with self.assertRaises(Exception):files.seal(record)
   self.assertEqual(outside.read_text(),'safe')
 def test_marker_and_directory_replacement(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder).resolve()/'demo';record=files.create(root,'demo');seal=files.seal(record)
   (root/files.MARKER).write_text('foreign')
   with self.assertRaises(Exception):files.cleanup(record,seal,True)
   self.assertTrue(root.exists())

if __name__=='__main__':unittest.main()
