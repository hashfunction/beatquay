"""Recheck capture and original qualification inputs immediately before install/activation."""
import argparse
import json
import os
from pathlib import Path
import capture_checks as checks
from artifact_files import plain
from prepare_capture import verify_local_inputs


def verify(inputs,source,installed=None):
 bound=checks.binding();capture=checks.checkout(checks.BINDING.parents[2],os.environ.get('GITHUB_SHA'))
 verified=verify_local_inputs(inputs,source,bound);e=verified['modules'].evidence
 prepared=e.load(plain(inputs/'capture-inputs.json'))
 for key,value in {'schema_version':1,'purpose':'marketing screenshots only','consumer_acceptance':False,
  'installation_qualification_claimed':False,'capture_source':capture,'capture_run_id':os.environ.get('GITHUB_RUN_ID'),
  'capture_run_attempt':os.environ.get('GITHUB_RUN_ATTEMPT'),'qualified':bound,
  'package_path':str(verified['package']),'package_record_path':str(verified['metadata']/'msix-store-package-record.json'),
  'original_export_receipt':verified['modules'].package.file_record(verified['receipt'])}.items():e.same(prepared.get(key),value,'capture input '+key)
 proof=dict(prepared['current_native_source_delivery']);original=dict(verified['ready']['nativeSourceDelivery'])
 e.utc(proof.pop('verifiedAtUtc'));e.utc(original.pop('verifiedAtUtc'));e.same(proof,original,'retained fresh source readback')
 public=prepared['current_application_source'];e.same(public,verified['ready']['applicationSource'],'retained public application source')
 if installed:verified['modules'].package.verify_installed(installed,verified['record']['payload'],'store')
 return verified

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--inputs',type=Path,required=True);parser.add_argument('--qualified-source',type=Path,required=True)
 parser.add_argument('--installed-root',type=Path);args=parser.parse_args();verify(args.inputs,args.qualified_source,args.installed_root)
