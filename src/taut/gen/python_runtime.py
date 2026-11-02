"""Canonical source closure and hash-verified ownership for Python outputs."""
from __future__ import annotations

import hashlib
import json
from contextlib import contextmanager
from pathlib import Path

from ..contracts import (RUNTIME_OWNER, GENERATOR_BUILD, DESCRIPTOR_CONTRACT,
                         CODEC_CONTRACT, require_contract)

BASE_FILES = ("__init__.py", "_runtime_version.py", "contracts.py", "facts.py", "rules.py",
              "descriptors.py", "wire/__init__.py", "wire/cbor.py", "wire/codec.py",
              "wire/jsoncodec.py", "ext.py")


def resolve_mode(runtime, runtime_mode, validation):
    if type(runtime) is not bool or type(validation) is not bool:
        raise TypeError("runtime and validation must be Boolean")
    if runtime_mode is not None and runtime_mode not in ("source", "package"):
        raise ValueError("runtime_mode must be source, package or None (supplied runtime)")
    if runtime and runtime_mode == "package":
        raise ValueError("conflicting runtime options: runtime=True/--with-runtime requests source, not package")
    return runtime_mode or ("source" if runtime else None)


def runtime_binding(bindings, default_root):
    binding = dict((bindings or {}).get("python", {}))
    allowed = {"owner", "module", "source_root", "descriptor_contract", "codec_contract", "capabilities"}
    if set(binding) - allowed:
        raise ValueError(f"unknown Python runtime binding keys {sorted(set(binding) - allowed)}")
    if binding.get("module", "taut") != "taut":
        raise ValueError("Python foundation must bind to one canonical module taut; rebind split owner")
    require_contract(artifact="Python runtime binding", owner=binding.get("owner", RUNTIME_OWNER),
                     descriptor=binding.get("descriptor_contract", DESCRIPTOR_CONTRACT),
                     codec=binding.get("codec_contract", CODEC_CONTRACT),
                     capabilities=binding.get("capabilities", ()))
    return Path(binding.get("source_root", default_root)).resolve()


def _hash(data):
    return hashlib.sha256(data).hexdigest()


def _json(data):
    return (json.dumps(data, indent=2, sort_keys=True) + "\n").encode()


def _is_alias(path):
    import stat
    if path.is_symlink():
        return True
    try:
        return bool(getattr(path.lstat(), "st_file_attributes", 0) &
                    getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))
    except FileNotFoundError:
        return False


def _physical_path(path):
    """Normalize filesystem identity, including Windows drive/UNC namespace spelling.

    Ownership/mutation callers must inspect the original lexical path for aliases
    first; resolving identity is not permission to follow a directory reparse point.
    """
    import os
    lexical = Path(path)
    if os.name == 'nt':
        spelling = str(lexical)
        ordinary = None
        if spelling[:8].lower() == '\\\\?\\unc\\':
            ordinary = Path('\\\\' + spelling[8:])
        elif spelling.startswith('\\\\?\\') and len(spelling) > 6 and spelling[5:7] == ':\\':
            ordinary = Path(spelling[4:])
        if ordinary is not None:
            components = ordinary.parts[1:]
            if ordinary.anchor.startswith('\\\\'):
                components += tuple(ordinary.anchor.strip('\\').split('\\'))
            reserved = {'CON', 'PRN', 'AUX', 'NUL', 'CONIN$', 'CONOUT$'}
            reserved.update(f'{base}{digit}' for base in ('COM', 'LPT') for digit in '123456789\u00b9\u00b2\u00b3')
            for component in components:
                if component in ('.', '..'):
                    continue
                if (component.endswith(('.', ' ')) or component.split('.')[0].upper() in reserved
                        or any(ord(char) < 32 or char in '<>:"|?*' for char in component)):
                    raise ValueError(f'{lexical}: unsupported Windows namespace path component {component!r}; '
                                     'use ordinary filename components without trailing dots/spaces or reserved names')
    resolved = lexical.resolve()
    if os.name == 'nt':
        spelling = str(resolved)
        if spelling[:8].lower() == '\\\\?\\unc\\':
            resolved = Path('\\\\' + spelling[8:])
        elif spelling.startswith('\\\\?\\') and len(spelling) > 6 and spelling[5:7] == ':\\':
            resolved = Path(spelling[4:])
    return resolved


def _read_manifest(path, kind):
    if _is_alias(path) or (path.exists() and not path.is_file()):
        raise ValueError(f"{path}: unsafe ownership metadata path; use a fresh root or explicit migration")
    if not path.exists():
        return {"kind": kind, "owner": RUNTIME_OWNER, "descriptor": 1, "codec": 1,
                "generator": GENERATOR_BUILD, "files": {}, "users": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data["kind"] != kind or not isinstance(data["files"], dict) or not isinstance(data["users"], dict):
            raise ValueError("invalid ownership inventory")
        require_contract(artifact=str(path), owner=data["owner"], descriptor=data["descriptor"], codec=data["codec"])
        if data["generator"] != GENERATOR_BUILD:
            raise ValueError("incompatible generation policy; use a fresh root or explicit user-managed migration")
        for name, digest in data["files"].items():
            target = (path.parent / name).resolve()
            if not target.is_relative_to(path.parent.resolve()) or target == path:
                raise ValueError("ownership path escapes its root")
            if not target.is_file() or _hash(target.read_bytes()) != digest:
                raise ValueError(f"modified/missing generator-owned file {target}")
        return data
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"{path}: unsafe runtime/output ownership: {exc}") from exc


@contextmanager
def output_locks(roots):
    locks = []
    created = []
    try:
        for root in sorted(set(_physical_path(p) for p in roots)):
            if root.exists() and not root.is_dir():
                raise ValueError(f"{root}: output owner must be a directory; use a fresh root or explicit migration")
            missing = []
            ancestor = root
            while not ancestor.exists():
                missing.append(ancestor)
                ancestor = ancestor.parent
            for directory in reversed(missing):
                try:
                    directory.mkdir()
                    created.append(directory)
                except FileExistsError:
                    pass
            # A stable lock at the owner itself works across cwd/TEMP settings.
            # Empty directories created for a failed preflight are removed below.
            lock = root / ".taut-generation.lock"
            try:
                handle = lock.open("xb")
            except FileExistsError as exc:
                raise ValueError(f"generation lock exists: {lock}; another generator is active, or remove a stale lock after inspection") from exc
            locks.append((lock, handle))
        yield
    finally:
        for path, handle in reversed(locks):
            handle.close()
            path.unlink()
        for directory in reversed(created):
            try:
                directory.rmdir()
            except OSError:
                pass  # successful output or a concurrent user now owns its contents


def plan_outputs(directory, texts, *, mode, validation, source_root, consume_source=False):
    """Preflight everything, then return writes/deletions without mutating outputs."""
    directory = directory.resolve()
    manifest = directory / ".taut-python-outputs.json"
    old = _read_manifest(manifest, "python-schema")
    writes = {directory / name: value.encode("utf-8") for name, value in texts.items()}
    deletes = set()
    for path in writes:
        name = path.relative_to(directory).as_posix()
        if path.is_symlink() or (path.exists() and name not in old["files"]):
            raise ValueError(f"unknown/handwritten output {path}; use a fresh directory or explicit migration")
    for name in old["files"]:
        path = directory / name
        if path not in writes:
            deletes.add(path)
    runtime_roots = {source_root}
    if old.get("source_root"):
        runtime_roots.add(Path(old["source_root"]))
    user = str(manifest)
    runtime_source = Path(__file__).resolve().parents[1]
    for root in runtime_roots:
        root = root.resolve()
        owner_path = root / ".taut-runtime.json"
        rt = _read_manifest(owner_path, "python-runtime")
        if root == source_root and mode != "source" and consume_source and not owner_path.exists():
            raise ValueError(f"{owner_path}: explicitly bound source owner is unavailable; generate its source "
                             "runtime first, then generate this consumer, or bind a compatible package owner")
        rt["users"].pop(user, None)
        if root == source_root and mode == "source":
            rt["users"][user] = {"validation": validation}
        # Explicit consumer bindings keep shared source components alive too.
        elif root == source_root and owner_path.exists() and consume_source:
            rt["users"][user] = {"validation": validation, "consumer": True}
        files = list(BASE_FILES) + (["validation.py"] if any(u["validation"] for u in rt["users"].values()) else [])
        desired = {}
        if rt["users"]:
            desired = {"taut/" + rel: (runtime_source / rel).read_bytes() for rel in files}
        runtime_dir = root / "taut"
        if _is_alias(runtime_dir):
            raise ValueError(f"{runtime_dir}: unsafe/obstructed output directory alias; use a fresh root or explicit migration")
        if runtime_dir.exists():
            for path in runtime_dir.rglob("*"):
                if _is_alias(path):
                    raise ValueError(f"{path}: unsafe/obstructed output directory alias; use a fresh root or explicit migration")
                if not path.is_file() or ("__pycache__" in path.parts and path.suffix == ".pyc"):
                    continue
                rel = path.relative_to(root).as_posix()
                if path.is_symlink() or rel not in rt["files"]:
                    raise ValueError(f"unknown/handwritten runtime {path}; use a fresh owner root or explicit migration")
        if desired and (mode == "source" and root == source_root):
            for rel, content in desired.items():
                path = root / rel
                if path.exists() and rel not in rt["files"]:
                    raise ValueError(f"unknown runtime file {path}; refusing adoption")
                writes[path] = content
        elif desired:
            # Consumer mode cannot install/add missing components, even from local source.
            missing = set(desired) - set(rt["files"])
            if missing:
                raise ValueError(f"runtime {root} missing {sorted(missing)}; regenerate source owner with validation support")
            desired = {rel: (root / rel).read_bytes() for rel in desired}
        for rel in set(rt["files"]) - set(desired):
            deletes.add(root / rel)
        if owner_path.exists() or desired:
            rt["files"] = {rel: _hash(data) for rel, data in desired.items()}
            if desired:
                writes[owner_path] = _json(rt)
            else:
                deletes.add(owner_path)
    new = dict(old, files={name: _hash(text.encode("utf-8")) for name, text in texts.items()},
               mode=mode or "supplied", validation=validation,
               source_root=str(source_root) if mode == "source" or consume_source else None)
    writes[manifest] = _json(new)
    return writes, deletes


def apply_outputs(writes, deletes):
    # All ownership checks have completed. Replace individual files atomically.
    import os
    import tempfile
    deletes = set(deletes)
    physical_targets = {}
    for target in set(writes) | deletes:
        path = target.absolute()
        for component in reversed(path.parents):
            linked = _is_alias(component)
            if linked or (component.exists() and not component.is_dir()):
                raise ValueError(f"{component}: unsafe/obstructed output directory; use a fresh root or explicit migration")
        if _is_alias(path) or (path.exists() and not path.is_file()):
            raise ValueError(f"{path}: unsafe output file path; use a fresh root or explicit migration")
        identity = _physical_path(path)
        previous = physical_targets.get(identity)
        if previous is not None or (target in writes and target in deletes):
            raise ValueError(f"conflicting physical output targets {previous or target} and {target}; refusing overlapping write/delete ownership")
        physical_targets[identity] = target
    for path, content in writes.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            stream.write(content)
            temporary = Path(stream.name)
        try:
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
    for path in deletes:
        path.unlink()
