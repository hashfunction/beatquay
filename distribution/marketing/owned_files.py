"""Exclusive capture trees; verify every sealed byte before deleting any file.
Copyright 2026 Trieflow LLC. MIT.
"""
import argparse
import hashlib
import json
from pathlib import Path
import uuid
from artifact_files import plain
from capture_checks import require

MARKER='.beatsprig-capture-owner.json'
ALLOWED={
 'demo':{'.beatquay-profile-initial.xml','Evening Pulse/Evening Pulse.mmp','Evening Pulse/Evening Pulse Reopened.mmp','Evening Pulse/Evening Pulse.wav'},
 'signing':{'BeatSprig.Marketing.signed.msix','BeatSprig.Marketing.public.cer'},
}

def file(path):
 plain(path);before=path.stat();require(before.st_size<=220_000_000,'Owned file exceeds capture bound')
 digest=hashlib.sha256()
 with path.open('rb') as stream:
  for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
 after=path.stat();require((before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns),'Owned file changed during hashing')
 return {'bytes':after.st_size,'sha256':digest.hexdigest()}

def create(root,kind):
 require(kind in ALLOWED,'Unknown owned capture tree');plain(root.parent,True);root.mkdir()
 marker={'kind':kind,'nonce':uuid.uuid4().hex};(root/MARKER).write_text(json.dumps(marker),encoding='utf-8')
 return {'root':str(root),'kind':kind,'marker':marker,'device':root.stat().st_dev,'inode':root.stat().st_ino}

def seal(record):
 root=plain(Path(record['root']),True);require(record['kind'] in ALLOWED,'Unknown owned capture kind')
 require((root.stat().st_dev,root.stat().st_ino)==(record['device'],record['inode']),'Owned root identity changed')
 plain(root/MARKER);require(json.loads((root/MARKER).read_text())==record['marker'],'Owned capture marker changed')
 entries={};directories=[]
 for path in root.rglob('*'):
  relative=path.relative_to(root).as_posix()
  if path.is_dir():
   plain(path,True);require(record['kind']=='demo' and relative=='Evening Pulse','Untracked capture directory');directories.append(relative)
  else:
   require(relative==MARKER or relative in ALLOWED[record['kind']],'Untracked capture file');entries[relative]=file(path)
 require(len(entries)<=6,'Capture file count exceeds bound')
 return {'files':entries,'directories':sorted(directories)}

def cleanup(record,expected,stopped):
 require(stopped is True,'Retained process termination required before capture cleanup')
 require(seal(record)==expected,'Sealed capture tree changed; all files preserved')
 root=Path(record['root'])
 for relative in expected['files']:(root/relative).unlink()
 for relative in reversed(expected['directories']):(root/relative).rmdir()
 root.rmdir()

def write(path,value):
 with path.open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['create','seal','seal-empty','cleanup'])
 parser.add_argument('--root',type=Path);parser.add_argument('--kind',choices=ALLOWED);parser.add_argument('--record',type=Path,required=True)
 parser.add_argument('--seal',type=Path);parser.add_argument('--stopped',action='store_true');args=parser.parse_args()
 if args.action=='create':write(args.record,create(args.root,args.kind))
 elif args.action in ('seal','seal-empty'):
  value=seal(json.loads(args.record.read_text()))
  if args.action=='seal-empty':require(set(value['files'])=={MARKER} and value['directories']==[],'Unsealed capture outputs preserved')
  write(args.seal,value)
 else:cleanup(json.loads(args.record.read_text()),json.loads(args.seal.read_text()),args.stopped)
