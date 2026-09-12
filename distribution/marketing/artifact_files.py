"""Small bounded ZIP reader for the two pinned original artifact classes.
Copyright 2026 Trieflow LLC. MIT. Partial owned extraction is retained on failure.
"""
from pathlib import Path
import stat
import unicodedata
import zipfile

from capture_checks import relative_path,require


def plain(path,directory=False):
    path=Path(path).absolute()
    for entry in reversed((path,*path.parents)):
        info=entry.lstat()
        require(not stat.S_ISLNK(info.st_mode) and not getattr(info,'st_file_attributes',0)&0x400,'Reparse artifact path')
        require(stat.S_ISDIR(info.st_mode) if entry!=path or directory else stat.S_ISREG(info.st_mode),'Unexpected artifact file type')
    return path


def extract(archive,output,maximum,exact_members=None):
    require(type(maximum) is int and maximum>0,'Positive artifact byte bound required')
    archive=plain(archive);output=Path(output).absolute();plain(output.parent,True)
    with zipfile.ZipFile(archive) as incoming:
        entries=incoming.infolist();names=[entry.filename for entry in entries];seen=set()
        require(0<len(entries)<=2048 and sum(entry.file_size for entry in entries)<=maximum,'Expanded artifact exceeds bound')
        for entry in entries:
            relative_path(entry.filename)
            key=unicodedata.normalize('NFC',entry.filename).casefold()
            require(key not in seen,'Duplicate or Windows-aliased artifact path');seen.add(key)
            kind=stat.S_IFMT(entry.external_attr>>16)
            require(not entry.is_dir() and kind in (0,stat.S_IFREG) and entry.flag_bits&1==0,'Artifact member is not an unencrypted regular file')
        if exact_members is not None:require(set(names)==set(exact_members),'Unexpected artifact membership')
        output.mkdir()  # Exclusively ours; do not merge or replace an existing tree.
        for entry in entries:
            target=output/entry.filename;target.parent.mkdir(parents=True,exist_ok=True);plain(target.parent,True)
            copied=0
            with incoming.open(entry) as source,target.open('xb') as destination:
                for block in iter(lambda:source.read(1024*1024),b''):
                    copied+=len(block);require(copied<=entry.file_size,'Artifact member exceeded declared size')
                    destination.write(block)
            require(copied==entry.file_size,'Artifact member length differs')
