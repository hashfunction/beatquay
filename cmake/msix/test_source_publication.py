"""Original public receipt bytes and controlled network boundaries; no fake release publication."""
import copy
import hashlib
import io
from pathlib import Path
import unittest
from unittest.mock import patch

import source_publication as subject
from store_workflow_evidence import json_bytes,read

SOURCE=Path(__file__).resolve().parents[2]
FIXTURE=Path(__file__).parent/'fixtures/public-source-20260912'


class SourcePublicationTests(unittest.TestCase):
    def setUp(self):
        self.receipt=json_bytes(read(FIXTURE/'public-source-delivery.json'))
        self.inputs=json_bytes(read(FIXTURE/'source-delivery-inputs.json'))
        self.payload={name:{key:row[key] for key in ('bytes','sha256')} for name,row in self.inputs['originalNoticeMembers'].items()}
        self.calls=[]
    def fetch(self,url,maximum,retain):
        self.calls.append((url,maximum,retain))
        if url==subject.BASE+'public-source-delivery.json':data=read(FIXTURE/'public-source-delivery.json')
        else:
            row=next(x for x in self.receipt['verifiedAssets'] if x['publicUrl']==url)
            if not retain:return {key:row[key] for key in ('bytes','sha256','sha512')},None
            data=read(FIXTURE/'source-delivery-inputs.json') if row['name']=='source-delivery-inputs.json' else read(SOURCE/'distribution/native-source/source-release.json')
        return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'sha512':hashlib.sha512(data).hexdigest()},data
    def test_current_original_notices_and_all_17_source_rows_bind_original_published_receipt(self):
        got=subject.verify_publication(SOURCE,self.payload,self.fetch)
        self.assertEqual(got['verifiedSourceArchiveCount'],17);self.assertEqual(got['originalNoticeMembersVerified'],259)
        self.assertEqual(len(self.calls),22);self.assertEqual(len(got['verifiedAssets']),21)
        self.assertFalse(got['credentialsSent']);self.assertFalse(got['archivesRetainedLocally'])
    def test_asset_corruption_missing_delivery_and_changed_packaged_notice_fail(self):
        for kind in ('size','sha256','unavailable','notice'):
            with self.subTest(kind=kind):
                payload=copy.deepcopy(self.payload)
                if kind=='notice':payload[next(iter(payload))]['sha256']='0'*64
                def fetch(url,maximum,retain):
                    actual,data=self.fetch(url,maximum,retain)
                    if url.endswith('fftw-3.3.11.tar.gz'):
                        if kind=='size':actual['bytes']-=1
                        if kind=='sha256':actual['sha256']='0'*64
                        if kind=='unavailable':raise OSError('public source unavailable')
                    return actual,data
                with self.assertRaises((ValueError,OSError)):subject.verify_publication(SOURCE,payload,fetch)
    def test_actual_streaming_packet_digest_and_https_redirect_boundary(self):
        data=b'original public fixture bytes'*200
        class Response(io.BytesIO):status=200;url=subject.BASE+'fixture.tar.gz'
        class Opener:
            def open(inner,request,timeout):
                self.assertNotIn('Authorization',request.headers);self.assertNotIn('Cookie',request.headers)
                self.assertEqual(timeout,30);self.assertEqual(request.get_method(),'GET')
                expected='application/vnd.github+json' if request.host=='api.github.com' else 'application/octet-stream'
                self.assertEqual(request.get_header('Accept'),expected)
                return Response(data)
        with patch.object(subject,'build_opener',return_value=Opener()):
            actual,body=subject.download(subject.BASE+'fixture.tar.gz',len(data),True)
            self.assertEqual(actual,{'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'sha512':hashlib.sha512(data).hexdigest()})
            self.assertEqual(body,data)
            subject.download('https://api.github.com/repos/hashfunction/beatquay/git/commits/'+('a'*40),len(data),True)
            with self.assertRaises(ValueError):subject.download(subject.BASE+'fixture.tar.gz',len(data)-1)
        for url in ('http://github.com/x','https://foreign.example/source','https://token@github.com/source'):
            with self.assertRaises(ValueError):subject.allowed_url(url)
    def test_exact_anonymous_public_git_commit_and_tree(self):
        commit='a'*40;tree='b'*40
        for field,value in [(None,None),('sha','c'*40),('tree',{'sha':'d'*40})]:
            def fetch(url,maximum,retain):
                import json
                record={'sha':commit,'tree':{'sha':tree}}
                if field:record[field]=value
                data=json.dumps(record).encode()
                return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()},data
            if field:
                with self.assertRaises(ValueError):subject.verify_public_tree(commit,tree,fetch)
            else:self.assertEqual(subject.verify_public_tree(commit,tree,fetch)['tree'],tree)


if __name__=='__main__':unittest.main()
