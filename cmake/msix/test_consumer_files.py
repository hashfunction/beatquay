# Copyright 2026 Trieflow LLC. MIT. Synthetic files test the independent verifier, never UI acceptance.
import array
import copy
import math
from pathlib import Path
import sys
import tempfile
import unittest
import wave
import xml.etree.ElementTree as ET

import consumer_files as subject
SOURCE = Path(__file__).resolve().parents[2]
TEMPLATE = SOURCE / 'data/projects/templates/BeatSprig-Drum-Grid.mpt'

class ConsumerFilesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / 'Evening Pulse.mmp'
        self.reopened = self.root / 'Evening Pulse Reopened.mmp'
        self.doc = ET.parse(TEMPLATE).getroot()
        self.doc.set('type', 'song'); self.doc.find('songtemplate').tag = 'song'
        self.doc.find('head').set('bpm', '116')
        self.write()
    def write(self):
        ET.ElementTree(self.doc).write(self.project, encoding='utf-8', xml_declaration=True)
        self.reopened.write_bytes(self.project.read_bytes())
    def check(self):
        return subject.verify_projects(TEMPLATE, self.project, self.reopened, self.root)
    def test_full_original_arrangement_with_actual_edit_and_reopened_save(self):
        got = self.check(); self.assertEqual(got['notes'], 55); self.assertEqual(got['tracks'], 3)
        self.assertEqual(got['tempo'], 116); self.assertEqual(got['bars'], 4)
        self.assertTrue(got['reopened_semantics_equal'])
    def test_unchanged_template_tempo_is_not_a_completed_edit(self):
        self.doc.find('head').set('bpm', '112'); self.write()
        with self.assertRaisesRegex(ValueError, 'bpm'): self.check()
    def test_note_instrument_track_and_clip_mutations_are_rejected(self):
        original = copy.deepcopy(self.doc)
        changes = [('song/trackcontainer/track/midiclip/note','key','61'),
                   ('song/trackcontainer/track/instrumenttrack','vol','0'),
                   ('song/trackcontainer/track/instrumenttrack/instrument/kicker','noise','1'),
                   ('song/trackcontainer/track','muted','1'),
                   ('song/trackcontainer/track/midiclip','pos','1')]
        for path,key,value in changes:
            with self.subTest(path=path,key=key):
                self.doc=copy.deepcopy(original); self.doc.find(path).set(key,value); self.write()
                with self.assertRaises(ValueError): self.check()
    def test_missing_extra_notes_and_tracks_are_rejected(self):
        original = copy.deepcopy(self.doc)
        for path in ['song/trackcontainer', 'song/trackcontainer/track/midiclip']:
            for add in (False,True):
                self.doc=copy.deepcopy(original); parent=self.doc.find(path)
                if add: parent.append(copy.deepcopy(parent[0]))
                else: parent.remove(parent[0])
                self.write()
                with self.assertRaises(ValueError): self.check()
    def test_reopen_cannot_be_a_different_project_or_new_audio_setting(self):
        second=copy.deepcopy(self.doc); second.find('.//instrumenttrack').set('new-audio-setting','1')
        ET.ElementTree(second).write(self.reopened)
        with self.assertRaisesRegex(ValueError,'reopened'): self.check()
    def test_reopened_mixer_change_is_not_ignored(self):
        mixer=ET.SubElement(self.doc.find('song'),'mixer')
        ET.SubElement(mixer,'mixerchannel',num='0',volume='1',muted='0')
        self.write()
        second=copy.deepcopy(self.doc); second.find('song/mixer/mixerchannel').set('volume','0')
        ET.ElementTree(second).write(self.reopened)
        with self.assertRaisesRegex(ValueError,'reopened'): self.check()
    def test_links_outside_root_entities_and_oversize_are_rejected(self):
        self.reopened.unlink(); self.reopened.symlink_to(self.project)
        with self.assertRaises(ValueError): self.check()
        self.reopened.unlink(); self.reopened.write_bytes(b'x'*(2*1024*1024+1))
        with self.assertRaises(ValueError): self.check()
        self.reopened.write_bytes(b'<!DOCTYPE foo [<!ENTITY x "boom">]><lmms-project/>')
        with self.assertRaises(ValueError): self.check()
    def wave(self, name='render.wav', rate=44100, frames=None, level=5000, silence_bar=None):
        frames=frames or round(5*240/116*rate)
        data=array.array('h')
        for i in range(frames):
            # Deliberately quiet padding; content must be present in every actual arrangement bar.
            sample=round(level*math.sin(2*math.pi*220*i/rate)) if i/rate < 4*240/116 else 0
            if silence_bar is not None and silence_bar*240/116 <= i/rate < (silence_bar+1)*240/116: sample=0
            data.extend((sample,sample))
        if sys.byteorder != 'little': data.byteswap()
        path=self.root/name
        with wave.open(str(path),'wb') as stream:
            stream.setnchannels(2); stream.setsampwidth(2); stream.setframerate(rate); stream.writeframes(data.tobytes())
        return path
    def test_wave_all_musical_bars_and_quiet_end_padding(self):
        result=subject.verify_wave(self.wave(),self.root)
        self.assertEqual(len(result['arrangement_bar_rms_pcm16']),4)
        self.assertAlmostEqual(result['duration_seconds'],5*240/116,places=4)
    def test_wave_silence_clipping_wrong_duration_partial_song_and_truncation(self):
        for args in [{'level':0},{'level':32767},{'frames':44100},{'silence_bar':2}]:
            with self.subTest(args=args), self.assertRaises(ValueError): subject.verify_wave(self.wave(**args),self.root)
        path=self.wave(); path.write_bytes(path.read_bytes()[:-8000])
        with self.assertRaises(ValueError): subject.verify_wave(path,self.root)
    def test_nonzero_dc_is_not_musical_audio(self):
        path=self.wave()
        with wave.open(str(path),'rb') as stream: frames=stream.getnframes()
        with wave.open(str(path),'wb') as stream:
            stream.setnchannels(2); stream.setsampwidth(2); stream.setframerate(44100)
            stream.writeframes(b'\x88\x13' * frames * 2)
        with self.assertRaises(ValueError): subject.verify_wave(path,self.root)
    def test_profile_only_known_ui_changes_and_owned_recent_files(self):
        before=self.root/'before.xml'; after=self.root/'after.xml'
        text='<lmms version="1.0.0"><paths workingdir="C:/Users/runner/Documents/BeatQuay/"/><app configured="1"/><ui/><recentfiles/><favoriteitems/></lmms>'
        before.write_text(text); after.write_text(text)
        result=subject.verify_profile(before,after,'C:/Users/runner/Documents/BeatQuay',[])
        self.assertEqual(result['changed_fields'],[])
        doc=ET.fromstring(text); doc.find('ui').set('songeditorzoom','8')
        ET.SubElement(doc.find('recentfiles'),'file',path='C:/owned/Evening Pulse.mmp')
        ET.ElementTree(doc).write(after)
        self.assertTrue(subject.verify_profile(before,after,'C:/Users/runner/Documents/BeatQuay',['C:/owned/Evening Pulse.mmp'])['changed_fields'])
        for mutation in ('foreign_recent','foreign_setting','workingdir'):
            bad=copy.deepcopy(doc)
            if mutation=='foreign_recent': bad.find('recentfiles/file').set('path','C:/foreign.mmp')
            elif mutation=='foreign_setting': bad.find('app').set('unknown','1')
            else: bad.find('paths').set('workingdir','C:/foreign')
            ET.ElementTree(bad).write(after)
            with self.assertRaises(ValueError): subject.verify_profile(before,after,'C:/Users/runner/Documents/BeatQuay',['C:/owned/Evening Pulse.mmp'])

if __name__ == '__main__': unittest.main()
