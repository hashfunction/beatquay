"""Generated receipts/files exercise export policy; they never establish Windows acceptance."""
import copy
from datetime import timedelta
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from xml.etree.ElementTree import ParseError
import store_workflow_evidence as subject

SOURCE=Path(__file__).resolve().parents[2]
FIXTURE=Path(__file__).parent/'fixtures/consumer-34696012333'


class EvidenceFileTests(unittest.TestCase):
    def test_original_bytes_duplicate_json_and_reparse_ancestor_refusal(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent=Path(temporary).resolve();path=parent/'receipt.json';path.write_bytes(b'{"accepted":true}')
            self.assertEqual(subject.read(path),b'{"accepted":true}')
            self.assertEqual(subject.load(path),{'accepted':True})
            with self.assertRaisesRegex(ValueError,'Duplicate'):subject.json_bytes(b'{"accepted":true,"accepted":false}')
            original=Path.lstat
            def lstat(candidate,*args,**kwargs):
                if candidate==parent:return SimpleNamespace(st_mode=0o040755,st_file_attributes=0x400)
                return original(candidate,*args,**kwargs)
            # Exercise the actual Windows reparse-attribute predicate, without
            # requiring junction privileges or changing any real parent folder.
            with patch.object(Path,'lstat',lstat),self.assertRaisesRegex(ValueError,'reparse'):subject.read(path)


class WaveReceiptTests(unittest.TestCase):
    def test_actual_dotnet_utc_format_and_timezone_refusals(self):
        actual='2026-09-12T12:17:09.4962903Z'
        self.assertEqual(subject.utc(actual).isoformat(),'2026-09-12T12:17:09.496290+00:00')
        for value in ('2026-09-12T12:17:09','2026-09-12T12:17:09+01:00','2026-09-12',False):
            with self.assertRaises(ValueError):subject.utc(value)

    def test_complete_wave_metrics_and_strict_mutations(self):
        frames=round(5*240/116*44100)
        original=dict(frames=frames,channels=2,sample_rate=44100,sample_width_bytes=2,
            duration_seconds=frames/44100,peak_pcm16=5000,rms_pcm16=2000.0,
            bytes=44+frames*4,sha256='a'*64,expected_padding_bars=1,
            arrangement_bar_rms_pcm16=[2200.0]*4,arrangement_bar_ac_rms_pcm16=[2100.0]*4)
        subject.verify_wave_receipt(original)
        for name,value in [('frames',True),('channels',1),('sample_rate',48000),('sample_width_bytes',3),
            ('duration_seconds',0.0),('peak_pcm16',32767),('rms_pcm16',0),('bytes',44),('sha256','missing'),
            ('expected_padding_bars',True),('arrangement_bar_rms_pcm16',[0.0]*4),
            ('arrangement_bar_ac_rms_pcm16',[float('nan')]*4),('arrangement_bar_ac_rms_pcm16',[3000]*4)]:
            changed=copy.deepcopy(original);changed[name]=value
            with self.subTest(name=name,value=value),self.assertRaises(ValueError):subject.verify_wave_receipt(changed)


class LifecycleTests(unittest.TestCase):
    """Controlled completed-state fixtures are derived from a FAILED original run.

    Only the actual UI/file observations are historical evidence; generated final
    state permits policy mutation tests and is never a Windows success receipt.
    """
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.originals={}
        manifest=subject.load(FIXTURE/'manifest.json')
        for name,row in manifest['originalFiles'].items():
            data=(FIXTURE/row['fixture']).read_bytes()
            if row['fixture'].endswith('.gz'):data=gzip.decompress(data)
            self.assertEqual({'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()},{key:row[key] for key in ('bytes','sha256')})
            self.originals[name]=data
        self.commit=manifest['sourceCommit'];self.run='34696012333';self.attempt='1'
        self.record=subject.json_bytes(self.originals['msix-package-record.json'])
        pin=subject.load(SOURCE/'distribution/runner-shell-inputs.json')
        context=dict(windows=True,os64=True,process64=True,ci='true',actions='true',environment='github-hosted',
            repository=pin['repository'],image_os=pin['image_os'],image_version=pin['image_version'],system_root='C:\\Windows')
        before=dict(errors=[],files=pin['files'],registry=pin['registry'],products=[dict(hive='LocalMachine',view='Registry64',key=pin['product']['code'],
            values=dict(DisplayName=pin['product']['name'],DisplayVersion=pin['product']['version'],Publisher='TortoiseSVN',WindowsInstaller=1,
            InstallLocation='',UninstallString='MsiExec.exe /I'+pin['product']['code']))])
        absent=dict(products=[],registry=[],files=[],errors=[])
        preparation=dict(schema_version=1,binding=dict(source_commit=self.commit,workflow_run_id=self.run,workflow_run_attempt=self.attempt),
            context=context,pin_sha256=subject.package.file_record(SOURCE/'distribution/runner-shell-inputs.json')['sha256'],
            before=before,rechecked=before,after=absent,prepared=True,error=None,started_utc='2026-09-12T13:00:00Z',completed_utc='2026-09-12T13:01:00Z',
            uninstall=dict(program=dict(path='C:\\Windows\\System32\\msiexec.exe',bytes=1,sha256='b'*64),
            arguments=['/x',pin['product']['code'],'/qn','/norestart','REBOOT=ReallySuppress'],process_id=123,completed=True,exit_code=0,observation_error=None))
        path=self.root/'runner-shell-preparation.json';path.write_text(json.dumps(preparation))
        self.record['evidenceInputs'][path.name]=subject.package.file_record(path)
        self.records={}
        for mode,folder in [('qualification','msix-install'),('store','msix-store-install')]:
            for name,data in self.originals.items():
                if name.startswith('msix-install/'):
                    dest=self.root/folder/name.removeprefix('msix-install/');dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
            directory=self.root/folder
            record=copy.deepcopy(self.record);record['identity']=subject.package.identity_for(mode)
            record['sourceInputs'].update({name:subject.package.file_record(SOURCE/name) for name in subject.HELPERS})
            receipt=subject.load(directory/'installation-qualification.json')
            workflow=subject.load(directory/'consumer-workflow/consumer-workflow.json')
            bindings=dict(source_commit=self.commit,workflow_run_id=self.run,workflow_run_attempt=self.attempt,identity_mode=mode)
            receipt.update(bindings);workflow.update(bindings)
            receipt['runner_shell']={phase:dict(identity_mode=mode,context=context,absent=True,state=absent,
                observed_utc='2026-09-12T13:39:4'+str(6+i)+'Z',preparation=dict(path='C:\\runner\\build-evidence\\runner-shell-preparation.json',
                **subject.package.file_record(path))) for i,phase in enumerate(('preflight','before_activation'))}
            receipt.update(identity=record['identity'],qualification_started_at_utc='2026-09-12T13:39:45Z',
                completed_operations=subject.OPERATIONS,completed_cleanup=subject.CLEANUP,
                qualification_identity_only=mode=='qualification',installed_identity_verified=True,store_identity_used=mode=='store',
                clean_close_verified=True,uninstall_verified=True,installation_qualification_passed=True,workflow_acceptance=True,
                primary_error=None,loaded_module_rejection=None,helper_bindings={name:record['sourceInputs'][name] for name in subject.HELPERS})
            workflow.update(helper_bindings=receipt['helper_bindings'],main_window_handle=workflow['stages'][0]['window']['root']['native_window_handle'],
                export_loop_settings={'Export as loop (remove extra bar)':'Off','Export between loop markers':'Off'})
            workflow['wave_verification']['sample_width_bytes']=2
            for key in ('process_exit','cleanup_process_exit'):
                receipt[key]=dict(process_id=workflow['process_id'],wait_completed=True,exit_code=0,normal_exit=True,observation_error=None)
            receipt['owned_profile']['observations'].append(dict(action='normal_close',sha256=receipt['owned_profile']['sha256'],changed_fields=['recentfiles'],observed_utc='2026-09-12T13:41:29Z'))
            window=subject.load(directory/'window-observation.json');window['main_window_handle']=workflow['main_window_handle']
            receipt['window']=window
            for screen in workflow['screenshots']:screen.update(bindings,main_window_handle=workflow['main_window_handle'])
            before=subject.load(directory/'loaded-modules.json');after=copy.deepcopy(before)
            if not any(row.get('relative_path')=='plugins/kicker.dll' for row in after):
                after.append(dict(name='kicker.dll',path='C:/Program Files/WindowsApps/'+receipt['package_full_name']+'/plugins/kicker.dll',
                    origin='package',relative_path='plugins/kicker.dll',sha256=record['payload']['plugins/kicker.dll']['sha256'],platform_signature=None))
            receipt['loaded_module_count']=len(after)
            if mode=='store':
                old=receipt['package_full_name'];new='1659hashfunction.BeatQuay_1.0.1.0_x64__r3hxytd7jt6c4'
                old_family=old.split('_1.0.1.0_x64__')[0]+'_a74jba1vjrwc6';new_family='1659hashfunction.BeatQuay_r3hxytd7jt6c4'
                def remap(value):
                    if isinstance(value,dict):return {k:remap(v) for k,v in value.items()}
                    if isinstance(value,list):return [remap(x) for x in value]
                    if isinstance(value,str):
                        value=value.replace(old,new).replace(old_family,new_family)
                        if value.startswith('2026-09-12T') and (value.endswith('Z') or value.endswith('+00:00')):value=(subject.utc(value)+timedelta(minutes=10)).isoformat()
                    return value
                receipt=remap(receipt);workflow=remap(workflow);before=remap(before);after=remap(after)
            receipt['project_export_workflow']=workflow
            for name,value in [('installation-qualification.json',receipt),('consumer-workflow/consumer-workflow.json',workflow),('window-observation.json',window),
                               ('loaded-modules.json',before),('loaded-modules-after-workflow.json',after)]:
                (directory/name).write_text(json.dumps(value))
            self.records[mode]=record
    def verify(self):return subject.verify_lifecycles(self.root,self.records,SOURCE,self.commit,self.run,self.attempt)
    def test_complete_generated_two_lifecycles_recheck_actual_retained_projects_and_captures(self):
        got=self.verify();self.assertEqual(set(got),{'qualification','store'})
        self.assertFalse(got['store']['waveRereadAfterCleanup']);self.assertEqual(got['store']['projectVerification']['tempo'],116)
    def test_windows_loader_case_matching_requires_unique_payload_and_exact_hash(self):
        self.verify()
        rows=subject.load(self.root/'msix-install/loaded-modules.json')
        subject.verify_modules(rows,self.records['qualification'],subject.load(self.root/'msix-install/installation-qualification.json')['package_full_name'],False)
        record=copy.deepcopy(self.records['qualification']);record['payload']['MSVCP140.dll']=record['payload']['msvcp140.dll']
        with self.assertRaisesRegex(ValueError,'Ambiguous'):subject.verify_modules(rows,record,'ignored',False)
        next(x for x in rows if x.get('relative_path')=='MSVCP140.dll')['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'module differs'):subject.verify_modules(rows,self.records['qualification'],subject.load(self.root/'msix-install/installation-qualification.json')['package_full_name'],False)

    def test_original_failed_lifecycle_cannot_export(self):
        (self.root/'msix-install/installation-qualification.json').write_bytes(self.originals['msix-install/installation-qualification.json'])
        with self.assertRaises(ValueError):self.verify()
    def test_typed_failures_cleanup_order_run_attempt_module_and_source_guards(self):
        self.verify()
        path=self.root/'msix-store-install/installation-qualification.json';original=path.read_bytes()
        mutations=[('clean_close_verified',False),('uninstall_verified',False),('store_identity_used',1),('workflow_run_attempt','2'),
            ('completed_cleanup',subject.CLEANUP[:-1]),('completed_operations',list(reversed(subject.OPERATIONS))),
            ('primary_error','native failure'),('loaded_module_rejection',{'reason':'unresolved DLL'}),('cleanup_errors',['certificate remains']),('evidence_errors',['unreadable']),
            ('qualification_started_at_utc','2026-09-12T13:00:00Z'),('owned_package_full_name','foreign'),('helper_bindings',{})]
        for key,value in mutations:
            row=subject.json_bytes(original);row[key]=value;path.write_text(json.dumps(row))
            with self.subTest(key=key),self.assertRaises(ValueError):self.verify()
        path.write_bytes(original)
        modules=self.root/'msix-store-install/loaded-modules-after-workflow.json'
        rows=subject.load(modules);rows[0]['origin']='unresolved';modules.write_text(json.dumps(rows))
        with self.assertRaises(ValueError):self.verify()
    def test_actual_consumer_metrics_stage_order_controls_and_captures_refuse_mutations(self):
        self.verify()
        directory=self.root/'msix-store-install'
        receipt_path=directory/'installation-qualification.json';workflow_path=directory/'consumer-workflow/consumer-workflow.json'
        original=receipt_path.read_bytes();workflow_original=workflow_path.read_bytes()
        def wave(value):value['wave_verification']['sample_width_bytes']=3
        def stage(value):value['stages'][3]['stage']='tempo_value_116'
        def wheel(value):next(x for x in value['inputs'] if x['kind']=='native_tempo_wheel')['wheel_delta']=240
        def file_dialog(value):next(x for x in value['inputs'] if x['kind']=='uia_value')['control']['process_id']+=1
        def loop(value):value['export_loop_settings']['Export between loop markers']='On'
        def capture(value):value['screenshots'][0]['main_window_handle']+=1
        def capture_time(value):value['screenshots'][0]['captured_utc']='2026-09-12T12:00:00Z'
        def project(value):value['file_verification']['tempo']=112
        for mutate in (wave,stage,wheel,file_dialog,loop,capture,capture_time,project):
            receipt=subject.json_bytes(original);workflow=subject.json_bytes(workflow_original)
            mutate(workflow);receipt['project_export_workflow']=workflow
            receipt_path.write_text(json.dumps(receipt));workflow_path.write_text(json.dumps(workflow))
            with self.subTest(mutation=mutate.__name__),self.assertRaises(ValueError):self.verify()
        receipt_path.write_bytes(original);workflow_path.write_bytes(workflow_original)
        self.verify()

    def test_changed_project_screenshot_and_missing_source_helper_refuse(self):
        self.verify()
        for name in ('Evening Pulse Reopened.mmp','01-evening-pulse-project.png'):
            path=self.root/'msix-store-install/consumer-workflow'/name;original=path.read_bytes();path.write_bytes(b'changed')
            with self.subTest(name=name),self.assertRaises((ValueError,ParseError)):self.verify()
            path.write_bytes(original)
        del self.records['store']['sourceInputs'][subject.HELPERS[0]]
        with self.assertRaises((ValueError,KeyError)):self.verify()

    def test_runner_preparation_and_both_fresh_launch_absence_are_required(self):
        self.verify()
        for mode,folder in [('qualification','msix-install'),('store','msix-store-install')]:
            path=self.root/folder/'installation-qualification.json';original=path.read_bytes()
            receipt=subject.json_bytes(original);receipt.pop('runner_shell',None);path.write_text(json.dumps(receipt))
            with self.subTest(mode=mode),self.assertRaisesRegex(ValueError,'runner'):self.verify()
            path.write_bytes(original)
            for phase in ('preflight','before_activation'):
                for key,value in [('absent','true'),('state',dict(products=[],registry=[dict(foreign=True)],files=[],errors=[])),
                                  ('identity_mode','foreign'),('observed_utc','2026-09-12T12:00:00Z')]:
                    receipt=subject.json_bytes(original);receipt['runner_shell'][phase][key]=value;path.write_text(json.dumps(receipt))
                    with self.subTest(mode=mode,phase=phase,key=key),self.assertRaisesRegex(ValueError,'runner'):self.verify()
                    path.write_bytes(original)

    def test_runner_original_inputs_and_uninstall_are_independently_checked(self):
        path=self.root/'runner-shell-preparation.json';original=path.read_bytes()
        def verify_changed(value):
            path.write_text(json.dumps(value))
            # These are generated test package records only; refresh their file
            # hash to exercise semantic checks beyond stale-byte rejection.
            for record in self.records.values():record['evidenceInputs'][path.name]=subject.package.file_record(path)
            with self.assertRaisesRegex(ValueError,'runner'):self.verify()
            path.write_bytes(original)
            for record in self.records.values():record['evidenceInputs'][path.name]=subject.package.file_record(path)
        for field,value in [('prepared','true'),('error','observation failed'),('pin_sha256','f'*64),('after',dict(products=[],registry=[],files=[dict(foreign=True)],errors=[]))]:
            changed=subject.json_bytes(original);changed[field]=value
            with self.subTest(field=field):verify_changed(changed)
        for field,value in [('exit_code',3010),('exit_code','0'),('completed',False),('process_id',0),('arguments',['/x','foreign'])]:
            changed=subject.json_bytes(original);changed['uninstall'][field]=value
            with self.subTest(field=field,value=value):verify_changed(changed)
        changed=subject.json_bytes(original);changed['before']['files'][0]['sha256']='f'*64;changed['rechecked']=copy.deepcopy(changed['before'])
        verify_changed(changed)
        changed=subject.json_bytes(original);changed['rechecked']['products'][0]['values']['InstallLocation']='C:\\Program Files\\TortoiseSVN\\'
        verify_changed(changed)
        self.verify()


if __name__=='__main__':unittest.main()
