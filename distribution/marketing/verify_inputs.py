"""Original qualification evidence remains distinct from a later capture run.
Copyright 2026 Trieflow LLC. MIT.
"""
import hashlib
import os
from pathlib import Path


def verify_original_lifecycles(root,records,source,bound,original,evidence):
    # This is the qualified source's independent whole-record/file/oracle verifier.
    # The original exported WAV was deleted by its owned lifecycle; its complete
    # typed oracle is verified here, never described as rereading deleted audio.
    actual=evidence.verify_lifecycles(root,records,source,bound['source_commit'],
                                     bound['workflow_run_id'],bound['workflow_run_attempt'])
    evidence.same(actual,original,'original complete exported installed lifecycles')
    return actual


def verify_original_packages(source,root,store_path,ready,bound,package,evidence):
    source=Path(source);root=Path(root);records={};originals={};tools={}
    inputs=evidence.load(root/'package-input.json')
    sources=package.source_inputs(source,source/'data/branding/beatquay-256.png')
    for mode,prefix in [('qualification','msix'),('store','msix-store')]:
        name=prefix+'-package-record.json';record=evidence.load(root/name)
        for key,value in dict(schemaVersion=1,sourceCommit=bound['source_commit'],identityMode=mode,
            identity=package.identity_for(mode),qualificationIdentityOnly=mode=='qualification',storeIdentityStaged=mode=='store',
            licenseClearanceClaimed=False,correspondingSourceComplete=False,publicRelease=False,signed=False,
            installationQualificationPassed=False).items():evidence.same(record.get(key),value,'original package '+key)
        package.validate_run_binding(record,bound['workflow_run_id'],bound['workflow_run_attempt'])
        evidence.same(record['sourceInputs'],sources,'all exact qualified source/helper/notice inputs')
        evidence.same(record['inputInventory'],package.file_record(root/'package-input.json'),'original native inventory bytes')
        for key in ('sourceCommit','workflowRunId','workflowRunAttempt','sourceInputs','evidenceInputs','runtime','peImports','buildProvenance'):
            evidence.same(record.get(key),inputs.get(key),'original input join '+key)
        evidence.same(record['releaseInput'],inputs['files'],'original release input inventory')
        evidence.same(record['releaseInput'],package._inventory_rows(root/'stage-inventory.json'),'retained stage byte inventory')
        for relative,value in record['evidenceInputs'].items():
            package._checked_path(relative)
            if relative.startswith('notices/') and not os.path.lexists(root/relative):
                # The original metadata upload omits some notice extensions.
                # Every notice was also copied into the qualified package.
                # Join BOTH records here; verify_msix below reads and hashes
                # the complete original Store payload before this can succeed.
                payload='licenses/dependencies/'+relative[len('notices/'):]
                evidence.same(record['payload'].get(payload),value,'original packaged notice '+relative)
                evidence.same(ready['packageRecord']['payload'].get(payload),value,'original Store notice '+relative)
            else:
                evidence.same(package.file_record(root/relative),value,'retained native evidence '+relative)
        for relative,value in record['releaseInput'].items():
            evidence.same(record['payload'].get(relative),value,'unchanged qualified release payload '+relative)
        manifest=package.create_manifest(mode)
        evidence.same(record['payload'].get('AppxManifest.xml'),dict(bytes=len(manifest),sha256=hashlib.sha256(manifest).hexdigest()),'fixed current manifest bytes')
        evidence.same(record.get('unpackedVerification'),dict(verifiedPayloadFiles=len(record['payload'])),'exact original SDK unpack count')
        make=record['makeAppx']
        evidence.same(package._tool_record(make['path'],make['sdkVersion']),make,'same original SDK pack/unpack tool bytes')
        sign=evidence.load(root/(prefix+'-install/installation-qualification.json'))['signtool']
        sign_path=Path(sign['path'])
        if sign_path.name.casefold()!='signtool.exe' or not os.path.samefile(sign_path.parent,Path(make['path']).parent):
            raise ValueError('SignTool is not the original exact SDK sibling')
        evidence.same(sign['sdk_version'],'10.0.26100.0','original signing SDK version')
        evidence.same(package.file_record(sign_path),{key:sign[key] for key in ('bytes','sha256')},'same original SignTool bytes')
        records[mode]=record;tools[mode]=dict(makeAppx=make,signTool=sign)
        originals[name]=package.file_record(root/name)
        # Private input copies and the first unsigned package were intentionally
        # not uploaded. Their original export bindings must join the retained
        # exact metadata/container receipts; do not claim these files were reread.
        originals['private-'+mode+'-record']=originals[name]
        originals['unsigned-'+mode]=record['containerVerification']['package']
    evidence.same(ready['packageRecord'],records['store'],'original exported whole Store record')
    evidence.same(ready['originalPackageInputs'],originals,'all original export package input bindings')
    evidence.same(ready['originalSdkTools'],tools,'all original export SDK bindings')
    evidence.same(package.verify_msix(store_path,records['store']['payload'],'store'),records['store']['containerVerification'],'exact existing unsigned Store container')
    return records
