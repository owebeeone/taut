from pathlib import Path
root=Path(__file__).resolve().parent
old=Path('D:/projects/limbo/cpp-go-oneof-scratch/global-gate-r0')
ps=(old/'run-gate.ps1').read_text().replace('cpp-go-oneof-scratch','swift-oneof-scratch')
(root/'run-gate.ps1').write_text(ps,encoding='utf-8',newline='\n')
plugin=(old/'collection_receipt.py').read_text()
plugin=plugin.replace("POLICY={f'src/tests/test_oneof.py::test_enum_authoring_metadata_namespace_is_reserved_early[{n}]' for n in ('name','members','options')}", 'POLICY=set()')
plugin=plugin.replace("'test_cpp_go_distribution.py')", "'test_cpp_go_distribution.py','test_swift_oneof.py','test_swift.py','test_swift_distribution.py','test_oneof.py')")
(root/'collection_receipt.py').write_text(plugin,encoding='utf-8',newline='\n')
s=(old/'run-global-gate.py').read_text()
s=s.replace('ONE settled C++/Go r0 global gate','ONE settled all-nine Swift r0 global gate')
s=s.replace('4222822320cbb22e376f8b387a963e86aad10ff2','c02765930f06cfcb19a522843aa54582db514706').replace('bd455ef9174fb13679d0ec6814e43ec1345505fc','a8f37984471654902149d136b7a13a588346b58f')
s=s.replace("POLICY=[f'src/tests/test_oneof.py::test_enum_authoring_metadata_namespace_is_reserved_early[{name}]' for name in ('name','members','options')]",'POLICY=[]')
s=s.replace("PREP['user_owned_parallel_work']['monitored_sources']", "{p:{'sha256':h} for p,h in PREP['protection']['user_five'].items()}")
s=s.replace("PREP['excluded_old_python_artifacts']['files']", "{p:{'sha256':h} for p,h in PREP['protection']['excluded35_hashes'].items()}")
s=s.replace("path.startswith('dev-docs/CppGoOneOfCheckpoint-')", "path in {'dev-docs/SwiftOneOfCheckpoint-ReviewCode-0.md','dev-docs/SwiftOneOfCheckpoint-ReviewState-0.md','dev-docs/SwiftOneOfCheckpoint-Verdict-0.md','dev-docs/SwiftOneOfCheckpoint-Acceptance-0.json'}")
s=s.replace('dev-docs/CppGoOneOfCheckpoint-Preparation.json','dev-docs/SwiftOneOfCheckpoint-Preparation.json')
s=s.replace("'pending user-owned Enum.case; exact unchanged old reservation assertion'", "'no enum-policy exclusions authorized'")
s=s.replace('only8marked duplicate parity +3exact authoring-policy deselections','only8marked duplicate parity deselections; all enum cases enabled')
s=s.replace('exact11deselections','exact8deselections').replace('len(deselected)==11','len(deselected)==8')
s=s.replace('go85_selected','go145_selected').replace("['test_go_oneof.py']==85", "['test_go_oneof.py']==145")
s=s.replace("'go_feature_results':", "'swift116_selected':collection['selected_counts']['test_swift_oneof.py']==116,\n        'swift_feature_results':{name:sum(outcomes[k]==name for k in outcomes if k[0]=='test_swift_oneof') for name in ('passed','failed','skipped')},\n        'go_feature_results':")
s=s.replace("or not result['go145_selected']", "or not result['go145_selected'] or not result['swift116_selected']")
s=s.replace("save('expected-tuple.json',EXPECTED);", "raw_verify(state,'before');\n    save('expected-tuple.json',EXPECTED);")
s=s.replace("save('tuple-after.json',after);", "raw_verify(after_state,'after');\n    save('tuple-after.json',after);")
extra='''
def raw_verify(state,phase):
    rows={}
    pair_names=PREP['owned_allowlist']
    if len(pair_names)!=45 or len(PREP['files'])!=44:raise RuntimeError('Swift inventory count mismatch')
    for name,repo in REPOS.items():
        names=sorted(set(state[name]) | (set(pair_names) if name=='taut' else set()))
        request=''.join(EXPECTED[name]+':'+p+'\\n' for p in names).encode()
        data=subprocess.check_output(['git','-c','safe.directory='+repo.as_posix(),'-C',str(repo),'cat-file','--batch'],input=request)
        pos=0;rows[name]={}
        for p in names:
            end=data.index(b'\\n',pos);header=data[pos:end].split();size=int(header[2]);pos=end+1
            blob=data[pos:pos+size];pos+=size+1
            expected=hashlib.sha256(blob).hexdigest();actual=digest(repo/p)
            if expected!=actual:raise RuntimeError('raw committed blob mismatch: '+name+':'+p)
            if name=='taut' and p in PREP['files'] and actual!=PREP['files'][p]['sha256']:
                raise RuntimeError('Swift frozen Preparation hash mismatch: '+p)
            rows[name][p]={'blob_sha256':expected,'actual_sha256':actual,'matches_blob':True,'swift_owned':name=='taut' and p in pair_names}
    save('raw-source-blob-'+phase+'.json',{'source_tuple':EXPECTED,'files':rows,'counts':{k:len(v) for k,v in rows.items()},'swift_owned_count':sum(r['swift_owned'] for v in rows.values() for r in v.values()),'preparation_self_bound_by_commit':True})

'''
s=s.replace('def main():',extra+'def main():')
(root/'run-global-gate.py').write_text(s,encoding='utf-8',newline='\n')
