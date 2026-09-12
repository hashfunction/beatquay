#!/usr/bin/env python3
"""Export one exact unsigned Store package after both installed lifecycles pass.

No installation, signing, GitHub upload or Store submission is performed here.
The command is deliberately usable only in the reviewed Windows workflow run.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

import msix_qualification as package
import source_publication as publication
import store_workflow_evidence as evidence

OUTPUT_PACKAGE='BeatSprig_1.0.1.0_x64.msix'
OUTPUT_RECEIPT='BeatSprig_1.0.1.0_x64.export.json'
MODES={'qualification':('msix-package-record.json','msix-install'),
       'store':('msix-store-package-record.json','msix-store-install')}


def workflow_context(reviewed, environ, platform):
    if not isinstance(reviewed,str) or not re.fullmatch('[0-9a-f]{40}',reviewed):
        raise ValueError('An exact reviewed public application commit is required')
    expected={'CI':'true','GITHUB_ACTIONS':'true','GITHUB_REPOSITORY':'hashfunction/beatquay',
              'GITHUB_EVENT_NAME':'workflow_dispatch','BEATSPRIG_EXPORT_STORE_PACKAGE':'true','GITHUB_SHA':reviewed}
    if platform!='win32' or any(environ.get(k)!=v for k,v in expected.items()):
        raise ValueError('Unsigned export requires the explicit reviewed Windows workflow dispatch')
    run=environ.get('GITHUB_RUN_ID');attempt=environ.get('GITHUB_RUN_ATTEMPT')
    package.validate_run_binding(dict(workflowRunId=run,workflowRunAttempt=attempt),run,attempt)
    return dict(sourceCommit=reviewed,workflowRunId=run,workflowRunAttempt=attempt,
        repository='hashfunction/beatquay',workflowEvent='workflow_dispatch')


def local_source(source, reviewed):
    def git(*args):
        return subprocess.run(['git','-C',str(source),*args],check=True,shell=False,
                              capture_output=True,text=True,timeout=60).stdout.strip()
    if git('rev-parse','HEAD')!=reviewed:raise ValueError('Checkout differs from the reviewed public commit')
    # Avoid the Windows shell caret syntax; this returns the same exact Git tree.
    tree=git('show','-s','--format=%T','HEAD')
    if not re.fullmatch('[0-9a-f]{40}',tree):raise ValueError('Missing exact source Git tree')
    if git('status','--porcelain=v1','--untracked-files=all','--ignore-submodules=none'):
        raise ValueError('Dirty source checkout cannot export')
    return dict(commit=reviewed,tree=tree)


def plain_directory(path):
    path=Path(path).absolute()
    for parent in reversed((path,*path.parents)):
        if not stat.S_ISDIR(package._reject_link(parent).st_mode):raise ValueError('Expected real directory')
    return path


def verify_packages(source, root, package_paths, context):
    """Rebuild each record from actual native stage, original DLLs and source."""
    source=Path(source);root=Path(root);records={};files={};tools={}
    if set(package_paths)!=set(MODES):raise ValueError('Both original unsigned packages are required')
    for mode,(record_name,folder) in MODES.items():
        path=Path(package_paths[mode]);plain_directory(path.parent)
        if path.name!=package.package_filename(mode):raise ValueError('Unexpected original package filename')
        record_path=root/record_name;record=evidence.load(record_path)
        package.verify_record_inputs(path,record_path,source/'stage',source/'data/branding/beatquay-256.png',
            context['sourceCommit'],root/'package-input.json',root,source,mode)
        package.validate_run_binding(record,context['workflowRunId'],context['workflowRunAttempt'])
        evidence.same(record.get('sourceCommit'),context['sourceCommit'],'package source commit')
        # The installer consumed the retained private record, not the metadata copy.
        private=path.parent/'package-record.json'
        evidence.same(evidence.read(private),evidence.read(record_path),'original installer package record')
        make=record.get('makeAppx',{})
        evidence.same(package._tool_record(make.get('path',''),make.get('sdkVersion')),make,'original SDK pack/unpack executable')
        installed=evidence.load(root/folder/'installation-qualification.json')
        sign=installed.get('signtool',{})
        sign_path=Path(sign.get('path',''));plain_directory(sign_path.parent)
        if sign_path.name.casefold()!='signtool.exe' or not os.path.samefile(sign_path.parent,Path(make['path']).parent):
            raise ValueError('SignTool is not the original exact SDK sibling')
        evidence.same(sign.get('sdk_version'),'10.0.26100.0','SignTool SDK version')
        evidence.same(package.file_record(sign_path),{key:sign.get(key) for key in ('bytes','sha256')},'original SignTool bytes')
        records[mode]=record
        files[record_name]=package.file_record(record_path)
        files['private-'+mode+'-record']=package.file_record(private)
        files['unsigned-'+mode]=package.file_record(path)
        tools[mode]=dict(makeAppx=make,signTool=sign)
    return dict(records=records,files=files,tools=tools)


class OwnedOutput:
    """Remove only unchanged files created by this exact invocation."""
    def __init__(self,path):
        self.path=Path(path).absolute();plain_directory(self.path.parent)
        self.path.mkdir()  # Exclusive; preexisting directories and links are refused.
        self.identity=self.key(package._reject_link(self.path));self.files={}

    @staticmethod
    def key(info):return info.st_dev,info.st_ino

    def write(self,name,blocks):
        self.verify(complete=False)
        if name not in (OUTPUT_PACKAGE,OUTPUT_RECEIPT):raise ValueError('Unexpected unsigned export output')
        path=self.path/name
        hasher=hashlib.sha256();size=0
        with path.open('xb') as stream:
            self.files[name]=dict(identity=self.key(os.fstat(stream.fileno())),bytes=0,sha256=hasher.hexdigest())
            try:
                for block in blocks:
                    written=stream.write(block)
                    hasher.update(block[:written]);size+=written
                    self.files[name].update(bytes=size,sha256=hasher.hexdigest())
                    if written!=len(block):raise OSError('Short write of unsigned export')
                stream.flush();os.fsync(stream.fileno())
            finally:
                # Expected bytes come from writes, never from a potentially changed
                # output path. A foreign replacement or in-place mutation is retained.
                self.files[name].update(bytes=size,sha256=hasher.hexdigest())

    def verify(self,complete=True):
        plain_directory(self.path)
        if self.key(package._reject_link(self.path))!=self.identity:raise ValueError('Export directory was replaced')
        if set(x.name for x in self.path.iterdir())!=set(self.files):raise ValueError('Unexpected file in owned export directory')
        if complete and set(self.files)!={OUTPUT_PACKAGE,OUTPUT_RECEIPT}:raise ValueError('Unsigned export does not contain exactly two outputs')
        for name,row in self.files.items():
            path=self.path/name
            if self.key(package._reject_link(path))!=row['identity']:raise ValueError('Owned export file was replaced')
            evidence.same(package.file_record(path),{k:row[k] for k in ('bytes','sha256')},'unchanged owned export '+name)

    def cleanup(self):
        # Verify the whole directory before deleting anything; one foreign or
        # changed file preserves the entire output for investigation.
        self.verify(complete=False)
        for name in self.files:(self.path/name).unlink()
        self.path.rmdir()


def export(source, package_paths, reviewed, *, environ=None, platform=None, fetch=publication.download):
    source=plain_directory(source);root=plain_directory(source/'build-evidence')
    context=workflow_context(reviewed,os.environ if environ is None else environ,sys.platform if platform is None else platform)
    source_before=local_source(source,reviewed)
    public=publication.verify_public_tree(reviewed,source_before['tree'],fetch)
    before=verify_packages(source,root,package_paths,context)
    lifecycles=evidence.verify_lifecycles(root,before['records'],source,reviewed,context['workflowRunId'],context['workflowRunAttempt'])
    delivery=publication.verify_publication(source,before['records']['store']['payload'],fetch)
    # Network verification can take minutes. Re-read all native/package/original
    # DLL and consumer evidence before producing any output, without replaying UI.
    evidence.same(verify_packages(source,root,package_paths,context),before,'unchanged original package inputs')
    evidence.same(evidence.verify_lifecycles(root,before['records'],source,reviewed,context['workflowRunId'],context['workflowRunAttempt']),lifecycles,'unchanged original lifecycle evidence')
    evidence.same(local_source(source,reviewed),source_before,'unchanged clean public source')
    record=dict(schemaVersion=1,**context,generatedAtUtc=datetime.now(timezone.utc).isoformat(),
        applicationSource=public,nativeSourceDelivery=delivery,packageRecord=before['records']['store'],
        originalPackageInputs=before['files'],originalSdkTools=before['tools'],installedLifecycles=lifecycles,
        output=dict(file=OUTPUT_PACKAGE,**before['files']['unsigned-store']),
        unsigned=True,storeIdentityInstalledAndVerified=True,bothCompleteInstalledLifecyclesVerified=True,
        exactCurrentNativeSourceDeliveryVerified=True,publicBinaryRelease=False,storeSubmitted=False,
        wackTested=False,physicalAudioVerified=False,scope='Exact minimal Windows stage and original two installed lifecycles; no device playback, recording, WACK, upgrade or Store acceptance claim.')
    owned=OwnedOutput(root/'store-export')
    try:
        with package._regular_stream(package_paths['store']) as stream:
            owned.write(OUTPUT_PACKAGE,iter(lambda:stream.read(1024*1024),b''))
        evidence.same(package.file_record(owned.path/OUTPUT_PACKAGE),before['files']['unsigned-store'],'copied original unsigned bytes')
        # Recheck the unsigned OPC container, including the absence of signatures.
        package.verify_msix(owned.path/OUTPUT_PACKAGE,before['records']['store']['payload'],'store')
        owned.write(OUTPUT_RECEIPT,[package._canonical_json(record)])
        evidence.same(verify_packages(source,root,package_paths,context),before,'package inputs after export')
        evidence.same(evidence.verify_lifecycles(root,before['records'],source,reviewed,context['workflowRunId'],context['workflowRunAttempt']),lifecycles,'lifecycle evidence after export')
        evidence.same(local_source(source,reviewed),source_before,'source after export')
        owned.verify()
        return record
    except Exception as original:
        try:owned.cleanup()
        except Exception as cleanup:
            # Do not replace the original failure or delete unowned/changed data.
            print('Unsigned export cleanup refused; output retained: '+str(cleanup),file=sys.stderr)
        raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--qualification-package',type=Path,required=True)
    parser.add_argument('--store-package',type=Path,required=True)
    parser.add_argument('--reviewed-public-source',required=True)
    args=parser.parse_args()
    export(Path(__file__).resolve().parents[2],dict(qualification=args.qualification_package,store=args.store_package),args.reviewed_public_source)
    print('Exactly two unsigned Store export files verified; no public binary publication or Store submission performed.')


if __name__=='__main__':main()
