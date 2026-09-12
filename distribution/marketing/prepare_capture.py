"""Prepare exactly the reviewed original Store package and metadata, without a rebuild.
Copyright 2026 Trieflow LLC. MIT.
"""
import argparse
from datetime import datetime,timezone
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import capture_checks as checks
from artifact_files import extract,plain
from verify_inputs import verify_original_packages,verify_original_lifecycles


def qualified_modules(source):
    source=plain(source,True);folder=source/'cmake/msix'
    sys.path.insert(0,str(folder))
    result={}
    for name in ('msix_qualification','store_workflow_evidence','source_publication','export_store_package'):
        module=importlib.import_module(name)
        checks.require(Path(module.__file__).resolve()==(folder/(name+'.py')).resolve(),'Foreign qualification module loaded')
        result[name]=module
    for name,path in [('native_source',source/'distribution/native_source.py'),('ms_runtime_origins',folder/'ms_runtime_origins.py'),('consumer_files',folder/'consumer_files.py')]:
        checks.require(Path(sys.modules[name].__file__).resolve()==path.resolve(),'Foreign qualification dependency loaded')
    return SimpleNamespace(package=result['msix_qualification'],evidence=result['store_workflow_evidence'],publication=result['source_publication'])


def gh_json(endpoint):
    result=subprocess.run(['gh','api',endpoint],capture_output=True,check=True,timeout=30)
    checks.require(len(result.stdout)<=1_048_576,'GitHub metadata exceeds bound')
    return json.loads(result.stdout)


def write_json(path,value):
    with Path(path).open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2);stream.write('\n')


def artifact(number,name,output,maximum,bound,members=None):
    endpoint=f'repos/{checks.REPOSITORY}/actions/artifacts/{number}';info=gh_json(endpoint)
    checks.require(type(info.get('id')) is int and info['id']==number and info.get('name')==name and info.get('expired') is False and
        type(info.get('workflow_run',{}).get('id')) is int and info['workflow_run']['id']==int(bound['workflow_run_id']) and
        info['workflow_run'].get('head_sha')==bound['source_commit'] and
        type(info.get('size_in_bytes')) is int and 0<info['size_in_bytes']<=maximum,'Pinned artifact identity or size differs')
    archive=output.with_suffix('.zip');plain(archive.parent,True);owned=False
    try:
      with archive.open('xb') as stream:
        owned=True
        # gh owns the authenticated GitHub artifact redirect; no arbitrary URL or
        # repository credential is forwarded by this script to another host.
        subprocess.run(['gh','api',endpoint+'/zip'],stdout=stream,check=True,timeout=120)
      checks.require(archive.stat().st_size==info['size_in_bytes'],'Downloaded artifact differs from pinned metadata size')
      extract(archive,output,maximum,members)
    finally:
      if owned:archive.unlink()
    return info


def verify_local_inputs(inputs,source,bound):
    source=plain(source,True);inputs=plain(inputs,True);git=checks.checkout(source,bound['source_commit']);modules=qualified_modules(source)
    p=modules.package;e=modules.evidence
    package=inputs/'store'/checks.PACKAGE_NAME;receipt_path=inputs/'store'/checks.RECEIPT_NAME
    e.same(p.file_record(package),bound['package'],'reviewed original Store package bytes')
    e.same(p.file_record(receipt_path),bound['export_receipt'],'reviewed original export receipt bytes')
    ready=e.load(receipt_path);checks.verify_export_context(ready,bound)
    checks.verify_run(e.load(inputs/'qualified-run.json'),bound)
    roots=list((inputs/'metadata').rglob('msix-store-package-record.json'))
    checks.require(len(roots)==1,'Exactly one original Store package metadata root required');root=roots[0].parent
    records=verify_original_packages(source,root,package,ready,bound,p,e)
    lifecycles=verify_original_lifecycles(root,records,source,bound,ready['installedLifecycles'],e)
    e.utc(ready['generatedAtUtc'])
    checks.require(e.utc(ready['generatedAtUtc'])>=e.utc(lifecycles['store']['completedAtUtc']),'Export predates completed Store lifecycle')
    for key in ('commit','tree'):e.same(ready['applicationSource'].get(key),git[key],'original public application '+key)
    return dict(modules=modules,git=git,ready=ready,record=records['store'],metadata=root,package=package,receipt=receipt_path)


def main(output,qualified):
    bound=checks.binding()
    checks.require(sys.platform=='win32' and os.environ.get('CI')=='true' and os.environ.get('GITHUB_ACTIONS')=='true' and
        os.environ.get('GITHUB_REPOSITORY')==checks.REPOSITORY and os.environ.get('GITHUB_EVENT_NAME')=='workflow_dispatch',
        'Capture requires the standalone BeatSprig Windows dispatch')
    capture=checks.checkout(checks.BINDING.parents[2],os.environ.get('GITHUB_SHA'))
    checks.checkout(qualified,bound['source_commit']);plain(output.parent,True);output.mkdir()
    run=gh_json(f"repos/{checks.REPOSITORY}/actions/runs/{bound['workflow_run_id']}");checks.verify_run(run,bound)
    package_artifact=artifact(bound['store_artifact_id'],'BeatSprig-1.0.1-reviewed-unsigned-Store-export',output/'store',220_000_000,bound,{checks.PACKAGE_NAME,checks.RECEIPT_NAME})
    metadata_artifact=artifact(bound['metadata_artifact_id'],'BeatSprig-Windows-candidate-metadata',output/'metadata',64_000_000,bound)
    write_json(output/'qualified-run.json',run)
    verified=verify_local_inputs(output,qualified,bound);m=verified['modules']
    public=m.publication.verify_public_tree(bound['source_commit'],verified['git']['tree'])
    delivery=m.publication.verify_publication(qualified,verified['record']['payload'])
    original=dict(verified['ready']['nativeSourceDelivery']);fresh=dict(delivery)
    original_time=m.evidence.utc(original.pop('verifiedAtUtc'));fresh.pop('verifiedAtUtc')
    checks.require(original_time<=m.evidence.utc(verified['ready']['generatedAtUtc']),'Original source delivery postdates export')
    m.evidence.same(original,fresh,'current complete source delivery matches original export')
    # Recheck exact local bytes after the bounded anonymous source download.
    again=verify_local_inputs(output,qualified,bound)
    m.evidence.same(again['ready'],verified['ready'],'unchanged original export after public source readback')
    write_json(output/'capture-inputs.json',dict(schema_version=1,purpose='marketing screenshots only',consumer_acceptance=False,
        installation_qualification_claimed=False,capture_source=capture,capture_run_id=os.environ['GITHUB_RUN_ID'],capture_run_attempt=os.environ['GITHUB_RUN_ATTEMPT'],
        qualified=bound,package_artifact=package_artifact,metadata_artifact=metadata_artifact,
        package_path=str(verified['package']),package_record_path=str(verified['metadata']/'msix-store-package-record.json'),
        original_export_receipt=m.package.file_record(verified['receipt']),current_application_source=public,current_native_source_delivery=delivery,
        verified_at_utc=datetime.now(timezone.utc).isoformat()))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--qualified-source',type=Path,required=True)
    args=parser.parse_args();main(args.output,args.qualified_source)
