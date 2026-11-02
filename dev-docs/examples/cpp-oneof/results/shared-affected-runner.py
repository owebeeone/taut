from pathlib import Path
import hashlib,json,os,subprocess,sys,time
ROOT=Path('D:/projects/limbo/taut-dev/taut');WORK=ROOT.parent
RESULT=ROOT/'dev-docs/examples/cpp-oneof/results'
old=json.loads((ROOT/'dev-docs/EcmaOneOfCheckpoint-Preparation.json').read_text())
protected=list(old['user_owned_parallel_work']['monitored_sources'])
excluded=list(old['excluded_old_python_artifacts']['files'])
repos=[WORK,ROOT,WORK/'taut-shape-py',WORK/'taut-shape-rs',WORK/'taut-shape-ts']
def sha(data):return hashlib.sha256(data).hexdigest()
def snapshot():
 result={'protected':{},'excluded':{},'indices':{},'locks':{},'shared_and_cpp_source':{}}
 for label,names in [('protected',protected),('excluded',excluded)]:
  result[label]={n:sha((ROOT/n).read_bytes()) for n in names}
 for r in repos:
  p=r/'.git/index'
  if p.is_file():result['indices'][str(r)]=sha(p.read_bytes())
  for name in ('Cargo.lock','pnpm-lock.yaml','uv.lock','package-lock.json','pyproject.toml'):
   p=r/name
   if p.is_file():result['locks'][str(p)]=sha(p.read_bytes())
 for p in (WORK/'gwz.conf').rglob('*'):
  if p.is_file():result['locks'][str(p)]=sha(p.read_bytes())
 names=['src/taut/gen/scaffold.py','src/taut/cli.py','src/taut/gen/cpp.py','src/taut/gen/cpp_metadata.py','src/taut/gen/cpp_runtime.py','src/taut/corpus/parity_cpp.py']
 names += ['src/taut/gen/runtime/'+n for n in ('foundation.hpp','foundation.cpp','descriptors.hpp','reports.hpp','validation.hpp')]
 result['shared_and_cpp_source']={n:sha((ROOT/n).read_bytes()) for n in names}
 return result
nodes={
 'test_python_runtime_distribution.py':['test_safe_transitions_shared_users_and_no_partial_writes','test_runtime_preflight_protects_outputs','test_repeated_runtime_same_owner_reuses_and_shared_engine_survives','test_explicit_consumer_requires_owner_then_keeps_engine_after_producer_detaches','test_obstructed_runtime_directory_fails_before_any_output_write','test_linked_runtime_directory_cannot_redirect_writes','test_owned_cleanup_cannot_follow_junction_into_unowned_identical_files'],
 'test_rust_oneof.py':['test_unknown_outputs_refuse_before_writes','test_shared_source_consumers_keep_owner_and_engine','test_modified_owner_mode_change_is_unchanged','test_source_cleanup_rejects_directory_junction_before_any_write','test_equivalent_shared_root_keeps_both_users_and_enabled_engine','test_physical_write_delete_overlap_fails_before_mutation','test_windows_extended_path_spelling_shares_owner_and_schema_identity','test_distinct_windows_namespace_directories_refuse_without_mutation','test_windows_namespace_rejection_is_shared_by_identity_boundaries'],
 'test_java_oneof.py':['test_modified_unknown_files_are_atomic','test_shared_users_modes_equivalent_roots_and_handwritten_survive','test_symlink_and_parent_obstructions_preflight'],
 'test_kotlin_oneof.py':['test_shared_source_users_and_all_mode_transitions','test_unknown_shared_user_cannot_be_silently_discarded','test_windows_namespace_identity_rejected_before_mutation'],
 'test_js_oneof.py':['test_modified_or_handwritten_files_unchanged','test_shared_users_transitions_preserve_engine_until_last_user','test_unavailable_bound_source_owner_is_not_adopted','test_obstructed_or_alias_owner_unchanged','test_windows_junction_and_namespace_ambiguity_refused','test_equivalent_root_reuse_and_engine_preservation'],
 'test_typescript_oneof.py':['test_modified_unknown_outputs_fail_atomically','test_shared_source_users_and_modes','test_windows_ambiguous_namespace_root_is_refused'],
 'test_js_ts_distribution.py':['test_shared_namespace_guard_retains_ads_component_before_path_conversion','test_shared_help_preserves_jvm_and_ecma_methods_defaults_and_artifact_formats'],
 'test_cpp_go_distribution.py':['test_previous_owner_alias_rejected_before_lock_mutation','test_pair_plans_all_targets_before_mutation'],
}
args=[sys.executable,'-m','pytest',*[f'src/tests/{file}::{name}' for file,names in nodes.items() for name in names],'-q','--basetemp','D:/projects/limbo/cpp-go-oneof-scratch/pytest-shared-affected']
before=snapshot();(RESULT/'shared-affected-before.json').write_text(json.dumps(before,indent=2,sort_keys=True)+'\n')
started=time.monotonic();r=subprocess.run(args,cwd=ROOT,capture_output=True,encoding='utf-8');elapsed=time.monotonic()-started
(RESULT/'shared-affected.log').write_text(r.stdout+r.stderr,encoding='utf-8')
after=snapshot();(RESULT/'shared-affected-after.json').write_text(json.dumps(after,indent=2,sort_keys=True)+'\n')
receipt={'command':args,'cwd':str(ROOT),'interpreter':sys.version,'returncode':r.returncode,'elapsed_seconds':elapsed,'preserved':before==after,'scope':'Focused accepted Python/Rust/JVM/ECMA ownership, transitions, namespace, physical overlap; new eight-target previous-owner pre-lock junction rejection; no native target compilation requested','changed_sections':[k for k in before if before[k]!=after[k]],'counts_are_not_additive':True}
(RESULT/'shared-affected-receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print(r.stdout+r.stderr);print(json.dumps(receipt));sys.exit(r.returncode or (0 if before==after else 2))
