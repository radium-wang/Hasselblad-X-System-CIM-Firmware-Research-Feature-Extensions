"""离线展开官方 4.2.0 的 CIL 允许规则；不访问设备、不修改权限。"""
from collections import defaultdict
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / '.research-cache/python'))
from dissect.extfs import ExtFS

INPUTS = [
    ('system.img', '/etc/selinux/plat_sepolicy.cil', 'f9f92bc77e3efcb060320793810166ddf5d226ce2aa5ac509dc35240c235fa26'),
    ('system.img', '/etc/selinux/mapping/28.0.cil', 'd2dd31730abe06f9e9ed740f16e13d76cbf66d2f43413f78af99a66d6b549001'),
    ('vendor.img', '/etc/selinux/plat_pub_versioned.cil', 'eb7eb475ed48f12e1fdb4531e3c16a04574c14576e63cd33cc1118e60996f925'),
    ('vendor.img', '/etc/selinux/vendor_sepolicy.cil', '0c0e92e7aea517d981d8d1728b0612e1aada7e49812d77a5a97e06a98e328c50'),
]


def parse(line):
    tokens = iter(re.findall(r'\(|\)|[^\s()]+', line))

    def value(token):
        if token != '(':
            if token == ')':
                raise ValueError('unexpected close')
            return token
        result = []
        for token in tokens:
            if token == ')':
                return result
            result.append(value(token))
        raise ValueError('unclosed expression')

    result = value(next(tokens))
    if next(tokens, None) is not None:
        raise ValueError('trailing expression')
    return result


def collect_forms():
    forms = []
    for image, path, expected in INPUTS:
        with (ROOT / '.research-cache' / image).open('rb') as handle:
            raw = ExtFS(handle).get(path).open().read()
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError('firmware input mismatch: ' + path)
        text = raw.decode('utf-8')
        # This fixed firmware has no conditionally granted allow rules.
        if re.search(r'^\((?:booleanif|tunableif|typealias)', text, re.M):
            raise ValueError('unsupported conditional or alias')
        for line in text.splitlines():
            if line.startswith(('(type ', '(typeattribute ', '(typeattributeset ', '(allow ')):
                forms.append(parse(line))
    return forms


def resolve(forms, source):
    types = {f[1] for f in forms if f[0] == 'type'}
    attrs = defaultdict(list)
    for form in forms:
        if form[0] == 'typeattribute':
            attrs[form[1]]
        elif form[0] == 'typeattributeset':
            attrs[form[1]].append(form[2])

    @lru_cache(None)
    def expand(symbol):
        if symbol in types:
            return frozenset([symbol])
        if symbol not in attrs:
            raise ValueError('unknown type or attribute: ' + symbol)
        return frozenset().union(*(evaluate(x) for x in attrs[symbol]))

    def evaluate(expression):
        if isinstance(expression, str):
            return expand(expression)
        if not expression:
            return frozenset()
        operator = expression[0]
        if operator == 'not':
            assert len(expression) == 2
            return frozenset(types) - evaluate(expression[1])
        if operator == 'and':
            return frozenset.intersection(*(evaluate(v) for v in expression[1:]))
        if operator == 'or':
            return frozenset().union(*(evaluate(v) for v in expression[1:]))
        if operator == 'xor':
            assert len(expression) == 3
            return evaluate(expression[1]) ^ evaluate(expression[2])
        if operator == 'all':
            assert len(expression) == 1
            return frozenset(types)
        return frozenset().union(*(evaluate(v) for v in expression))

    assert source in types
    rights = defaultdict(set)
    matched = []
    for form in forms:
        if form[0] != 'allow' or source not in expand(form[1]):
            continue
        assert len(form) == 4 and len(form[3]) == 2
        class_name, permissions = form[3]
        assert isinstance(class_name, str) and isinstance(permissions, list)
        assert all(isinstance(p, str) for p in permissions)
        targets = {source} if form[2] == 'self' else expand(form[2])
        for target in targets:
            rights[(target, class_name)].update(permissions)
        matched.append(form)
    return rights, matched


def main():
    forms = collect_forms()
    rights, matched = resolve(forms, 'hbl_camera_service')
    examined = [
        'hbl_camera_service_tmpfs', 'shell_data_file', 'system_data_file',
        'vendor_data_file', 'nativetest_data_file', 'cache_file',
        'system_file', 'hbl_camera_service_exec',
    ]
    executable = sorted(t for (t, cls), perms in rights.items()
                        if cls == 'file' and {'execute', 'execute_no_trans'} <= perms)
    overlap = [t for t in executable if {'write', 'create'} & rights[(t, 'file')]]
    controls = [{'target': t, 'class': cls, 'permissions': sorted(perms)}
                for (t, cls), perms in sorted(rights.items())
                if cls == 'security' or (cls == 'process' and
                    {'dyntransition', 'setexec', 'setcurrent', 'transition'} & perms)]
    relabel = [{'target': t, 'class': cls, 'permissions': sorted(perms)}
               for (t, cls), perms in sorted(rights.items())
               if {'relabelto', 'relabelfrom'} & perms]
    report = {
        'firmware': '4.2.0', 'source': 'official-firmware-static', 'deviceAccesses': 0,
        'inputHashes': {image + ':' + path: digest for image, path, digest in INPUTS},
        'domain': 'hbl_camera_service', 'matchingAllowRules': len(matched),
        'examined': {t: {'file': sorted(rights[(t, 'file')]),
                         'dir': sorted(rights[(t, 'dir')])} for t in examined},
        'executeWithoutDomainTransition': executable,
        'writeOrCreateAndExecuteTypes': overlap,
        'securityAndTransitionControls': controls, 'relabelPermissions': relabel,
        'limitations': [
            'Only fixed-image unconditional allow rules; not a live kernel policy dump.',
            'A matching allow does not override DAC, mount options, labels or constraints.',
            'No device commands, policy changes, relabeling or candidate launch.',
        ],
    }
    out = ROOT / 'x2d/outputs/4.2.0/ui-load-permissions.json'
    out.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
