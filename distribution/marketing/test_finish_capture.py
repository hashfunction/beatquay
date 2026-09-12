"""Generated final states test policy, never represent a native capture success."""
import copy
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
SOURCE=Path(__file__).resolve().parents[2];sys.path.insert(0,str(SOURCE/'cmake/msix'))
import test_store_workflow_evidence as fixtures
import finish_capture as subject

class FinishTests(unittest.TestCase):
 def setUp(self):
  f=fixtures.LifecycleTests();f.setUp();self.addCleanup(f.doCleanups);self.directory=f.root/'msix-store-install'
  e=fixtures.subject;self.e=e;original=e.load(self.directory/'installation-qualification.json');workflow=original['project_export_workflow']
  paths={key:'C:\\BeatSprig Demo\\Evening Pulse\\'+name for key,name in [('first','Evening Pulse.mmp'),('reopened','Evening Pulse Reopened.mmp'),('wave','Evening Pulse.wav')]}
  mapping={workflow['project_paths'][key]:value for key,value in paths.items()}
  def remap(value):
   if isinstance(value,str):
    for old,new in mapping.items():value=value.replace(old,new).replace(old.replace('\\','/'),new.replace('\\','/'))
    return value
   if isinstance(value,list):return [remap(x) for x in value]
   if isinstance(value,dict):return {key:remap(item) for key,item in value.items()}
   return value
  workflow=remap(workflow);self.workflow=workflow
  self.context=dict(source_commit=f.commit,workflow_run_id=f.run,workflow_run_attempt=f.attempt)
  self.verified=dict(modules=SimpleNamespace(evidence=e,package=e.package),record=f.records['store'])
  self.receipt=dict(schema_version=1,purpose='marketing screenshots only',consumer_acceptance=False,installation_qualification_claimed=False,
   capture_passed=True,capture_source_commit=f.commit,capture_run_id=f.run,capture_run_attempt=f.attempt,qualified_source_commit=f.commit,
   capture_started_at_utc=original['qualification_started_at_utc'],generated_at_utc=original['generated_at_utc'],
   original_consumer_observation=workflow,owned_files_cleaned=True,loaded_modules=e.load(self.directory/'loaded-modules-after-workflow.json'))
  for key in ('identity_mode','identity','unsigned_package_sha256','unsigned_package_unchanged','signed_copy_sha256','certificate_private_key_exported',
   'registration_ownership_established','process_identity_ownership_established','clean_close_verified','uninstall_verified','primary_error','cleanup_errors','evidence_errors',
   'loaded_module_rejection','residual_package_full_names','completed_operations','completed_cleanup','owned_package_full_name','activated_process_package_full_name',
   'process_exit','cleanup_process_exit','owned_profile','working_directory','helper_bindings','native_display'):self.receipt[key]=original[key]
  self.receipt['frames']=[]
  for screen in workflow['screenshots']:
   frame=dict(main_pid=workflow['process_id'],foreground_pid=workflow['process_id'],main_handle=workflow['main_window_handle'],
    foreground_handle=screen['foreground_window'],title=screen['project_title'],dpi=96,observed_utc=screen['captured_utc'],
    **{key:screen[key] for key in ('x','y','width','height','display')})
   self.receipt['frames'].append(dict(file=screen['file'],before=frame,after=copy.deepcopy(frame),
    original_source_sha256=original['helper_bindings']['cmake/msix/consumer-workflow.ps1']['sha256'],original_script_sha256='a'*64))
  self.write()
 def write(self):
  (self.directory/'capture-result.json').write_text(json.dumps(self.receipt))
  (self.directory/'consumer-workflow/consumer-workflow.json').write_text(json.dumps(self.workflow))
 def verify(self):return subject.verify_capture(self.directory,SOURCE,self.verified,self.context)
 def test_complete_and_mutated_final_gates(self):
  self.verify();original=copy.deepcopy(self.receipt)
  for key,value in [('capture_passed',False),('consumer_acceptance',True),('installation_qualification_claimed',True),('capture_run_attempt','2'),
   ('qualified_source_commit','0'*40),('uninstall_verified',False),('cleanup_errors',['residual']),('owned_files_cleaned',False),('frames',[])]:
   self.receipt=copy.deepcopy(original);self.receipt[key]=value;self.write()
   with self.subTest(key=key),self.assertRaises(ValueError):self.verify()
  self.receipt=original;self.receipt['frames'][1]['after']['foreground_pid']+=1;self.write()
  with self.assertRaises(ValueError):self.verify()
 def test_partial_consumer_or_pixels_and_paths_refused(self):
  self.verify();original=copy.deepcopy(self.workflow)
  for change in ('path','wav','stage','input'):
   self.workflow=copy.deepcopy(original)
   if change=='path':self.workflow['project_paths']['first']='C:\\CI\\Evening Pulse.mmp'
   elif change=='wav':self.workflow['wave_verification']['frames']=True
   elif change=='stage':self.workflow['stages'].pop()
   else:self.workflow['inputs'].pop()
   self.receipt['original_consumer_observation']=self.workflow;self.write()
   with self.subTest(change=change),self.assertRaises(ValueError):self.verify()
  self.workflow=original;self.receipt['original_consumer_observation']=original;self.write()
  png=self.directory/'consumer-workflow/01-evening-pulse-project.png';png.write_bytes(png.read_bytes()+b'changed')
  with self.assertRaises(ValueError):self.verify()
 def test_publication_copies_exact_png_bytes_and_excludes_every_other_file(self):
  receipt=self.verify();self.verified.update(receipt=self.directory/'capture-result.json',package=self.directory/'qualification-window.png')
  subject.publish(self.directory,receipt,self.verified,self.context)
  output=self.directory/'published';self.assertEqual({x.name for x in output.iterdir()},set(subject.ALIASES.values())|{'capture-provenance.json'})
  for original,alias in subject.ALIASES.items():self.assertEqual((output/alias).read_bytes(),(self.directory/'consumer-workflow'/original).read_bytes())
  with self.assertRaises(ValueError):subject.publish(self.directory,receipt,self.verified,self.context)

if __name__=='__main__':unittest.main()
