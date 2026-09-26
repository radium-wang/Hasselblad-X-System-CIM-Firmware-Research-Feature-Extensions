#!/usr/bin/env python3
"""Offline candidate-closure audit of an isolated ORIGINAL X2D II ML library bundle.

Never copies or executes firmware. Greedily identifies unique source providers
needed by a mixed DT_NEEDED closure. Symbol closure is NOT ABI/driver approval.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
from elftools.elf.elffile import ELFFile
from audit_symbol_surface import dynamic_symbols, library_exports, providers


def needed(path):
    with path.open('rb') as stream:
        section = ELFFile(stream).get_section_by_name('.dynamic')
        return [t.needed for t in section.iter_tags() if t.entry.d_tag == 'DT_NEEDED']


def version_surface(path):
    """Versioned strong imports + exported names/versions, without loading ELF."""
    with path.open('rb') as stream:
        elf = ELFFile(stream)
        required = {}
        defined = {}
        needs = elf.get_section_by_name('.gnu.version_r')
        if needs:
            for dependency, auxiliaries in needs.iter_versions():
                for version in auxiliaries:
                    required[version['vna_other'] & 0x7fff] = (dependency.name, version.name)
        definitions = elf.get_section_by_name('.gnu.version_d')
        if definitions:
            for version, names in definitions.iter_versions():
                defined[version['vd_ndx'] & 0x7fff] = next(names).name
        indices = elf.get_section_by_name('.gnu.version')
        imports, exports = [], set()
        for index, symbol in enumerate(elf.get_section_by_name('.dynsym').iter_symbols()):
            if not symbol.name:
                continue
            raw = indices.get_symbol(index)['ndx'] if indices else 'VER_NDX_GLOBAL'
            version_index = raw & 0x7fff if isinstance(raw, int) else 0
            if symbol['st_shndx'] == 'SHN_UNDEF':
                if symbol['st_info']['bind'] == 'STB_GLOBAL' and version_index in required:
                    provider, version = required[version_index]
                    imports.append((symbol.name, provider, version))
            elif symbol['st_info']['bind'] in ('STB_GLOBAL', 'STB_WEAK') and \
                    symbol['st_other']['visibility'] in ('STV_DEFAULT', 'STV_PROTECTED'):
                exports.add((symbol.name, defined.get(version_index)))
        return imports, exports


def check_versions(surfaces):
    failures = []
    for consumer, (imports, _) in surfaces.items():
        for symbol, provider, version in imports:
            if provider not in surfaces or (symbol, version) not in surfaces[provider][1]:
                failures.append({'consumer': consumer, 'symbol': symbol,
                                 'provider': provider, 'version': version})
    return failures


def validate_source_libraries(source, names):
    """Accept explicit library basenames only; this option never loads a library."""
    result = set()
    for name in names:
        if not re.fullmatch(r'lib[A-Za-z0-9_+.-]+\.so', name):
            raise ValueError('source library must be a lib*.so basename: ' + name)
        if not (source / 'lib64' / name).is_file():
            raise ValueError('source library is absent: ' + name)
        result.add(name)
    return result


def library_selection(source, target, source_libraries=(), retained_target_libraries=()):
    requested = validate_source_libraries(source, source_libraries)
    retained = validate_source_libraries(target, retained_target_libraries)
    if requested & retained:
        raise ValueError('a library cannot be both donor and retained target: ' +
                         ', '.join(sorted(requested & retained)))
    return requested, retained


def audit(source, target, source_libraries=(), retained_target_libraries=()):
    source_exports = library_exports(source)
    requested, retained = library_selection(source, target, source_libraries,
                                             retained_target_libraries)
    chosen = set(requested)
    history = []
    missing_files = set()
    unresolved = {}
    cache = {}

    def symbols(path):
        if path not in cache:
            cache[path] = dynamic_symbols(path)
        return cache[path]

    for step in range(20):
        nodes = {'dji_ml': source / 'bin/dji_ml'}
        queue = ['dji_ml']
        missing_files = set()
        while queue:
            parent = queue.pop()
            for name in needed(nodes[parent]):
                if name in nodes:
                    continue
                root = source if name in chosen or not (target / 'lib64' / name).is_file() else target
                path = root / 'lib64' / name
                if not path.is_file():
                    missing_files.add(name)
                    continue
                if root == source:
                    chosen.add(name)
                nodes[name] = path
                queue.append(name)
        available = set().union(*(symbols(p)[1] for p in nodes.values()))
        unresolved = {name: sorted(symbols(path)[0] - available)
                      for name, path in nodes.items() if symbols(path)[0] - available}
        additions = set()
        ambiguous = {}
        for symbol in sorted({s for values in unresolved.values() for s in values}):
            options = providers(symbol, source_exports)
            # Only replace an already required SONAME; never silently inject
            # arbitrary global providers into the loader namespace.
            reachable = [name for name in options if name in nodes]
            if len(reachable) == 1:
                if reachable[0] not in chosen and reachable[0] not in retained:
                    additions.add(reachable[0])
            else:
                ambiguous[symbol] = options
        history.append({'round': step, 'add_source_libraries': sorted(additions),
                        'unresolved_symbol_count': len({s for v in unresolved.values() for s in v})})
        if not additions:
            break
        chosen |= additions
    device_paths = {}
    for name, path in nodes.items():
        if path == source / 'bin/dji_ml' or name in chosen:
            found = sorted({s.decode('ascii') for s in re.findall(rb'/dev/[A-Za-z0-9_./-]+', path.read_bytes())})
            if found: device_paths[name] = found
    versions = {name: version_surface(path) for name, path in nodes.items()}
    version_failures = check_versions(versions)
    manifest = []
    for name, path in sorted(nodes.items()):
        donor = path == source / 'bin/dji_ml' or name in chosen
        root = source if donor else target
        manifest.append({'name': name, 'origin': 'X2DII-1.3.16.2' if donor else 'X2D-4.2.0',
                         'path': path.relative_to(root).as_posix(),
                         'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                         'bytes': path.stat().st_size, 'needed': needed(path)})
    return {
        'scope': 'original X2D II 1.3.16.2 dji_ml, isolated user-space dependencies against X2D 4.2.0',
        'method': 'greedy unversioned closure followed by provider-specific symbol-version audit; no execution',
        'requested_source_libraries': sorted(requested),
        'pinned_target_libraries': sorted(retained),
        'unreachable_pinned_target_libraries': sorted(retained - nodes.keys()),
        'unreachable_requested_source_libraries': sorted(requested - nodes.keys()),
        'source_libraries': sorted(chosen & nodes.keys()),
        'source_library_count': len(chosen & nodes.keys()),
        'retained_target_libraries': sorted(n for n in nodes if n != 'dji_ml' and n not in chosen),
        'missing_needed_files': sorted(missing_files), 'unresolved_by_consumer': unresolved,
        'ambiguous_or_unreachable_providers': ambiguous, 'rounds': history,
        'source_device_paths': device_paths,
        'unversioned_symbol_closure': not unresolved and not missing_files,
        'versioned_import_count': sum(len(item[0]) for item in versions.values()),
        'versioned_import_failures': version_failures,
        'versioned_symbol_check_passed': not version_failures,
        'original_file_manifest': manifest,
        'device_execution_approved': False,
        'remaining_gates': ['symbol versions and C++ object layouts', 'private linker namespace and SELinux',
                            'first-generation kernel ioctl and DSP ABI', 'original encrypted model/config compatibility',
                            'duss_bb_channel_create_by_json is a conditional image-storage channel API; target name-based create is not an ABI alias',
                            'DSH receive payload extent: target 0x490 vs donor 0x890; never feed old messages directly to donor receiver',
                            'native frame import without compositor screenshots',
                            'object-result and AF ROI service contract; no LiDAR dependency'],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-system-root', required=True, type=Path)
    parser.add_argument('--target-system-root', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--source-library', action='append', default=[],
                        help='force a reachable original donor library for offline comparison; repeatable')
    parser.add_argument('--retain-target-library', action='append', default=[],
                        help='pin an original target library; report missing imports instead of automatically replacing it')
    args = parser.parse_args()
    try:
        report = audit(args.source_system_root, args.target_system_root, args.source_library,
                       args.retain_target_library)
    except ValueError as error:
        parser.error(str(error))
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('source_library_count', 'source_libraries',
                       'unversioned_symbol_closure', 'versioned_import_count',
                       'versioned_import_failures', 'unreachable_requested_source_libraries',
                       'device_execution_approved')}, indent=2))


if __name__ == '__main__':
    main()
