# Copyright 2026 Trieflow LLC. MIT. Read-only verification of actual UI-created files.
import argparse
import array
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
from pathlib import Path
import sys
import wave
import xml.etree.ElementTree as ET

SOURCE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SOURCE / 'tests/scripted'))
from starter_render import inspect_starter_wave, regular, sha256

TEMPO, BARS = 116, 4

def xml_file(path, boundary=None):
    path = Path(path)
    regular(path, boundary or path.parent)
    if not 0 < path.stat().st_size <= 2 * 1024 * 1024: raise ValueError('XML file exceeds bounds')
    data = path.read_bytes()
    if b'<!ENTITY' in data.upper() or b'<!DOCTYPE' in data.upper() and b'[' in data:
        raise ValueError('External/internal XML entities are not accepted')
    root = ET.fromstring(data)
    if len(list(root.iter())) > 10000: raise ValueError('XML element count exceeds bounds')
    return root

def canonical(element):
    def number(value):
        try:
            decimal = Decimal(value)
            if decimal.is_finite(): return str(decimal.normalize())
        except InvalidOperation: pass
        return value
    return [element.tag, sorted((key, number(value)) for key,value in element.attrib.items()),
            (element.text or '').strip(), [canonical(child) for child in element]]

def authored_attributes(expected, actual):
    if actual is None or actual.tag != expected.tag: raise ValueError('Missing authored element ' + expected.tag)
    for key,value in expected.attrib.items():
        got = actual.get(key)
        try: equal = got is not None and abs(Decimal(got)-Decimal(value)) < Decimal('0.0001')
        except InvalidOperation: equal = got == value
        if not equal: raise ValueError('Authored ' + expected.tag + '/' + key + ' differs')

def verify_projects(template, first, reopened, boundary):
    original = xml_file(template)
    if original.tag != 'lmms-project' or original.get('type') != 'songtemplate' or original.get('version') != '31':
        raise ValueError('Expected current original starter template')
    original.find('head').set('bpm',str(TEMPO))
    authored = original.findall('songtemplate/trackcontainer/track')
    if len(authored) != 3 or len(original.findall('.//note')) != 55: raise ValueError('Unexpected original musical fixture')
    semantics=[]
    for path in (first,reopened):
        root=xml_file(path,boundary)
        if root.tag != 'lmms-project' or root.get('type') != 'song' or root.get('version') != '31': raise ValueError('UI save is not a current song project')
        head=root.find('head'); authored_attributes(original.find('head'),head)
        tracks=root.findall('song/trackcontainer/track')
        if len(tracks) != 3 or len(root.findall('.//note')) != 55: raise ValueError('Saved track/note count differs')
        if any(root.findall('.//'+tag) for tag in ('sampleclip','audiofileprocessor','effect','automationclip','controller')):
            raise ValueError('Unexpected external resource, effect or automation')
        for expected,actual in zip(authored,tracks):
            authored_attributes(expected,actual)
            expected_instrument=expected.find('instrumenttrack'); instrument=actual.find('instrumenttrack')
            authored_attributes(expected_instrument,instrument)
            authored_attributes(expected_instrument.find('instrument'),instrument.find('instrument'))
            synth=instrument.find('instrument/kicker')
            authored_attributes(expected_instrument.find('instrument/kicker'),synth)
            if len(list(instrument.find('instrument'))) != 1: raise ValueError('Unexpected additional synth state')
            clips=actual.findall('midiclip'); expected_clips=expected.findall('midiclip')
            if len(clips) != BARS: raise ValueError('Saved clip count differs')
            for eclip,clip in zip(expected_clips,clips):
                authored_attributes(eclip,clip)
                notes=clip.findall('note'); enotes=eclip.findall('note')
                if len(notes) != len(enotes): raise ValueError('Saved phrase note count differs')
                for enote,note in zip(enotes,notes): authored_attributes(enote,note)
        semantics.append([canonical(head),[canonical(track) for track in tracks],
                          [canonical(node) for node in root.findall('song/mixer')]])
    if semantics[0] != semantics[1]: raise ValueError('The reopened in-memory project did not preserve full head/track/mixer semantics')
    return {'template_sha256':sha256(template),'first_sha256':sha256(first),'reopened_sha256':sha256(reopened),
            'tempo':TEMPO,'bars':BARS,'tracks':3,'notes':55,'reopened_semantics_equal':True,
            'semantic_sha256':hashlib.sha256(json.dumps(semantics[0],sort_keys=True).encode()).hexdigest()}

def verify_wave(path,boundary):
    path=regular(path,boundary)
    if not 44 < path.stat().st_size <= 4*1024*1024: raise ValueError('WAV exceeds the bounded arrangement size')
    # Same tested independent file inspection used by the CLI renderer; no CLI launch here.
    result=inspect_starter_wave(path,BARS,TEMPO)
    with wave.open(str(path),'rb') as stream:
        samples=array.array('h',stream.readframes(stream.getnframes()))
    if sys.byteorder != 'little': samples.byteswap()
    rms=[]; ac_rms=[]
    for bar in range(BARS):
        start=round(bar*240/TEMPO*44100)*2; end=round((bar+1)*240/TEMPO*44100)*2
        data=samples[start:end]
        value=math.sqrt(sum(sample*sample for sample in data)/len(data)) if data else 0
        if value <= 10: raise ValueError('One actual arrangement bar is silent or too quiet')
        mean=sum(data)/len(data)
        ac=math.sqrt(max(0,value*value-mean*mean))
        if ac <= 10 or max(data)-min(data) < 100: raise ValueError('Arrangement bar contains DC instead of musical audio')
        rms.append(value); ac_rms.append(ac)
    result['arrangement_bar_rms_pcm16']=rms
    result['arrangement_bar_ac_rms_pcm16']=ac_rms
    result['expected_padding_bars']=1
    return result

# Source-traced editor destructor preferences. No new arbitrary settings or paths are accepted.
UI_EXIT_FIELDS={'songeditorzoom','songeditorsnap','pianorollzoom','pianorollzoomvertical',
                'pianorollquantization','pianorollnotelength','pianorollsnap'}

def verify_profile(before,after,working,projects):
    first=xml_file(before); second=xml_file(after)
    if first.tag != 'lmms' or second.tag != 'lmms' or first.attrib != second.attrib: raise ValueError('Profile root changed')
    def normalize(path): return str(path).replace('\\','/').rstrip('/').casefold()
    for root in (first,second):
        paths=root.findall('paths')
        if len(paths)!=1 or normalize(paths[0].get('workingdir','')) != normalize(working): raise ValueError('Profile workingdir is not owned')
        if len(root.findall('recentfiles')) != 1 or len({child.tag for child in root}) != len(root): raise ValueError('Ambiguous profile sections')
    allowed={normalize(path) for path in projects}
    changed=[]
    for name in sorted(set(child.tag for child in first) | set(child.tag for child in second)):
        old=first.find(name); new=second.find(name)
        if old is None or new is None: raise ValueError('Profile section appeared/disappeared: '+name)
        if name=='recentfiles':
            if new.attrib or old.attrib: raise ValueError('Unexpected recentfiles attributes')
            for entry in list(old)+list(new):
                if entry.tag!='file' or set(entry.attrib)!={'path'} or list(entry) or normalize(entry.get('path')) not in allowed: raise ValueError('Foreign recent project in owned profile')
            if canonical(old)!=canonical(new): changed.append('recentfiles')
        elif name=='ui':
            if list(old) or list(new): raise ValueError('Unexpected nested UI profile settings')
            for key in old.attrib.keys() | new.attrib.keys():
                if old.get(key)!=new.get(key):
                    if key not in UI_EXIT_FIELDS or new.get(key) is None or not new.get(key).isdigit() or int(new.get(key))>1024: raise ValueError('Untracked UI profile change: '+key)
                    changed.append('ui/'+key)
        elif canonical(old)!=canonical(new): raise ValueError('Untracked profile change: '+name)
    return {'before_sha256':sha256(before),'after_sha256':sha256(after),'changed_fields':changed,'working_directory_verified':True}

def main():
    parser=argparse.ArgumentParser(); sub=parser.add_subparsers(dest='command',required=True)
    project=sub.add_parser('project'); project.add_argument('--template',required=True); project.add_argument('--first',required=True); project.add_argument('--reopened',required=True); project.add_argument('--root',required=True)
    audio=sub.add_parser('wave'); audio.add_argument('--path',required=True); audio.add_argument('--root',required=True)
    profile=sub.add_parser('profile'); profile.add_argument('--before',required=True); profile.add_argument('--after',required=True); profile.add_argument('--working',required=True); profile.add_argument('--project',action='append',default=[])
    args=parser.parse_args()
    if args.command=='project': result=verify_projects(args.template,args.first,args.reopened,args.root)
    elif args.command=='wave': result=verify_wave(args.path,args.root)
    else: result=verify_profile(args.before,args.after,args.working,args.project)
    print(json.dumps(result,sort_keys=True))

if __name__=='__main__': main()
