"""Compile and run host-only fakes; never build or launch the real device entry."""
import argparse
import csv
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cc', default=os.environ.get('CC', 'clang'))
    args = parser.parse_args()
    cc = shutil.which(args.cc)
    if not cc:
        parser.error('a C11 compiler is required; use --cc or CC')
    manifest = json.loads((MODULE / 'source-manifest.json').read_text())
    for record in manifest['files'] + [manifest['fixture']]:
        assert hashlib.sha256((MODULE / record['path']).read_bytes()).hexdigest() == record['sha256'], record['path']
    fixture = MODULE / manifest['fixture']['path']
    with fixture.open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == manifest['fixture']['events'] == 92
    flags = ['-std=c11', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
             '-D_DEFAULT_SOURCE', '-D_POSIX_C_SOURCE=200809L',
             '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
             '-I' + str(MODULE / 'native'),
             '-I' + str(MODULE / 'CodeTests/input-synthesis')]
    sources = [MODULE / 'native/j8_core.c', MODULE / 'native/j8_runtime.c']
    checks = []
    with tempfile.TemporaryDirectory(prefix='joystick8-offline-') as tmp:
        tmp = Path(tmp)
        capture = tmp / 'normalized-events.raw'
        previous = -1
        with capture.open('wb') as stream:
            for row in rows:
                at, kind, code, value = [int(row[n]) for n in ('relative_us', 'type', 'code', 'value')]
                assert at >= previous >= -1
                assert (kind == 0 and code == 0 and value == 0 or
                        kind == 1 and code in (34, 49, 48, 47) and value in (0, 1, 2))
                previous = at
                # Artificial epoch avoids the historical replay reader's zero sentinel.
                sec, usec = divmod(1000000 + at, 1000000)
                stream.write(struct.pack('<qqHHi', sec, usec, kind, code, value))
        for name, test in [('core-runtime', 'test_j8.c'), ('linux-adapter-fakes', 'test_linux.c')]:
            binary = tmp / name
            command = [cc, *flags, *map(str, sources),
                       str(MODULE / 'CodeTests/input-synthesis' / test), '-o', str(binary)]
            subprocess.run(command, check=True, capture_output=True, text=True)
            run = [str(binary)] + ([str(capture)] if test == 'test_j8.c' else [])
            result = subprocess.run(run, check=True, capture_output=True, text=True)
            checks.append(dict(name=name, stdout=result.stdout))
            print(result.stdout, end='')
    report = dict(status='passed', camera_access=False, firmware_inputs_required=False,
                  sanitizer='address,undefined', source_hashes_verified=True,
                  normalized_fixture_events=len(rows), checks=checks,
                  hardware_execution_in_this_run=False)
    output = MODULE / 'outputs'
    output.mkdir(exist_ok=True)
    (output / 'offline-checks.json').write_text(json.dumps(report, indent=2) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
