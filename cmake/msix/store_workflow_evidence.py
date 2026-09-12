"""Read-only export boundary for the two actual installed consumer lifecycles."""
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path, PureWindowsPath
import re

import consumer_files
import msix_qualification as package

OPERATIONS = ['Preflight','PrepareSignedCopy','Install','ActivateAndVerify','ConsumerWorkflow','CloseCleanly','UninstallAndVerify']
CLEANUP = ['StopOwnedProcess','RemoveOwnedPackage','RemoveTrustedCertificate','RemovePersonalCertificate',
           'RemoveOwnedProfile','RemoveOwnedWorkingDirectory','RestoreDisplay','RemoveTemporaryFiles']
HELPERS = ['cmake/msix/qualify-msix-install.ps1','cmake/msix/consumer-workflow.ps1','cmake/msix/consumer-display.ps1',
           'cmake/msix/first-run.ps1','cmake/msix/consumer_files.py','tests/scripted/starter_render.py',
           'cmake/msix/verify_record.py','cmake/msix/msix_qualification.py','cmake/msix/qualification-bindings.ps1',
           'cmake/msix/ms_runtime_origins.py','cmake/msix/runner-shell.ps1','distribution/runner-shell-inputs.json']
STAGES = ['original_template_opened','song_editor_maximized'] + [f'tempo_value_{x}' for x in range(112,117)] + [
          'project_saved','new_empty_project_before_reopen','reopened_project_verified','export_settings',
          'actual_export_completed','stopped_project_unchanged']
MAIN = 'BeatSprig 1.0.1'
SUFFIX = ' - [Song-Editor]'
TEMPLATE = 'data/projects/templates/BeatSprig-Drum-Grid.mpt'


def same(actual, expected, label):
    if type(actual) is not type(expected) or (actual!=expected if isinstance(expected,bytes) else
        json.dumps(actual, sort_keys=True, allow_nan=False) != json.dumps(expected, sort_keys=True, allow_nan=False)):
        raise ValueError('Mismatched ' + label)


def digest(value, label='SHA256'):
    if not isinstance(value,str) or not re.fullmatch('[0-9a-f]{64}',value): raise ValueError('Invalid '+label)
    return value


def integer(value, minimum=0, label='integer'):
    if type(value) is not int or value < minimum: raise ValueError('Invalid '+label)
    return value


def number(value, minimum=0, label='number'):
    if type(value) not in (int,float) or not math.isfinite(value) or value < minimum: raise ValueError('Invalid '+label)
    return value


def utc(value):
    if not isinstance(value,str): raise ValueError('Missing UTC observation time')
    match=re.fullmatch(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d{1,7}))?(?:Z|\+00:00)',value)
    if not match: raise ValueError('Observation time must be explicit UTC')
    # .NET emits seven fractional digits; Python 3.10 accepts six. Original
    # receipt bytes stay unchanged. Truncation is conservative for the strict
    # first-completed < second-started check; equal microseconds are refused.
    normalized=match[1]+'.'+(match[2] or '').ljust(6,'0')[:6]+'+00:00'
    try: result=datetime.fromisoformat(normalized)
    except ValueError as error: raise ValueError('Invalid UTC observation time') from error
    if result.tzinfo is None or result.utcoffset().total_seconds()!=0: raise ValueError('Observation time must be UTC')
    return result


def json_bytes(data):
    def pairs(items):
        result={}
        for key,value in items:
            if key in result: raise ValueError('Duplicate JSON key: '+key)
            result[key]=value
        return result
    def invalid(value): raise ValueError('Non-finite JSON number: '+value)
    return json.loads(data.decode('utf-8-sig'),object_pairs_hook=pairs,parse_constant=invalid)


def read(path, limit=16*1024*1024):
    path=Path(path).absolute()
    for parent in path.parents:package._reject_link(parent)
    with package._regular_stream(path) as stream: data=stream.read(limit+1)
    if len(data)>limit: raise ValueError('Oversized export evidence')
    return data


def load(path): return json_bytes(read(path))


def windows(value):
    if not isinstance(value,str) or '\0' in value or '..' in PureWindowsPath(value).parts: raise ValueError('Unsafe observed Windows path')
    path=PureWindowsPath(value)
    if not path.is_absolute() or path.drive.startswith('\\'): raise ValueError('Expected absolute local Windows path')
    return path


def verify_runner_shell(root, source, record, receipt, mode, start, end, first_stage):
    """Independently check the original runner preparation and two live reads."""
    pin=load(source/'distribution/runner-shell-inputs.json')
    path=root/'runner-shell-preparation.json'; preparation=load(path); measured=package.file_record(path)
    same(record['evidenceInputs'].get(path.name),measured,'runner preparation bytes in original package')
    same(preparation.get('schema_version'),1,'runner schema')
    same(preparation.get('binding'),{key:receipt[key] for key in ('source_commit','workflow_run_id','workflow_run_attempt')},'runner source/run/attempt')
    same(preparation.get('pin_sha256'),package.file_record(source/'distribution/runner-shell-inputs.json')['sha256'],'runner original pin')
    context=dict(windows=True,os64=True,process64=True,ci='true',actions='true',environment='github-hosted',
                 repository=pin['repository'],image_os=pin['image_os'],image_version=pin['image_version'],system_root='C:\\Windows')
    same(preparation.get('context'),context,'runner image/context')
    same(preparation.get('prepared'),True,'runner prepared');same(preparation.get('error'),None,'runner preparation error')
    before=preparation.get('before',{});same(preparation.get('rechecked'),before,'runner inputs unchanged before uninstall')
    same(before.get('errors'),[],'runner original observation errors')
    products=before.get('products',[])
    if len(products)!=1: raise ValueError('Unknown runner products')
    product=products[0];values=product.get('values',{})
    for key,value in dict(hive='LocalMachine',view='Registry64',key=pin['product']['code']).items():same(product.get(key),value,'runner product '+key)
    for key,value in dict(DisplayName=pin['product']['name'],DisplayVersion=pin['product']['version'],Publisher='TortoiseSVN',WindowsInstaller=1).items():same(values.get(key),value,'runner product '+key)
    if values.get('InstallLocation') not in ('','C:\\Program Files\\TortoiseSVN\\') or values.get('UninstallString') not in tuple('MsiExec.exe /'+flag+pin['product']['code'] for flag in ('I','X')):raise ValueError('Unknown runner product path/command')
    for key,order in [('files',('path',)),('registry',('hive','view','key','name'))]:
        sort=lambda row:tuple(row.get(k,'') for k in order)
        same(sorted(before.get(key,[]),key=sort),sorted(pin[key],key=sort),'runner original '+key)
    absent=dict(products=[],registry=[],files=[],errors=[])
    same(preparation.get('after'),absent,'runner absent after uninstall')
    native=preparation.get('uninstall',{})
    for key,value in dict(completed=True,exit_code=0,observation_error=None).items():same(native.get(key),value,'runner original uninstall '+key)
    integer(native.get('process_id'),1,'runner original MSI PID')
    same(native.get('arguments'),['/x',pin['product']['code'],'/qn','/norestart','REBOOT=ReallySuppress'],'runner exact MSI command')
    program=native.get('program',{});same(program.get('path'),'C:\\Windows\\System32\\msiexec.exe','runner exact MSI executable')
    integer(program.get('bytes'),1,'runner MSI bytes');digest(program.get('sha256'),'runner MSI hash')
    if not utc(preparation.get('started_utc'))<utc(preparation.get('completed_utc'))<start:raise ValueError('Invalid runner preparation time order')
    observations=receipt.get('runner_shell',{})
    if set(observations)!= {'preflight','before_activation'}:raise ValueError('Missing both runner absence observations')
    previous=start
    for phase in ('preflight','before_activation'):
        observed=observations[phase]
        same(observed.get('identity_mode'),mode,'runner observation identity')
        same(observed.get('context'),context,'runner fresh context')
        same(observed.get('absent'),True,'runner fresh absence');same(observed.get('state'),absent,'runner fresh registry/files')
        original=observed.get('preparation',{})
        same({key:original.get(key) for key in ('bytes','sha256')},measured,'runner observed original preparation')
        if windows(original.get('path')).name!='runner-shell-preparation.json':raise ValueError('Wrong runner preparation filename')
        now=utc(observed.get('observed_utc'))
        if not previous<=now<min(end,first_stage):raise ValueError('Invalid runner fresh launch observation order')
        previous=now
    return dict(preparation=measured,uninstallExitCode=0,observations=observations)


def verify_wave_receipt(row):
    expected={'channels':2,'sample_rate':44100,'sample_width_bytes':2,'expected_padding_bars':1}
    for key,value in expected.items(): same(row.get(key),value,'WAV '+key)
    frames=integer(row.get('frames'),1,'WAV frames'); size=integer(row.get('bytes'),45,'WAV size')
    duration=number(row.get('duration_seconds'),0,'WAV duration')
    peak=integer(row.get('peak_pcm16'),100,'WAV peak'); rms=number(row.get('rms_pcm16'),0,'WAV RMS')
    if (abs(duration-frames/44100)>1e-9 or abs(duration-5*240/116)>=0.25 or
        not 44+4*frames<=size<=4*1024*1024 or peak>=32767 or not 10<rms<=peak):
        raise ValueError('WAV duration/PCM16/file/energy bounds differ from independent inspector')
    for key in ('arrangement_bar_rms_pcm16','arrangement_bar_ac_rms_pcm16'):
        values=row.get(key)
        if not isinstance(values,list) or len(values)!=4: raise ValueError('Missing all four musical bar metrics')
        if any(not 10<number(value,0,'bar energy')<=peak for value in values): raise ValueError('Silent or invalid musical bar energy')
    if any(ac>rms+1e-6 for rms,ac in zip(row['arrangement_bar_rms_pcm16'],row['arrangement_bar_ac_rms_pcm16'])):
        raise ValueError('AC energy exceeds total energy')
    digest(row.get('sha256'),'WAV hash')


def verify_window(window, process_id, title=None, handle=None):
    same(window.get('truncated'),False,'complete window inventory')
    same(window.get('process_id'),process_id,'window process')
    root=window.get('root',{})
    for key,value in {'available':True,'visible':True,'enabled':True,'process_id':process_id}.items(): same(root.get(key),value,'window root '+key)
    if title is not None:
        same(window.get('title'),title,'observed title');same(root.get('name'),title,'observed root name')
    if handle is not None: same(root.get('native_window_handle'),handle,'retained main HWND')
    if type(root.get('native_window_handle')) is not int or root['native_window_handle']==0: raise ValueError('Missing actual window handle')
    for name in ('width','height'): number(root.get(name),1,'window '+name)
    for name in ('x','y'): number(root.get(name),-32768,'window '+name)
    if not isinstance(window.get('controls'),list) or not 0<len(window['controls'])<=750: raise ValueError('Missing bounded window controls')


def control(window, process_id, kind, name, enabled=True):
    found=[row for row in window['controls'] if row.get('type')==kind and row.get('name')==name and
           row.get('available') is True and row.get('visible') is True and row.get('enabled') is enabled and
           type(row.get('process_id')) is int and row['process_id']==process_id]
    if len(found)!=1: raise ValueError('Missing unique owned '+kind+': '+name)
    return found[0]


def verify_modules(rows, record, full_name, after):
    if not isinstance(rows,list) or not rows or len(rows)>512: raise ValueError('Missing bounded loaded module inventory')
    seen=set(); packaged=set()
    payload={name.casefold():(name,row) for name,row in record['payload'].items()}
    if len(payload)!=len(record['payload']): raise ValueError('Ambiguous Windows payload path')
    for row in rows:
        path=windows(row.get('path')); key=str(path).casefold()
        if key in seen: raise ValueError('Duplicate loaded module')
        seen.add(key); digest(row.get('sha256'),'loaded module hash')
        same(path.name.casefold(),str(row.get('name')).casefold(),'module basename')
        if row.get('origin')=='package':
            relative=package._checked_path(row.get('relative_path'))
            # The Windows loader records CRT basenames in uppercase. Preserve
            # that observation; match the unique package path case-insensitively
            # just as the production PowerShell payload lookup does.
            match=payload.get(relative.casefold())
            if match is None or row['sha256']!=match[1]['sha256']: raise ValueError('Loaded package module differs')
            parts=tuple(x.casefold() for x in path.parts)
            tail=('windowsapps',full_name.casefold(),*PureWindowsPath(relative).parts)
            if parts[-len(tail):]!=tuple(x.casefold() for x in tail): raise ValueError('Loaded module is outside exact installed package')
            packaged.add(match[0])
        elif row.get('origin')=='windows':
            if len(path.parts)<3 or path.parts[1].casefold()!='windows' or row.get('relative_path') is not None: raise ValueError('Unexpected OS module path')
        elif row.get('origin')=='microsoft_defender_signed_platform':
            if not re.fullmatch(r'[A-Za-z]:\\ProgramData\\Microsoft\\Windows Defender\\Platform\\\d+\.\d+\.\d+\.\d+-\d+\\MpOav\.dll',str(path)): raise ValueError('Unexpected Defender module')
            signature=row.get('platform_signature',{})
            for key,value in {'signature_status':'Valid','signer_organization':'Microsoft Corporation','sha256':row['sha256']}.items(): same(signature.get(key),value,'Defender '+key)
            if signature.get('signer_common_name') not in ('Microsoft Windows Publisher','Microsoft Corporation','Microsoft Windows'): raise ValueError('Unexpected Defender signer')
            for key in ('signer_subject','signer_issuer','signer_thumbprint'):
                if not isinstance(signature.get(key),str) or not signature[key]: raise ValueError('Missing Defender certificate observation')
        else: raise ValueError('Unreviewed loaded module origin')
    required=set(record['runtime'].values()) | ({'plugins/kicker.dll'} if after else set())
    if not required<=packaged: raise ValueError('Required packaged runtime/instrument was not loaded')


def verify_lifecycle(directory, record, source, commit, run_id, attempt, mode):
    directory=Path(directory); source=Path(source); workflow_dir=directory/'consumer-workflow'
    receipt=load(directory/'installation-qualification.json'); workflow=load(workflow_dir/'consumer-workflow.json')
    same(receipt.get('schema_version'),1,'installed schema')
    bindings={'source_commit':commit,'workflow_run_id':run_id,'workflow_run_attempt':attempt,'identity_mode':mode}
    for key,value in bindings.items(): same(receipt.get(key),value,'installed '+key);same(workflow.get(key),value,'consumer '+key)
    same(receipt.get('identity'),package.identity_for(mode),'installed fixed identity')
    for key in ('add_appx_completed','registration_ownership_established','unsigned_package_unchanged','process_identity_ownership_established',
                'installed_identity_verified','clean_close_verified','uninstall_verified','installation_qualification_passed','workflow_acceptance'):
        same(receipt.get(key),True,'installed '+key)
    for key,value in {'qualification_identity_only':mode=='qualification','store_identity_used':mode=='store',
                      'certificate_private_key_exported':False,'public_release':False}.items(): same(receipt.get(key),value,'installed '+key)
    for key in ('primary_error','loaded_module_rejection'):
        if key not in receipt: raise ValueError('Missing explicit installed '+key)
        same(receipt[key],None,key)
    for key in ('cleanup_errors','evidence_errors','preflight_package_full_names','residual_package_full_names'): same(receipt.get(key),[],key)
    same(receipt.get('completed_operations'),OPERATIONS,'completed full workflow')
    same(receipt.get('completed_cleanup'),CLEANUP,'completed every cleanup')
    start=utc(receipt.get('qualification_started_at_utc')); end=utc(receipt.get('generated_at_utc'))
    if end<=start: raise ValueError('Lifecycle time order is invalid')
    runner_shell=verify_runner_shell(directory.parent,source,record,receipt,mode,start,end,utc(workflow['stages'][0]['observed_utc']))
    publisher_id='r3hxytd7jt6c4' if mode=='store' else 'a74jba1vjrwc6'
    family=record['identity']['packageName']+'_'+publisher_id
    full=record['identity']['packageName']+'_1.0.1.0_x64__'+publisher_id
    for key in ('package_full_name','owned_package_full_name','activated_process_package_full_name'): same(receipt.get(key),full,key)
    same(receipt.get('aumid'),family+'!BeatQuay','broker AUMID')
    unsigned=record['containerVerification']['package']['sha256']
    same(receipt.get('unsigned_package_sha256'),unsigned,'qualified unsigned package')
    if digest(receipt.get('signed_copy_sha256'))==unsigned: raise ValueError('Signed installation copy equals unsigned original')
    executable=record['payload']['beatsprig.exe']['sha256'];same(receipt.get('executable_sha256'),executable,'installed executable')
    helper_map={name:package.file_record(source/name) for name in HELPERS}
    for name,value in helper_map.items(): same(record['sourceInputs'].get(name),value,'source-bound helper '+name)
    same(receipt.get('helper_bindings'),helper_map,'installed helper bytes');same(workflow.get('helper_bindings'),helper_map,'consumer helper bytes')
    same(receipt.get('project_export_workflow'),workflow,'separate original consumer receipt')
    process_id=integer(workflow.get('process_id'),1,'owned process ID')
    for key in ('process_exit','cleanup_process_exit'):
        exit_record=receipt.get(key,{})
        for field,value in {'process_id':process_id,'wait_completed':True,'exit_code':0,'normal_exit':True,'observation_error':None}.items(): same(exit_record.get(field),value,key+' '+field)
    for key in ('owned_profile','working_directory'):
        owned=receipt.get(key,{})
        for field,value in {'source_commit':commit,'ownership_established':True,'process_id':process_id,'package_full_name':full,'cleanup_verified':True}.items(): same(owned.get(field),value,key+' '+field)
        windows(owned.get('path'))
    profile=receipt['owned_profile']; working=receipt['working_directory']
    same(profile.get('absent_before_activation'),True,'absent original profile');same(working.get('absent_before_action'),True,'absent original working directory')
    same(working.get('action_invoked'),True,'normal working directory creation')
    digest(profile.get('sha256'));digest(working.get('marker_sha256'))
    if windows(profile['path']).name!='.beatquayrc.xml' or windows(working['path']).name!='BeatQuay': raise ValueError('Compatible data paths changed')
    observations=profile.get('observations')
    if not isinstance(observations,list) or len(observations)<2 or observations[0].get('action')!='normal_first_run' or observations[-1].get('action')!='normal_close': raise ValueError('Missing first-run and normal-close profile readbacks')
    same(observations[-1].get('sha256'),profile['sha256'],'normal-close profile hash')
    for observation in observations:
        if not start<=utc(observation.get('observed_utc'))<=end: raise ValueError('Profile observation outside lifecycle')
        digest(observation.get('sha256'))
        if not isinstance(observation.get('changed_fields'),list) or any(field!='recentfiles' and field not in {'ui/'+x for x in consumer_files.UI_EXIT_FIELDS} for field in observation['changed_fields']): raise ValueError('Untracked profile field in receipt')
    first=receipt.get('first_run',{}); prompt=first.get('working_directory',{})
    for key,value in {'title':'Working directory','path':working['path'],'process_id':process_id,'visible':True,'action_name':'Yes','action_invoked':True}.items(): same(prompt.get(key),value,'first-run '+key)
    message='The BeatSprig working directory '+working['path'].replace('\\','/').rstrip('/')+'/ does not exist. Create it now? You can change the directory later via Edit -> Settings.'
    same(prompt.get('message'),message,'exact creation prompt')
    for key,value in {'setup_title':'BeatSprig - Settings','setup_visible':True,'action_name':'OK','action_invoked':True,'editor_title':MAIN,'editor_visible':True}.items(): same(first.get(key),value,'first-run '+key)
    window=load(directory/'window-observation.json');same(receipt.get('window'),window,'original startup observation')
    for key,value in {'title':MAIN,'process_id':process_id,'visible':True,'screenshot_captured':True,'actionable_controls_verified':True,'startup_limited':False,'screenshot_error':None}.items(): same(window.get(key),value,'startup '+key)
    number(window.get('sampled_colors'),16,'startup rendered colors');integer(window.get('actionable_control_count'),1)
    main_handle=workflow.get('main_window_handle')
    if type(main_handle) is not int or main_handle==0: raise ValueError('Missing retained main HWND')
    same(window.get('main_window_handle'),main_handle,'startup/consumer main HWND')
    startup_png=read(directory/'qualification-window.png')
    same(hashlib.sha256(startup_png).hexdigest(),window.get('screenshot_sha256'),'startup screenshot bytes')
    same(list(package.png_dimensions(startup_png)),[int(number(window.get('width'),400)),int(number(window.get('height'),300))],'startup screenshot dimensions')
    before=load(directory/'loaded-modules.json');after=load(directory/'loaded-modules-after-workflow.json')
    verify_modules(before,record,full,False);verify_modules(after,record,full,True)
    same(receipt.get('loaded_module_count'),len(after),'final module count')
    verify_consumer(workflow,workflow_dir,source,record,process_id,main_handle,full,bindings,start,end)
    display=receipt.get('native_display',{})
    for key,value in {'restore_verified':True,'restore_result':0,'test_result':0,'apply_result':0,'registry_updated':False,'unsafe_modes_enabled':False,'dpi_changed':False,'renderer_emulation_used':False}.items(): same(display.get(key),value,'native display '+key)
    same(display.get('restored'),display.get('before'),'original display restored');same(display.get('after'),display.get('selected'),'selected real display applied')
    if display['selected'] not in display.get('supported_modes',[]): raise ValueError('Unobserved native display mode')
    for screen in workflow['screenshots']: same(screen.get('display'),display['after'],'screenshot native mode')
    files={name:package.file_record(directory/name) for name in ('installation-qualification.json','window-observation.json','qualification-window.png','loaded-modules.json','loaded-modules-after-workflow.json')}
    files.update({'consumer-workflow/'+name:package.file_record(workflow_dir/name) for name in ['consumer-workflow.json','Evening Pulse.mmp','Evening Pulse Reopened.mmp']+[x['file'] for x in workflow['screenshots']]})
    return dict(identityMode=mode,packageFullName=full,packageSha256=unsigned,sourceCommit=commit,workflowRunId=run_id,
        workflowRunAttempt=attempt,processId=process_id,mainWindowHandle=main_handle,startedAtUtc=start.isoformat(),
        completedAtUtc=end.isoformat(),verifiedFiles=files,helperBindings=helper_map,projectVerification=workflow['file_verification'],
        recordedWaveVerification=workflow['wave_verification'],waveRereadAfterCleanup=False,runnerShellPreparation=runner_shell)


def verify_consumer(workflow, directory, source, record, process_id, main_handle, full, bindings, start, end):
    for key,value in {'schema_version':1,'package_full_name':full,'package_sha256':record['containerVerification']['package']['sha256'],
        'executable_sha256':record['payload']['beatsprig.exe']['sha256'],'acceptance':True,'primary_error':None,
        'cli_render_used':False,'physical_audio_output_claimed':False,'song_editor_maximized':True,
        'current_action':'stop_transport_and_verify_persistence'}.items(): same(workflow.get(key),value,'consumer '+key)
    if workflow.get('profile_attribution_error') is not None: raise ValueError('Consumer profile attribution failed')
    stages=workflow.get('stages',[]);same([x.get('stage') for x in stages],STAGES,'complete ordered real consumer stages')
    previous=start
    windows_by_stage={}
    for entry in stages:
        when=utc(entry.get('observed_utc'))
        if not previous<=when<=end: raise ValueError('Consumer stage time order differs')
        previous=when; window=entry.get('window',{});stage=entry['stage'];windows_by_stage[stage]=window
        if stage.startswith('tempo_value_'):
            verify_window(window,process_id,'BeatSprig')
            same(window['root'].get('class_name'),'lmms::gui::CaptionMenu','tempo menu root')
            for name,enabled in [('Tempo',False),('Copy value ('+stage.removeprefix('tempo_value_')+')',True)]:
                item=control(window,process_id,'MenuItem',name,enabled)
                same(item.get('class_name'),'QAction','tempo action class');same(item.get('automation_id'),'QApplication.lmms::gui::CaptionMenu.QAction','tempo action ancestry')
        else:
            title={'original_template_opened':MAIN,'song_editor_maximized':MAIN+SUFFIX,
                'project_saved':'Evening Pulse - '+MAIN+SUFFIX,'new_empty_project_before_reopen':MAIN+SUFFIX,
                'reopened_project_verified':'Evening Pulse Reopened - '+MAIN+SUFFIX,
                'export_settings':'Export project','actual_export_completed':'Export completed',
                'stopped_project_unchanged':'Evening Pulse Reopened - '+MAIN+SUFFIX}[stage]
            verify_window(window,process_id,title,None if stage in ('export_settings','actual_export_completed') else main_handle)
    paths=workflow.get('project_paths',{})
    for key,name in [('first','Evening Pulse.mmp'),('reopened','Evening Pulse Reopened.mmp'),('wave','Evening Pulse.wav')]:
        if windows(paths.get(key)).name!=name: raise ValueError('Unexpected actual consumer output path')
    if len({windows(path).parent for path in paths.values()})!=1: raise ValueError('Consumer output roots differ')
    project=consumer_files.verify_projects(source/TEMPLATE,directory/'Evening Pulse.mmp',directory/'Evening Pulse Reopened.mmp',directory)
    same(workflow.get('file_verification'),project,'independent retained project semantics/bytes')
    same(project['template_sha256'],record['payload'][TEMPLATE]['sha256'],'original packaged starter')
    wave=workflow.get('wave_verification',{});verify_wave_receipt(wave)
    result=windows_by_stage['actual_export_completed']
    details=[x for x in result['controls'] if x.get('type')=='Edit' and x.get('available') is True and x.get('visible') is True and x.get('process_id')==process_id and x.get('value')]
    if len(details)!=1: raise ValueError('Missing exact real export completion details')
    lines=[x for x in details[0]['value'].replace('\r','').split('\n') if x]
    if lines: lines[0]=lines[0].replace('\\','/')
    same(lines,[paths['wave'].replace('\\','/'),'Completed: '+str(wave['bytes'])+' bytes'],'export completion path/bytes')
    settings=windows_by_stage['export_settings']
    same(workflow.get('export_loop_settings'),{'Export as loop (remove extra bar)':'Off','Export between loop markers':'Off'},'observed unchanged loop settings')
    control(settings,process_id,'Button','Start')
    for kind,name in [('Text','Sampling rate:'),('Text','Bit depth:'),('CheckBox','Export as loop (remove extra bar)'),('CheckBox','Export between loop markers')]:control(settings,process_id,kind,name)
    inputs=workflow.get('inputs')
    if not isinstance(inputs,list) or not 15<=len(inputs)<=100: raise ValueError('Missing bounded real consumer inputs')
    wheels=[x for x in inputs if x.get('kind')=='native_tempo_wheel'];same(len(wheels),4,'four non-replayed tempo detents')
    for wheel in wheels: same(wheel.get('wheel_delta'),120,'tempo detent');same(wheel.get('action'),'edit_tempo_116','tempo action')
    for action,kind,name in [('new_from_original_template','MenuItem','File'),('new_from_original_template','MenuItem','New from template'),
        ('new_from_original_template','MenuItem','BeatSprig-Drum-Grid'),('export_project_wav','ListItem','44100 Hz'),
        ('export_project_wav','ListItem','16 Bit integer'),('export_project_wav','Button','Start'),
        ('stop_transport_and_verify_persistence','Button','Stop (Space)')]:
        matches=[x for x in inputs if x.get('kind')=='native_click' and x.get('action')==action and x.get('control',{}).get('type')==kind and x['control'].get('name')==name]
        if len(matches)!=1: raise ValueError('Missing exact observed consumer input '+name)
    for item in inputs:
        selected=item.get('control')
        if selected:
            for key,value in {'available':True,'visible':True,'enabled':True,'process_id':process_id}.items():same(selected.get(key),value,'input '+key)
    for action,key in [('save_original_project','first'),('new_then_reopen_saved_project','first'),('save_reopened_memory_to_new_project','reopened'),('export_project_wav','wave')]:
        values=[x for x in inputs if x.get('action')==action and x.get('kind')=='uia_value']
        if len(values)!=1: raise ValueError('Missing exact file dialog value receipt')
        same(values[0].get('value'),paths[key],'actual filename readback')
        same(values[0]['control'].get('automation_id'),'QApplication.QFileDialog.fileNameEdit','filename field ancestry')
        same(values[0]['control'].get('class_name'),'QLineEdit','filename field class')
    screens=workflow.get('screenshots');expected=['01-evening-pulse-project.png','02-export-project.png','03-export-completed.png']
    same([x.get('file') for x in screens] if isinstance(screens,list) else None,expected,'three exact working captures')
    for index,screen in enumerate(screens):
        for key,value in dict(bindings,process_id=process_id,main_window_handle=main_handle,package_full_name=full,
            package_sha256=record['containerVerification']['package']['sha256'],executable_sha256=record['payload']['beatsprig.exe']['sha256'],dpi=96).items():same(screen.get(key),value,'screen '+key)
        if not start<=utc(screen.get('captured_utc'))<=end: raise ValueError('Capture lies outside lifecycle')
        if type(screen.get('foreground_window')) is not int or screen['foreground_window']==0: raise ValueError('Missing foreground observation')
        same(screen.get('project_title'),('Evening Pulse' if index==0 else 'Evening Pulse Reopened')+' - '+MAIN+SUFFIX,'captured project')
        same(screen.get('allowed_dialogs'),[[],['Export project'],['Export project','Export completed']][index],'captured modal context')
        data=read(directory/screen['file']);same(hashlib.sha256(data).hexdigest(),digest(screen.get('sha256')),'capture bytes')
        width=integer(screen.get('width'),1400);height=integer(screen.get('height'),850)
        same(list(package.png_dimensions(data)),[width,height],'raw capture dimensions')
        display=screen.get('display',{});x=integer(screen.get('x'),0);y=integer(screen.get('y'),0)
        if x+width>integer(display.get('width'),width) or y+height>integer(display.get('height'),height): raise ValueError('Capture outside native desktop')


def verify_lifecycles(evidence, records, source, commit, run_id, attempt):
    result={mode:verify_lifecycle(Path(evidence)/folder,records[mode],source,commit,run_id,attempt,mode)
            for mode,folder in [('qualification','msix-install'),('store','msix-store-install')]}
    if utc(result['qualification']['completedAtUtc'])>=utc(result['store']['startedAtUtc']): raise ValueError('Store lifecycle began before disposable cleanup completed')
    if records['qualification']['releaseInput']!=records['store']['releaseInput']: raise ValueError('The two identities did not use the same native stage')
    return result
