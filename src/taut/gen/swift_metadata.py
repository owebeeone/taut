"""Native Swift value metadata and typed captureless adapters."""
from __future__ import annotations
import hashlib
import re
from . import swift
from .swift_runtime import OWNER, CAPABILITIES, module_name
from .go_metadata import fingerprint  # one portable normalized codec-fact algorithm
from ..facts import Scalar, EnumRef, MsgRef, ListOf, MapOf, MISSING_OK
from ..ir.export import schema_json


def q(value):
    # Encode characters once. Replacing JSON escape substrings would corrupt
    # literal backslash-b/backslash-u text in an explicitly supplied identity.
    escaped = {'"': '\\"', '\\': '\\\\', '\n': '\\n', '\r': '\\r', '\t': '\\t'}
    result = []
    for char in value:
        code = ord(char)
        if 0xD800 <= code <= 0xDFFF:
            raise ValueError('Swift metadata strings require Unicode scalar values')
        result.append(escaped.get(char, '\\u{' + format(code, 'x') + '}'
                                  if code < 32 or code in (127, 0x2028, 0x2029) else char))
    return '"' + ''.join(result) + '"'


def dictionary(values):
    return '[' + (', '.join(q(k) + ': ' + v for k, v in values.items()) if values else ':') + ']'


def literal(value):
    if value is None: return '.null'
    if type(value) is bool: return '.bool(' + str(value).lower() + ')'
    if type(value) is int: return '.int(' + str(value) + ')'
    if type(value) is float: return '.float(' + repr(value) + ')'
    if type(value) is str: return '.string(' + q(value) + ')'
    if type(value) is bytes: return '.bytes([' + ', '.join(map(str, value)) + '])'
    if hasattr(value, 'items'): return '.object(' + dictionary({k: literal(v) for k, v in value.items()}) + ')'
    if isinstance(value, (tuple, list)): return '.array([' + ', '.join(map(literal, value)) + '])'
    raise TypeError(value)


def facts(value):
    return dictionary({k: literal(v) for k, v in value.items()})


def preflight(schema, validation, external, runtime_module):
    from ..ir.validate import validate
    errors = validate(schema, targets=('swift',))
    declared = set(schema.messages) | set(schema.enums)
    if external.keys() - declared: errors.append(f'unknown Swift external types {sorted(external.keys()-declared)}')
    reserved = {runtime_module}
    if not runtime_module and 'Foundation' in declared:
        errors.append('Foundation: Swift flat supplied declaration hides the Foundation module used by canonical helpers; '
                      'bind an explicit imported runtime module (for example TautFoundation) in source/package/supplied mode')
    if not runtime_module:
        # Legacy supplied mode compiles the canonical foundation once in the
        # application module, so these are actual same-module declarations.
        reserved.update('FoundationEvidence MetadataValue TypeDescriptor EnumDescriptor FieldDescriptor OneOfDescriptor ConstraintDescriptor MessageDescriptor SchemaDescriptor RecordTraversal MessageBinding PathSegment ReferenceIdentity DescriptorLink foundationOwner foundationBuild descriptorContract codecContract oneOfRule foundationCapabilities requireFoundation confirmFoundation effectiveFacts requireMessageDescriptor requireEnumDescriptor requireMessageBinding'.split())
        if validation:
            reserved.update('ValidationIssue DeferredCheck ValidationReport ValidationWalk validateRecord isRecordValid'.split())
    for name in declared:
        local_collision = re.fullmatch(r'wire_(?:value|index|visitor|path|item|child|key|descriptor|evidence)[0-9]*', name)
        if not swift.is_identifier(name) or name in swift._SWIFT_KEYWORDS or name in reserved or name.startswith('TautSchema_') or local_collision:
            errors.append(f'{name}: Swift generated/runtime type collision or invalid identifier')
    for msg in schema.messages.values():
        reserved_fields = {'descriptor', 'schemaDescriptor', 'tautBinding'} | ({'validate', 'isValid'} if validation else set())
        if not runtime_module and validation:
            reserved_fields.update({'validateRecord', 'isRecordValid'})
        for field in msg.fields:
            if (not swift.is_identifier(field.name) or field.name in reserved_fields or (validation and field.name == runtime_module)
                or re.fullmatch(r'TautSchema_[0-9a-f]{16}', field.name)):
                errors.append(f'{msg.name}.{field.name}: Swift field/descriptor/method collision or invalid identifier')
    for enumeration in schema.enums.values():
        if not enumeration.members:
            errors.append(f'{enumeration.name}: Swift raw-value enums require a nonempty member inventory')
        for name in enumeration.members:
            members_reserved = {'descriptor', 'schemaDescriptor', 'CborError'}
            if not swift.is_identifier(name) or name in members_reserved or re.fullmatch(r'TautSchema_[0-9a-f]{16}', name):
                errors.append(f'{enumeration.name}.{name}: Swift enum member collision or invalid identifier')
    def refs(t):
        if isinstance(t, (MsgRef, EnumRef)): return {t.name}
        if isinstance(t, ListOf): return refs(t.elem)
        if isinstance(t, MapOf): return refs(t.key) | refs(t.value)
        return set()
    required = {'module', 'type', 'owner', 'descriptor_contract', 'codec_contract', 'capabilities'}
    for name, binding in external.items():
        try:
            good = (isinstance(binding, dict) and set(binding) == required and binding['type'] == name
                    and binding['owner'] == OWNER and type(binding['descriptor_contract']) is int
                    and binding['descriptor_contract'] == 1 and type(binding['codec_contract']) is int
                    and binding['codec_contract'] == 1 and isinstance(binding['capabilities'], (tuple, list, set))
                    and set(binding['capabilities']) == CAPABILITIES)
            if binding['module']: module_name(binding['module'])
            elif not isinstance(binding['module'], str): good = False
        except (KeyError, ValueError, TypeError): good = False
        if not good:
            errors.append(f'{name}: Swift external type requires module, type={name}, owner={OWNER}, descriptor=1 codec=1 capabilities={sorted(CAPABILITIES)}')
        elif binding['module'] in declared or binding['module'] == runtime_module:
            if binding['module']:
                errors.append(f'{name}: Swift child module collides with a schema type or foundation module')
        if good and binding['module'] and not runtime_module:
            errors.append(f'{name}: imported Swift child modules require an explicit shared foundation module binding')
        if name in schema.messages:
            needed = set().union(*(refs(f.type) for f in schema.messages[name].fields))
            if needed - external.keys(): errors.append(f'{name}: bind full Swift dependency graph {sorted(needed-external.keys())}')
    if errors: raise ValueError('; '.join(errors))


def emit_types(schema, *, forward_compat=False, validation=False, external_types=None,
               identity=None, runtime_module=''):
    if type(validation) is not bool: raise TypeError('Swift validation option must be Boolean')
    external = dict(external_types or {})
    if runtime_module: module_name(runtime_module)
    elif not isinstance(runtime_module, str): raise ValueError('Swift runtime_module must be a string')
    preflight(schema, validation, external, runtime_module)
    doc = schema_json(schema)
    identity = identity or 'schema_' + fingerprint(doc)[:16]
    holder = 'TautSchema_' + hashlib.sha256(identity.encode()).hexdigest()[:16]
    r = runtime_module + '.' if runtime_module else ''
    mn = {n: holder + '.message' + str(i) for i, n in enumerate(schema.messages)}
    en = {n: holder + '.enum' + str(i) for i, n in enumerate(schema.enums)}
    reference_types = swift.reference_messages(schema)
    def message_fingerprint(md):
        form = 'class' if md['name'] in reference_types else 'struct'
        return hashlib.sha256((fingerprint(md, forward_compat=forward_compat) + ':swift_native=' + form).encode()).hexdigest()
    out = ['// GENERATED Swift native codec + mandatory descriptor ABI 1; generator=swift-oneof-reference.1',
           '// taut-foundation-module: ' + runtime_module]
    if runtime_module: out += ['import ' + runtime_module]
    out += ['import ' + m for m in sorted({b['module'] for b in external.values() if b['module']})]
    out += ['']
    # Keep the established native codec projection, qualifying runtime types so
    # every schema's codec resolves to the same actual imported nominal owner.
    codec = []
    for e in schema.enums.values():
        if e.name not in external: codec += swift._emit_enum(e.name, e.members) + ['']
    for m in schema.messages.values():
        if m.name not in external: codec += swift._emit_message(m, schema, forward_compat) + ['']
    codec_text = '\n'.join(codec)
    # The imported public codec names keep their established spelling. Preflight
    # reserves real native collisions; importing resolves them to the one owner.
    out += [codec_text]
    for name, binding in external.items():
        if binding['module']:
            out += ['public typealias ' + name + ' = ' + binding['module'] + '.' + name]
    def external_type(name):
        module = external[name]['module']
        return (module + '.' if module else '') + name
    for name in schema.enums:
        if name not in external:
            out += ['public extension ' + name + ' {', '    static let descriptor: ' + r + 'EnumDescriptor = {',
                    '        _ = ' + holder + '.guardOwner', '        return ' + en[name], '    }()',
                    '    static var schemaDescriptor: ' + r + 'SchemaDescriptor { ' + holder + '.schema }', '}']
    for name, msg in schema.messages.items():
        if name in external: continue
        out += ['public extension ' + name + ' {', '    static let descriptor: ' + r + 'MessageDescriptor = {',
                '        _ = ' + holder + '.guardOwner', '        let wire_descriptor = ' + mn[name],
                '        wire_descriptor.checkLinks()', '        return wire_descriptor', '    }()',
                '    static var schemaDescriptor: ' + r + 'SchemaDescriptor { ' + holder + '.schema }',
                '    static let tautBinding: ' + r + 'MessageBinding<' + name + '> = ' + holder + '.binding' + str(list(schema.messages).index(name))]
        if validation:
            out += ['    func validate(recursive: Bool = true) -> ' + r + 'ValidationReport {',
                    '        ' + r + 'validateRecord(self, Self.tautBinding, recursive: recursive)', '    }',
                    '    func isValid(recursive: Bool = true) -> Bool {',
                    '        ' + r + 'isRecordValid(self, Self.tautBinding, recursive: recursive)', '    }']
        out += ['}']
    out += ['private enum ' + holder + ' {', '    static let guardOwner: () = {',
            '        let wire_evidence: ' + r + 'FoundationEvidence = ' + r + 'requireFoundation(' + q(identity) + ', ' + q(OWNER) + ', 1, 1, ["codec.v1", "descriptors.v1", "oneof.v1"])',
            '        precondition(wire_evidence.owner == "taut.swift.foundation" && wire_evidence.descriptor == 1 && wire_evidence.codec == 1 && Set(["codec.v1", "descriptors.v1", "oneof.v1"]).isSubset(of: wire_evidence.capabilities) && ' + r + 'foundationOwner == wire_evidence.owner && ' + r + 'descriptorContract == 1 && ' + r + 'codecContract == 1 && Set(["codec.v1", "descriptors.v1", "oneof.v1"]).isSubset(of: ' + r + 'foundationCapabilities()), "incompatible actual selected Swift foundation; regenerate/rebind")',
            '        ' + r + 'confirmFoundation(wire_evidence, ' + r + 'foundationOwner, ' + r + 'descriptorContract, ' + r + 'codecContract, ' + r + 'foundationCapabilities())']
    # A child's message fingerprint names enum references; the parent's complete
    # imported graph must also verify the actual enum inventories, even if no
    # local field names that enum directly. Do this before publishing any root.
    for name, binding in sorted(external.items()):
        if name in schema.messages:
            expected = message_fingerprint(next(m for m in doc['messages'] if m['name'] == name))
            require = 'requireMessageDescriptor'
        else:
            expected = fingerprint(next(e for e in doc['enums'] if e['name'] == name))
            require = 'requireEnumDescriptor'
        out += ['        _ = ' + r + require + '(' + external_type(name) + '.descriptor, ' + q(expected) + ')']
    out += ['    }()']
    for e, ed in zip(schema.enums.values(), doc['enums']):
        if e.name in external:
            expr = r + 'requireEnumDescriptor(' + external_type(e.name) + '.descriptor, ' + q(fingerprint(ed)) + ')'
        else:
            args = [q(e.name), q(identity + '.' + e.name), dictionary({n: str(v) for n, v in e.members.items()}), facts(e.options), facts(ed['member_options']), q(fingerprint(ed))]
            expr = r + 'EnumDescriptor(' + ', '.join(args) + ')'
        out += ['    static let ' + en[e.name].split('.')[-1] + ': ' + r + 'EnumDescriptor = ' + expr]
    def td(t):
        if isinstance(t, Scalar): return '.' + t.kind
        if isinstance(t, MsgRef): return '.message(' + q(t.name) + ', { ' + mn[t.name] + ' })'
        if isinstance(t, EnumRef): return '.enumeration(' + q(t.name) + ', { ' + en[t.name] + ' })'
        if isinstance(t, ListOf): return '.list(' + td(t.elem) + ')'
        if isinstance(t, MapOf): return '.map(' + td(t.key) + ', ' + td(t.value) + ')'
        raise TypeError(t)
    for m, md in zip(schema.messages.values(), doc['messages']):
        if m.name in external:
            expr = r + 'requireMessageDescriptor(' + external_type(m.name) + '.descriptor, ' + q(message_fingerprint(md)) + ')'
        else:
            fields = []
            for f in sorted(m.fields, key=lambda f: f.tag):
                presence = 'missing_ok' if f.optional == MISSING_OK else 'nullable' if f.optional else 'required'
                args = [q(f.name), q('' if f.virtual else swift._id(f.name)), str(f.tag), td(f.type), q(presence), str(f.transient).lower(), str(f.virtual).lower(), facts(f.options)]
                fields.append(r + 'FieldDescriptor(' + ', '.join(args) + ')')
            groups, constraints = [], []
            for ctrl in sorted(m.fields, key=lambda f: f.tag):
                if not ctrl.oneof: continue
                group = ctrl.oneof
                members = {n: '' for n in schema.enums[group.enum].members}
                for f in m.fields:
                    for case in f.cases:
                        if case.controlling_field == ctrl.name: members[case.member] = f.name
                groups.append(r + 'OneOfDescriptor(' + ', '.join([q(ctrl.name), en[group.enum], str(group.virtual).lower(), str(group.exhaustive).lower(), dictionary({n: q(v) for n, v in members.items()})]) + ')')
                constraints.append(r + 'ConstraintDescriptor("taut.oneof.v1", ' + facts({'controlling_field': ctrl.name}) + ')')
            array = lambda values: '[' + ', '.join(values) + ']'
            args = [q(m.name), q(identity + '.' + m.name), array(fields), array(groups), array(constraints), array(map(str, m.reserved_tags)), array(map(q, m.reserved_names)), 'nil' if m.next_id is None else str(m.next_id), facts(m.options), facts(md['effective']), q(message_fingerprint(md)), q('class' if m.name in reference_types else 'struct'), m.name + '.self']
            expr = r + 'MessageDescriptor(' + ', '.join(args) + ')'
        out += ['    static let ' + mn[m.name].split('.')[-1] + ': ' + r + 'MessageDescriptor = ' + expr]
    def walk(t, expr, path, depth=0):
        if isinstance(t, MsgRef):
            binding = (r + 'requireMessageBinding(' + external_type(t.name) + '.tautBinding, ' + q(message_fingerprint(next(m for m in doc['messages'] if m['name'] == t.name))) + ')') if t.name in external else t.name + '.tautBinding'
            return ['if !wire_visitor.record(' + expr + ', ' + binding + ', ' + path + ') { return false }']
        if isinstance(t, ListOf):
            inner = walk(t.elem, 'wire_child' + str(depth), 'wire_path' + str(depth), depth + 1)
            if not inner: return []
            return ['for (wire_index' + str(depth) + ', wire_child' + str(depth) + ') in ' + expr + '.enumerated() {', '    let wire_path' + str(depth) + ' = ' + path + ' + [' + r + 'PathSegment.forIndex(wire_index' + str(depth) + ')]', *['    ' + line for line in inner], '}']
        if isinstance(t, MapOf):
            key, value, subpath = ('wire_key' + str(depth), 'wire_child' + str(depth), 'wire_path' + str(depth))
            inner = walk(t.value, value, subpath, depth + 1)
            if not inner: return []
            encode = lambda expression: r + 'encode(' + r + {'int': 'Cbor.int', 'str': 'Cbor.text', 'bool': 'Cbor.bool'}[t.key.kind] + '(' + expression + '))'
            return ['for ' + key + ' in ' + expr + '.keys.sorted(by: { ' + encode('$0') + '.lexicographicallyPrecedes(' + encode('$1') + ') }) {', '    let ' + value + ' = ' + expr + '[' + key + ']!', '    let ' + subpath + ' = ' + path + ' + [' + r + 'PathSegment.forKey(' + q(t.key.kind) + ', ' + encode(key) + ')]', *['    ' + line for line in inner], '}']
        return []  # primitives and native enums are already statically typed
    for mi, m in enumerate(schema.messages.values()):
        if m.name in external: continue
        fields = sorted(m.fields, key=lambda f: f.tag)
        present = ['{ wire_value, wire_index in', 'switch wire_index {']
        reads = ['{ wire_value, wire_index in', 'switch wire_index {']
        enums = ['{ wire_value, wire_index in', 'switch wire_index {']
        walks = ['{ wire_value, wire_index, wire_visitor, wire_path in', 'switch wire_index {']
        for i, f in enumerate(fields):
            expr = 'wire_value.' + swift._id(f.name)
            present += [f'case {i}: return ' + ('false' if f.virtual else expr + ' != nil' if f.optional else 'true')]
            if f.virtual: continue
            if isinstance(f.type, EnumRef): enums += [f'case {i}: return ' + expr + ('?.rawValue' if f.optional else '.rawValue')]
            if isinstance(f.type, (Scalar, EnumRef)):
                kind = 'int' if isinstance(f.type, EnumRef) else {'str': 'string'}.get(f.type.kind, f.type.kind)
                native = 'wire_item.rawValue' if isinstance(f.type, EnumRef) else 'wire_item'
                val = '.' + kind + '(' + native + ')'
                reads += [f'case {i}: return ' + (expr + '.map { wire_item in ' + val + ' } ?? .null' if f.optional else val.replace('wire_item', expr))]
            inner = walk(f.type, 'wire_child' if f.optional else expr, 'wire_path')
            if inner:
                walks += [f'case {i}:']
                if f.optional: walks += ['if let wire_child = ' + expr + ' {', *['    ' + line for line in inner], '}']
                else: walks += inner
                walks += ['return true']
        present += ['default: return false', '}', '}']
        enums += ['default: return nil', '}', '}']
        reads += ['default: preconditionFailure("Swift primitive read requires stored primitive/enum field")', '}', '}']
        walks += ['default: return true', '}', '}']
        descriptor = ('reference: ' if m.name in swift.reference_messages(schema) else '') + m.name + '.descriptor'
        args = [descriptor, '\n'.join(present), '\n'.join(enums), '\n'.join(reads), '\n'.join(walks)]
        out += ['    static let binding' + str(mi) + ': ' + r + 'MessageBinding<' + m.name + '> = ' + r + 'MessageBinding(' + ',\n'.join(args).replace('\n', '\n    ') + ')']
    out += ['    static let schema: ' + r + 'SchemaDescriptor = {', '        _ = guardOwner', '        return ' + r + 'SchemaDescriptor(' + ', '.join([str(doc['version']), q(identity), dictionary(mn), dictionary(en), facts(schema.options), facts(doc['effective'])]) + ')', '    }()', '}']
    return '\n'.join(out) + '\n'
