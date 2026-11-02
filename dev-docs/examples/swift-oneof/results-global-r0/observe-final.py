from pathlib import Path
import hashlib,json
r=Path(__file__).resolve().parent
counts=json.loads((r/'final-derived-counts.json').read_text())
paths=sorted((r/'pytest-temp/test_generated_go_is_gofmt_cle0').glob('*.go'))+[r/'pytest-temp/test_go_runtime_and_parity_run0/main.go']
rows={}
for p in paths:
    b=p.read_bytes();rows[p.relative_to(r).as_posix()]={'sha256':hashlib.sha256(b).hexdigest(),'size':len(b),'CRLF':b.count(b'\r\n'),'LF_total':b.count(b'\n'),'bare_LF':b.count(b'\n')-b.count(b'\r\n')}
receipt={'observed_launcher_exit_code':0,'observed_pytest_exit_code':1,'test_runs':{'all16_codec_gate':1,'broad_pytest':1},'additional_test_runs':0,
 'baseline_scratch_byte_observation':rows,'association':'Read-only inspection of retained Windows write_text outputs. Known CRLF failures remain enabled; LF feature regression passed in same broad run. See baseline-source-proof.json for exact unchanged baseline files. No formatter rerun was performed.',
 'raw_source_integrity':{k:counts[k] for k in ('source_total','raw_blob_total','swift_owned_raw_count','raw_before_after_equal','protected_counts')}}
(r/'execution-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(receipt,indent=2))
