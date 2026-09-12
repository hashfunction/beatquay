import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import sys
import subprocess

SOURCE=Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SOURCE/'distribution'))
spec=importlib.util.spec_from_file_location('native_source',SOURCE/'distribution/native_source.py')
native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)


class NativeSourceTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.root=Path(temp.name).resolve()
        self.release=native.load_release(SOURCE/'distribution/native-source/source-release.json')

    def test_exact_seventeen_owners_preserve_compiled_and_build_only_distinction(self):
        self.assertEqual(len(self.release['archives']),17)
        by={x['owner']:x for x in self.release['archives']}
        self.assertEqual(by['ringbuffer']['role'],'compiled-in-core')
        self.assertEqual(by['qttools']['unexpandedGitlinks'],{'src/assistant/qlitehtml':'3fe5821dad98747d6e41c9ed54b86c3d0eee9daf'})
        self.assertEqual(by['qttools']['stageFiles'],[])
        self.assertFalse(self.release['correspondingSourceComplete'])
        originals=native.original_notices(SOURCE/'distribution/native-source')
        self.assertEqual(originals['GPL-3.0.txt'], originals['notices/app-submodules/ringbuffer/LICENSE.txt'])
        self.assertIn(b'$QT_BEGIN_LICENSE:BSD$',originals['notices/app/include/ControlLayout.h'])

    def test_changed_archive_size_sha256_sha512_and_symlink_rejected(self):
        release=copy.deepcopy(self.release); item=release['archives'][0]; data=b'exact archive fixture'
        item.update(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),sha512=hashlib.sha512(data).hexdigest())
        path=self.root/item['file'];path.write_bytes(data)
        self.assertEqual(len(native.verify_archives(release,self.root,{item['owner']})),1)
        for key,value in [('bytes',len(data)+1),('sha256','0'*64),('sha512','0'*128)]:
            saved=item[key];item[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):native.verify_archives(release,self.root,{item['owner']})
            item[key]=saved
        foreign=self.root/'foreign';path.rename(foreign);path.symlink_to(foreign)
        with self.assertRaises(ValueError):native.verify_archives(release,self.root,{item['owner']})
        self.assertEqual(foreign.read_bytes(),data)

    def test_missing_duplicate_and_false_publication_manifest_rejected(self):
        for mutation in ('missing','duplicate','published'):
            release=copy.deepcopy(self.release)
            if mutation=='missing':release['archives'].pop()
            elif mutation=='duplicate':release['archives'][0]=release['archives'][1]
            else:release['deliveryStatus']='published'
            file=self.root/(mutation+'.json');file.write_text(json.dumps(release))
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):native.load_release(file)

    def test_notice_tamper_missing_and_extra_fail(self):
        root=self.root/'bundle';shutil.copytree(SOURCE/'distribution/native-source',root)
        file=root/'notices/app-submodules/ringbuffer/LICENSE.txt';raw=file.read_bytes();file.write_bytes(raw+b'changed')
        with self.assertRaisesRegex(ValueError,'hash mismatch'):native.original_notices(root)
        file.write_bytes(raw);extra=root/'notices/foreign.txt';extra.write_bytes(b'foreign')
        with self.assertRaisesRegex(ValueError,'unexpected'):native.original_notices(root)
        extra.unlink();file.unlink()
        with self.assertRaises((OSError,ValueError)):native.original_notices(root)

    def test_current_build_pins_and_download_bytes_must_match(self):
        source=self.root/'source'; evidence=self.root/'evidence';evidence.mkdir()
        for name in ('distribution/candidate-inputs.json','distribution/qt-notices/6.11.2/manifest.json'):
            path=source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes((SOURCE/name).read_bytes())
        (evidence/'qt-downloads.json').write_text(json.dumps(self.release['qtBinaryInputs']))
        downloads=[{k:x[k] for k in ('file','bytes','sha256')} for x in self.release['archives'] if 'recipeSha512' in x]
        path=evidence/'dependency-downloads.json';path.write_text(json.dumps(downloads))
        native.validate_current_inputs(source,evidence,self.release)
        for key,value in [('bytes',downloads[0]['bytes']+1),('sha256','0'*64)]:
            changed=copy.deepcopy(downloads);changed[0][key]=value;path.write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError,'vcpkg source'):native.validate_current_inputs(source,evidence,self.release)
        path.write_text(json.dumps(downloads))
        lock_path=source/'distribution/candidate-inputs.json';lock=json.loads(lock_path.read_bytes())
        lock['vcpkg']['commit']='0'*40;lock_path.write_text(json.dumps(lock))
        with self.assertRaisesRegex(ValueError,'dependency pins'):native.validate_current_inputs(source,evidence,self.release)

    def test_original_notice_bytes_survive_git_index_and_windows_style_checkout(self):
        names=['distribution/native-source/notices/app-submodules/hiir/license.txt',
               'distribution/qt-notices/6.11.2/qtbase/src/3rdparty/forkfd/qt_attribution.json']
        subprocess.run(['git','init','--quiet',str(self.root)],check=True,capture_output=True)
        subprocess.run(['git','-C',str(self.root),'config','core.autocrlf','true'],check=True)
        (self.root/'.gitattributes').write_bytes((SOURCE/'.gitattributes').read_bytes())
        for name in names:
            path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes((SOURCE/name).read_bytes())
        subprocess.run(['git','-C',str(self.root),'add','.gitattributes',*names],check=True,capture_output=True)
        for name in names:
            expected=(SOURCE/name).read_bytes()
            self.assertEqual(subprocess.check_output(['git','-C',str(self.root),'show',':'+name]),expected)
            (self.root/name).unlink()
        subprocess.run(['git','-C',str(self.root),'checkout','--',*names],check=True,capture_output=True)
        for name in names:self.assertEqual((self.root/name).read_bytes(),(SOURCE/name).read_bytes())

    def test_collection_binds_actual_build_and_refuses_output_replacement(self):
        source=self.root/'source'; evidence=self.root/'evidence';evidence.mkdir()
        bundle=source/'distribution/native-source';shutil.copytree(SOURCE/'distribution/native-source',bundle)
        for name in ('distribution/candidate-inputs.json','distribution/qt-notices/6.11.2/manifest.json'):
            path=source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes((SOURCE/name).read_bytes())
        (evidence/'qt-downloads.json').write_text(json.dumps(self.release['qtBinaryInputs']))
        downloads=self.root/'downloads';downloads.mkdir();rows=[]
        for archive in self.release['archives']:
            if 'recipeSha512' not in archive:continue
            data=('fixture source '+archive['owner']).encode();(downloads/archive['file']).write_bytes(data)
            sha512=hashlib.sha512(data).hexdigest()
            archive.update(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),sha512=sha512,recipeSha512=sha512)
            rows.append({k:archive[k] for k in ('file','bytes','sha256')})
        (bundle/'source-release.json').write_text(json.dumps(self.release))
        (evidence/'dependency-downloads.json').write_text(json.dumps(rows))
        commit='a'*40;result={'source_commit':commit,'built':True}
        result_path=evidence/'result.json';output=evidence/'notices/native'
        for change in ({'source_commit':'b'*40},{'built':False},{'built':'true'}):
            result_path.write_text(json.dumps(dict(result,**change)))
            with self.subTest(change=change),self.assertRaisesRegex(ValueError,'actual successful native build'):
                native.collect(source,evidence,downloads,output,commit)
            self.assertFalse(output.exists())
        result_path.write_text(json.dumps(result))
        receipt=native.collect(source,evidence,downloads,output,commit)
        self.assertEqual(len(receipt['actualVcpkgSourceArchives']),11)
        self.assertEqual(receipt['sourceCommit'],commit);self.assertFalse(receipt['publicationVerified'])
        for name,raw in native.original_notices(bundle).items():self.assertEqual((output/name).read_bytes(),raw)
        saved=(output/'build-source.json').read_bytes()
        with self.assertRaisesRegex(ValueError,'output exists'):native.collect(source,evidence,downloads,output,commit)
        self.assertEqual((output/'build-source.json').read_bytes(),saved)

    def test_each_staged_pe_requires_a_source_or_verified_microsoft_owner(self):
        files=['beatsprig.exe','plugins/kicker.dll','Qt6Core.dll','libmp3lame.DLL','msvcp140.dll','data/image.png']
        owners=native.stage_owners(self.release,files,[{'path':'msvcp140.dll'}])
        self.assertEqual(owners['beatsprig.exe'],['application','hiir','ringbuffer'])
        self.assertEqual(owners['libmp3lame.DLL'],['mp3lame'])
        self.assertEqual(owners['msvcp140.dll'],['microsoft-verified-redist'])
        self.assertNotIn('data/image.png',owners)
        for unknown in ('foreign.dll','plugins/unknown.dll','opengl32sw.dll','qdoc.exe','vcruntime140.dll'):
            with self.subTest(unknown=unknown),self.assertRaisesRegex(ValueError,'source owner'):
                native.stage_owners(self.release,files+[unknown],[{'path':'msvcp140.dll'}])


if __name__=='__main__':unittest.main()
