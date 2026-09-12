"""Anonymous byte verification of the immutable reviewed native source delivery."""
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import ssl
import time
from urllib.parse import urlsplit
from urllib.request import HTTPSHandler, HTTPRedirectHandler, Request, build_opener

import msix_qualification as package
from store_workflow_evidence import digest, integer, json_bytes, load, read, same

REPOSITORY='https://github.com/hashfunction/beatquay'
TAG='beatsprig-native-source-1.0.1'
BASE=REPOSITORY+'/releases/download/'+TAG+'/'
RECEIPT_SHA='9b25fa44c88cc4c41605fdc1d08c3d722338499d44d53d15b0904e76bfd5543a'
ADDITIONAL={'BeatSprig-1.0.1-original-notices.tar.gz','SOURCE.md','source-release.json','source-delivery-inputs.json'}


def allowed_url(url):
    parsed=urlsplit(url)
    if parsed.scheme!='https' or parsed.username or parsed.password or parsed.hostname not in (
        'github.com','api.github.com','release-assets.githubusercontent.com','objects.githubusercontent.com'):
        raise ValueError('Public source download left the HTTPS GitHub boundary')


class PublicRedirect(HTTPRedirectHandler):
    def redirect_request(self,request,fp,code,msg,headers,newurl):
        allowed_url(newurl)
        return super().redirect_request(request,fp,code,msg,headers,newurl)


def download(url, maximum, retain=False):
    """Stream once without credentials, cookies or persistent archive copies."""
    allowed_url(url);integer(maximum,1,'download bound')
    opener=build_opener(HTTPSHandler(context=ssl.create_default_context()),PublicRedirect())
    accept='application/vnd.github+json' if urlsplit(url).hostname=='api.github.com' else 'application/octet-stream'
    request=Request(url,headers={'User-Agent':'BeatSprig-source-verification/1.0.1','Accept':accept})
    sha256=hashlib.sha256();sha512=hashlib.sha512();size=0;data=[];started=time.monotonic()
    with opener.open(request,timeout=30) as response:
        if response.status!=200: raise ValueError('Public source URL did not return HTTP 200')
        allowed_url(response.url)
        for chunk in iter(lambda:response.read(1024*1024),b''):
            size+=len(chunk)
            if size>maximum or time.monotonic()-started>300: raise ValueError('Public source download exceeded its byte/time bound')
            sha256.update(chunk);sha512.update(chunk)
            if retain:data.append(chunk)
    return {'bytes':size,'sha256':sha256.hexdigest(),'sha512':sha512.hexdigest()}, b''.join(data) if retain else None


def checked_download(url, expected, fetch, retain=False):
    actual,data=fetch(url,integer(expected.get('bytes'),1,'published length'),retain)
    for key in ('bytes','sha256','sha512'):
        if key in expected:same(actual.get(key),expected[key],'public asset '+key)
    if retain:
        if not isinstance(data,bytes):raise ValueError('Missing downloaded metadata body')
        same({'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()},
             {key:actual[key] for key in ('bytes','sha256')},'downloaded metadata body')
    return actual,data


def verify_public_tree(commit, tree, fetch=download):
    import re
    if not re.fullmatch('[0-9a-f]{40}',commit) or not re.fullmatch('[0-9a-f]{40}',tree):raise ValueError('Exact public application commit/tree required')
    url='https://api.github.com/repos/hashfunction/beatquay/git/commits/'+commit
    measured,data=fetch(url,1024*1024,True);body=json_bytes(data)
    same(body.get('sha'),commit,'anonymous public Git commit');same(body.get('tree',{}).get('sha'),tree,'anonymous public Git tree')
    return dict(commit=commit,tree=tree,url=REPOSITORY+'/tree/'+commit,anonymousCommitApi=url,response=measured)


def verify_publication(source, payload, fetch=download):
    source=Path(source);pin_path=source/'distribution/native-source-publication.json';pin=load(pin_path)
    same(pin.get('schemaVersion'),1,'publication pin schema');same(pin.get('repository'),REPOSITORY,'publication repository')
    same(pin.get('tag'),TAG,'publication tag');same(pin.get('releaseId'),387570510,'publication release')
    same(pin.get('publicReceipt'),{'url':BASE+'public-source-delivery.json','bytes':13180,'sha256':RECEIPT_SHA},'reviewed public receipt pin')
    measured,data=checked_download(pin['publicReceipt']['url'],pin['publicReceipt'],fetch,True)
    receipt=json_bytes(data)
    for key,value in {'schemaVersion':1,'mode':'public','releaseId':pin['releaseId'],'tag':TAG,'releaseUrl':REPOSITORY+'/releases/tag/'+TAG,
        'applicationSourceCommit':pin['sourcePublicationCommit'],'applicationSourceTree':pin['sourcePublicationTree'],
        'allPublicSourceAssetsVerified':True,'anonymous':True,'credentialsSent':False,'tlsCertificateVerification':True,
        'verifiedSourceArchiveCount':17,'verifiedSourceArchiveBytes':108354372,'correspondingSourceComplete':False,
        'finalBinaryBindingVerified':False,'windowsQualificationClaimed':False}.items():same(receipt.get(key),value,'published receipt '+key)
    rows=receipt.get('verifiedAssets')
    if not isinstance(rows,list) or len(rows)!=21 or len({row['name'] for row in rows})!=21:raise ValueError('Published source asset set differs')
    assets={row['name']:row for row in rows}
    release_path=source/'distribution/native-source/source-release.json'
    release=package.native_source.load_release(release_path)
    same(package.file_record(release_path)['sha256'],pin.get('sourceReleaseManifestSha256'),'unchanged native source manifest')
    if set(assets)!={row['file'] for row in release['archives']}|ADDITIONAL:raise ValueError('Missing or unreviewed public source assets')
    for row in rows:
        same(row.get('publicUrl'),BASE+row['name'],'immutable public asset URL')
        same(row.get('githubDigest'),'sha256:'+digest(row.get('sha256')),'GitHub published digest')
    for row in release['archives']:
        published=assets[row['file']]
        for key in ('bytes','sha256','sha512'):same(published.get(key),row[key],'native source archive '+row['owner']+'/'+key)
    bodies={};checked=[]
    for name,row in assets.items():
        measured,body=checked_download(row['publicUrl'],row,fetch,name in ('source-delivery-inputs.json','source-release.json'))
        checked.append(dict(name=name,url=row['publicUrl'],**measured))
        if body is not None:bodies[name]=body
    same(bodies['source-release.json'],read(release_path),'published native source manifest bytes')
    inputs=json_bytes(bodies['source-delivery-inputs.json'])
    for key,value in {'schemaVersion':1,'repository':REPOSITORY,'tag':TAG,'applicationSourceCommit':pin['sourcePublicationCommit'],
        'applicationSourceTree':pin['sourcePublicationTree'],'publicVerificationPending':True,'correspondingSourceComplete':False,
        'finalBinaryBindingVerified':False}.items():same(inputs.get(key),value,'historical publication inputs '+key)
    expected_archives=[dict(owner=row['owner'],name=row['file'],publicUrl=row['proposedDownloadUrl'],
                           **{key:row[key] for key in ('bytes','sha256','sha512')}) for row in release['archives']]
    same(inputs.get('sourceArchives'),expected_archives,'published source-owner mapping')
    members=inputs.get('originalNoticeMembers')
    if not isinstance(members,dict) or len(members)!=259:raise ValueError('Published original notice inventory differs')
    for name,item in members.items():
        package._checked_path(name);relative=package._checked_path(item.get('gitPath'))
        original=read(source/relative)
        expected={'bytes':item['bytes'],'sha256':item['sha256']}
        same({'bytes':len(original),'sha256':hashlib.sha256(original).hexdigest()},expected,'current original notice '+relative)
        same(hashlib.sha1(b'blob '+str(len(original)).encode()+b'\0'+original).hexdigest(),item['gitBlob'],'original Git notice blob')
        same(payload.get(name),expected,'packaged published notice '+name)
    return dict(publicationPin=package.file_record(pin_path),publicReceipt={'url':pin['publicReceipt']['url'],**pin['publicReceipt']},
        historicalPublicationCommit=pin['sourcePublicationCommit'],historicalPublicationTree=pin['sourcePublicationTree'],
        verifiedAssets=checked,verifiedSourceArchiveCount=17,verifiedSourceArchiveBytes=108354372,
        originalNoticeMembersVerified=259,unchangedNativeSourceManifest=package.file_record(release_path),
        anonymous=True,credentialsSent=False,tlsCertificateVerification=True,archivesRetainedLocally=False,
        verifiedAtUtc=datetime.now(timezone.utc).isoformat())
