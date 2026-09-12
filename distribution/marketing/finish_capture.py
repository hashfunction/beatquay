"""Verify the fresh capture observation and publish only identical raw PNG bytes.
Copyright 2026 Trieflow LLC. MIT.
"""
import argparse
from pathlib import Path, PureWindowsPath
import os
import shutil
from artifact_files import plain
from capture_checks import require
from prepare_capture import write_json
from verify_prepared import verify

ALIASES={'01-evening-pulse-project.png':'01-arrangement.png','02-export-project.png':'02-export-settings.png','03-export-completed.png':'03-export-completed.png'}


def verify_capture(directory,source,verified,context):
 e=verified['modules'].evidence;p=verified['modules'].package;record=verified['record']
 receipt=e.load(directory/'capture-result.json');workflow=e.load(directory/'consumer-workflow/consumer-workflow.json')
 for key,value in dict(schema_version=1,purpose='marketing screenshots only',consumer_acceptance=False,installation_qualification_claimed=False,
   capture_passed=True,capture_source_commit=context['source_commit'],capture_run_id=context['workflow_run_id'],capture_run_attempt=context['workflow_run_attempt'],
   qualified_source_commit=record['sourceCommit'],identity_mode='store',identity=p.identity_for('store'),
   unsigned_package_sha256=record['containerVerification']['package']['sha256'],unsigned_package_unchanged=True,certificate_private_key_exported=False,
   registration_ownership_established=True,process_identity_ownership_established=True,clean_close_verified=True,uninstall_verified=True,owned_files_cleaned=True,
   primary_error=None,cleanup_errors=[],evidence_errors=[],loaded_module_rejection=None,residual_package_full_names=[],
   completed_operations=e.OPERATIONS,completed_cleanup=e.CLEANUP).items():e.same(receipt.get(key),value,'capture '+key)
 e.same(receipt['original_consumer_observation'],workflow,'complete original capture consumer observation')
 if e.digest(receipt.get('signed_copy_sha256'))==receipt['unsigned_package_sha256']:raise ValueError('Capture did not use a separate signed copy')
 bindings=dict(context,identity_mode='store')
 for key,value in bindings.items():e.same(workflow.get(key),value,'fresh capture workflow '+key)
 full='1659hashfunction.BeatQuay_1.0.1.0_x64__r3hxytd7jt6c4'
 for key in ('owned_package_full_name','activated_process_package_full_name'):e.same(receipt.get(key),full,'capture '+key)
 pid=e.integer(workflow.get('process_id'),1);handle=e.integer(workflow.get('main_window_handle'),1)
 for key in ('process_exit','cleanup_process_exit'):
  for field,value in dict(process_id=pid,wait_completed=True,exit_code=0,normal_exit=True,observation_error=None).items():e.same(receipt.get(key,{}).get(field),value,'capture '+key+' '+field)
 for key in ('owned_profile','working_directory'):
  for field,value in dict(source_commit=context['source_commit'],ownership_established=True,process_id=pid,package_full_name=full,cleanup_verified=True).items():e.same(receipt.get(key,{}).get(field),value,'capture '+key+' '+field)
 for key,name in [('first','Evening Pulse.mmp'),('reopened','Evening Pulse Reopened.mmp'),('wave','Evening Pulse.wav')]:
  e.same(str(e.windows(workflow['project_paths'][key])),str(PureWindowsPath('C:/BeatSprig Demo/Evening Pulse')/name),'exact friendly demo path')
 start=e.utc(receipt['capture_started_at_utc']);end=e.utc(receipt['generated_at_utc']);require(end>start,'Capture time order invalid')
 helpers={name:p.file_record(source/name) for name in e.HELPERS}
 e.same(receipt.get('helper_bindings'),helpers,'capture original helper files');e.same(workflow.get('helper_bindings'),helpers,'consumer original helper files')
 e.verify_consumer(workflow,directory/'consumer-workflow',source,record,pid,handle,full,bindings,start,end)
 before=e.load(directory/'loaded-modules.json');after=e.load(directory/'loaded-modules-after-workflow.json')
 e.same(after,receipt['loaded_modules'],'capture module original');e.verify_modules(before,record,full,False);e.verify_modules(after,record,full,True)
 display=receipt.get('native_display',{})
 for key,value in dict(restore_verified=True,restore_result=0,test_result=0,apply_result=0,registry_updated=False,unsafe_modes_enabled=False,dpi_changed=False,renderer_emulation_used=False).items():e.same(display.get(key),value,'capture display '+key)
 e.same(display.get('restored'),display.get('before'),'capture original display restored');e.same(display.get('after'),display.get('selected'),'capture actual selected mode')
 require(display['selected'] in display.get('supported_modes',[]),'Capture mode not enumerated')
 frames=receipt.get('frames',[]);e.same([x.get('file') for x in frames],list(ALIASES),'three original guarded frames')
 for frame,screen in zip(frames,workflow['screenshots']):
  e.same(frame.get('original_source_sha256'),helpers['cmake/msix/consumer-workflow.ps1']['sha256'],'screen original source');e.digest(frame.get('original_script_sha256'))
  for side in ('before','after'):
   measured=frame[side]
   for key,value in dict(main_pid=pid,foreground_pid=pid,main_handle=handle,foreground_handle=screen['foreground_window'],title=screen['project_title'],dpi=96,
     x=screen['x'],y=screen['y'],width=screen['width'],height=screen['height'],display=display['after']).items():e.same(measured.get(key),value,'capture frame '+side+' '+key)
   require(start<=e.utc(measured['observed_utc'])<=end,'Frame outside capture lifecycle')
  require(e.utc(frame['before']['observed_utc'])<=e.utc(screen['captured_utc'])<=e.utc(frame['after']['observed_utc']),'Original pixels outside guarded observation')
 return receipt


def publish(directory,receipt,verified,context):
 p=verified['modules'].package;e=verified['modules'].evidence;output=directory/'published';plain(directory,True)
 require(not output.exists(),'Published capture output already exists')
 sources={name:plain(directory/'consumer-workflow'/name) for name in ALIASES}
 expected={screen['file']:{'bytes':sources[screen['file']].stat().st_size,'sha256':screen['sha256']} for screen in receipt['original_consumer_observation']['screenshots']}
 for name,path in sources.items():e.same(p.file_record(path),expected[name],'raw screen before publication')
 output.mkdir();rows=[]
 for name,path in sources.items():
  destination=output/ALIASES[name]
  with path.open('rb') as original,destination.open('xb') as copied:shutil.copyfileobj(original,copied)
  e.same(p.file_record(destination),expected[name],'identical raw PNG publication')
  rows.append(dict(original=name,file=ALIASES[name],**expected[name]))
 write_json(output/'capture-provenance.json',dict(schema_version=1,purpose='marketing screenshots only',consumer_acceptance=False,
  installation_qualification_claimed=False,capture=context,qualified_source_commit=verified['record']['sourceCommit'],
  qualified_original_export=p.file_record(verified['receipt']),qualified_package=p.file_record(verified['package']),
  capture_result=p.file_record(directory/'capture-result.json'),native_pixels_unedited=True,images=rows))

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--inputs',type=Path,required=True);parser.add_argument('--qualified-source',type=Path,required=True);parser.add_argument('--capture',type=Path,required=True);args=parser.parse_args()
 verified=verify(args.inputs,args.qualified_source);context={'source_commit':os.environ['GITHUB_SHA'],'workflow_run_id':os.environ['GITHUB_RUN_ID'],'workflow_run_attempt':os.environ['GITHUB_RUN_ATTEMPT']}
 receipt=verify_capture(args.capture,args.qualified_source,verified,context);publish(args.capture,receipt,verified,context)
