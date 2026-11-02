"""Explicit pytest plugin recording candidate bytes, collected IDs and every phase."""
import hashlib
import json
from pathlib import Path
import subprocess
import pytest

ROOT = Path(__file__).resolve().parent.parent
selected = {}
phases = {}


def pytest_addoption(parser):
    parser.addoption('--release-ledger')
    parser.addoption('--release-host')


def pytest_collection_finish(session):
    for item in session.items:
        selected[item.nodeid] = {'posix': bool(item.get_closest_marker('posix')),
                                 'gate': bool(item.get_closest_marker('gate'))}


@pytest.hookimpl(optionalhook=True)
def pytest_xdist_node_collection_finished(node, ids):
    for name in ids:
        selected.setdefault(name, {})


def pytest_runtest_logreport(report):
    phases.setdefault(report.nodeid, {})[report.when] = report.outcome


def pytest_sessionfinish(session, exitstatus):
    if hasattr(session.config, 'workerinput'):
        return
    target = session.config.getoption('--release-ledger')
    if not target:
        return
    def git(*args):
        return subprocess.check_output(['git', '-c', 'safe.directory='+ROOT.as_posix(),
                                        '-C', str(ROOT), *args])
    names = git('ls-files', '-z').decode().split('\0')
    files = {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
             for name in sorted(filter(None, names)) if (ROOT/name).is_file()}
    tree_hash = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
    payload = {'host': session.config.getoption('--release-host'),
               'head': git('rev-parse', 'HEAD').decode().strip(),
               'tree_hash': tree_hash, 'files': files, 'selected': selected,
               'phases': phases, 'exitstatus': int(exitstatus)}
    Path(target).write_text(json.dumps(payload, indent=2, sort_keys=True)+'\n', encoding='utf-8')
