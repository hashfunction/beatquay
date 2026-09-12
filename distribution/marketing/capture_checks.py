"""Verify a reviewed existing BeatSprig export for capture; never build an app.
Copyright 2026 Trieflow LLC. MIT.
"""
import json
from pathlib import Path, PurePosixPath
import re
import subprocess

BINDING=Path(__file__).with_name('binding.json')
REPOSITORY='hashfunction/beatquay'
PACKAGE_NAME='BeatSprig_1.0.1.0_x64.msix'
RECEIPT_NAME='BeatSprig_1.0.1.0_x64.export.json'


def require(condition, message):
    if not condition:raise ValueError(message)


def relative_path(value):
    require(isinstance(value,str) and value and '\\' not in value and ':' not in value and
            not value.startswith('/') and str(PurePosixPath(value))==value,'Unsafe artifact path')
    for part in value.split('/'):
        require(part not in ('','.','..') and not part.endswith((' ','.')) and
                not re.search(r'[\x00-\x1f<>"|?*]',part) and
                part.split('.')[0].upper() not in {'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(1,10)),*(f'LPT{i}' for i in range(1,10))},
                'Unsafe artifact path')
    return value


def validate_binding(value):
    require(isinstance(value,dict) and set(value)=={'schema_version','product','qualified'} and
            type(value['schema_version']) is int and value['schema_version']==1 and value['product']=='BeatSprig' and
            isinstance(value['qualified'],dict),'Capture needs a reviewed successful Store export')
    b=value['qualified']
    require(set(b)=={'source_commit','workflow_run_id','workflow_run_attempt','store_artifact_id','metadata_artifact_id','package','export_receipt'},
            'Exact capture binding fields required')
    require(isinstance(b['source_commit'],str) and re.fullmatch('[0-9a-f]{40}',b['source_commit']) and
            all(isinstance(b[k],str) and re.fullmatch('[1-9][0-9]*',b[k]) for k in ('workflow_run_id','workflow_run_attempt')),
            'Invalid exact source/run/attempt')
    require(all(type(b[k]) is int and b[k]>0 for k in ('store_artifact_id','metadata_artifact_id')),'Exact artifact IDs required')
    for key in ('package','export_receipt'):
        item=b[key]
        require(isinstance(item,dict) and set(item)=={'bytes','sha256'} and type(item['bytes']) is int and item['bytes']>0 and
                isinstance(item['sha256'],str) and re.fullmatch('[0-9a-f]{64}',item['sha256']),'Invalid exact byte binding')
    require(b['package']['bytes']<=200_000_000 and b['export_receipt']['bytes']<=16_000_000,'Capture input exceeds bound')
    return b


def binding():return validate_binding(json.loads(BINDING.read_text(encoding='utf-8')))


def verify_run(run,bound):
    require(type(run.get('id')) is int and run['id']==int(bound['workflow_run_id']) and
            type(run.get('run_attempt')) is int and run['run_attempt']==int(bound['workflow_run_attempt']) and
            run.get('head_sha')==bound['source_commit'] and run.get('conclusion')=='success' and
            run.get('event')=='workflow_dispatch' and run.get('path')=='.github/workflows/windows-candidate.yml' and
            run.get('repository',{}).get('full_name')==REPOSITORY,'Original successful Windows qualification run differs')


def verify_export_context(record,bound):
    expected=dict(schemaVersion=1,sourceCommit=bound['source_commit'],workflowRunId=bound['workflow_run_id'],
        workflowRunAttempt=bound['workflow_run_attempt'],repository=REPOSITORY,workflowEvent='workflow_dispatch',
        unsigned=True,storeIdentityInstalledAndVerified=True,bothCompleteInstalledLifecyclesVerified=True,
        exactCurrentNativeSourceDeliveryVerified=True,publicBinaryRelease=False,storeSubmitted=False,
        wackTested=False,physicalAudioVerified=False,output=dict(file=PACKAGE_NAME,**bound['package']))
    for key,value in expected.items():
        require(type(record.get(key)) is type(value) and json.dumps(record[key],sort_keys=True)==json.dumps(value,sort_keys=True),
                'Original complete unsigned export differs: '+key)


def checkout(source,commit):
    def git(*args):return subprocess.run(['git','-C',str(source),*args],capture_output=True,text=True,check=True,timeout=60).stdout.strip()
    require(isinstance(commit,str) and re.fullmatch('[0-9a-f]{40}',commit),'Exact checkout commit required')
    require(git('rev-parse','HEAD')==commit and not git('status','--porcelain=v1','--untracked-files=all','--ignore-submodules=none'),
            'Exact clean source checkout required')
    tree=git('show','-s','--format=%T','HEAD');require(re.fullmatch('[0-9a-f]{40}',tree),'Exact source tree required')
    return dict(commit=commit,tree=tree)


if __name__=='__main__':
    import argparse,os
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--binding-output',type=Path,required=True);args=parser.parse_args()
    bound=binding()  # Null binding fails before any output file or network access.
    checkout(BINDING.parents[2],os.environ.get('GITHUB_SHA'))
    with args.binding_output.open('a',encoding='utf-8') as stream:stream.write('qualified_source='+bound['source_commit']+'\n')
