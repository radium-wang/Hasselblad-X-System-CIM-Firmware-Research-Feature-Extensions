#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (c) 2026 Radium Wang
"""Prepare a bounded, reversible X2D Doom payload locally; no device access."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile

from elftools.elf.elffile import ELFFile
from build_loader import build

ROOT = Path(__file__).resolve().parents[1]
REMOTE = '/tmp/x2d-doom-trial'
STAGE = '/blackbox/.x2d-doom-trial-stage'
IPC = STAGE + '/ram'
CODE = STAGE + '/audio-code'
OWNER = 'x2d-doom-trial-4.2.0-20261007'
GUI_SHA = '16391452abdc69de9e0807e065c0f4ab3f1ccb5fc288f6fc4e6f5cb3bdca12e0'


def sha(raw): return hashlib.sha256(raw).hexdigest()


def scripts(seconds):
    # Independent factory-domain guardian restores the original service if the UI/engine exits.
    restore = f'''#!/system/bin/sh
export PATH=/system/bin:/system/xbin:/sbin
[ ! -L {REMOTE} ] && [ "$(cat {REMOTE}/owner)" = {OWNER} ] || exit 20
mkdir {REMOTE}/restore.lock 2>/dev/null || exit 0
trap 'rmdir {REMOTE}/restore.lock 2>/dev/null' EXIT
touch {REMOTE}/exit.request
[ -d {IPC} ] && touch {IPC}/exit.request
dbus-send --system --print-reply --dest=com.hasselblad.camera /camera org.freedesktop.DBus.Properties.Set string:com.hasselblad.camera string:forward_input_events variant:int32:0 >{REMOTE}/routing-reset.log 2>&1
for kind in gui engine audio; do
 pidfile={REMOTE}/$kind.pid; [ "$kind" = engine ] && pidfile={STAGE}/engine.pid
 p=$(cat "$pidfile" 2>/dev/null)
 case "$p" in ''|*[!0-9]*) continue;; esac
 if [ -r /proc/$p/environ ]; then
  tr '\\000' '\\n' </proc/$p/environ | grep -qx 'X2D_DOOM_TRIAL=1' || continue
  kill -CONT "$p" 2>/dev/null
  kill -TERM "$p" 2>/dev/null
 fi
done
sleep 1
for kind in gui engine audio; do
 pidfile={REMOTE}/$kind.pid; [ "$kind" = engine ] && pidfile={STAGE}/engine.pid
 p=$(cat "$pidfile" 2>/dev/null)
 case "$p" in ''|*[!0-9]*) continue;; esac
 if [ -r /proc/$p/environ ] && tr '\\000' '\\n' </proc/$p/environ | grep -qx 'X2D_DOOM_TRIAL=1'; then kill -KILL "$p" 2>/dev/null; fi
done
if [ -f {REMOTE}/gui.stopped ]; then start camera-gui; rm -f {REMOTE}/gui.stopped; fi
sleep 1
if [ ! -L {STAGE} ] && [ "$(cat {STAGE}/owner 2>/dev/null)" = {OWNER} ]; then
 clean=1
 if grep -q ' {CODE} tmpfs ' /proc/mounts; then umount {CODE} || clean=0; fi
 if grep -q ' {IPC} tmpfs ' /proc/mounts; then umount {IPC} || clean=0; fi
 if [ "$clean" = 1 ]; then rm -rf {STAGE}; else echo X2D_DOOM_RAM_UNMOUNT_FAILED; fi
fi
/system/bin/toybox nohup /system/bin/sh -c 'sleep 1;setprop sys.usb.config none;sleep 1;setprop sys.usb.config rndis,mass_storage,bulk,acm' >/dev/null 2>&1 &
rm -f {REMOTE}/gui.pid {REMOTE}/engine.pid {REMOTE}/audio.pid
echo X2D_DOOM_RESTORED
'''
    watch = f'''#!/system/bin/sh
export PATH=/system/bin:/system/xbin:/sbin
[ "$(cat {REMOTE}/owner)" = {OWNER} ] || exit 30
echo $$ >{REMOTE}/watch.pid
deadline=$(( $(date +%s) + {seconds} ))
while [ "$(date +%s)" -lt "$deadline" ]; do
 {{ [ -e {REMOTE}/exit.request ] || [ -e {IPC}/exit.request ]; }} && break
 for kind in gui engine audio; do
  pidfile={REMOTE}/$kind.pid; [ "$kind" = engine ] && pidfile={STAGE}/engine.pid
 p=$(cat "$pidfile" 2>/dev/null)
  case "$p" in ''|*[!0-9]*) continue;; esac
  kill -0 "$p" 2>/dev/null || {{ sh {REMOTE}/restore.sh; exit; }}
 done
 sleep .2
done
sh {REMOTE}/restore.sh
'''
    run = f'''#!/system/bin/sh
export PATH=/system/bin:/system/xbin:/sbin
[ "$(cat {REMOTE}/owner)" = {OWNER} ] || exit 40
[ ! -e {REMOTE}/exit.request ] && [ ! -e {IPC}/exit.request ] && [ ! -d {REMOTE}/restore.lock ] || exit 42
for pidfile in {REMOTE}/watch.pid {STAGE}/engine.pid {REMOTE}/audio.pid; do
 p=$(cat "$pidfile" 2>/dev/null)
 case "$p" in ''|*[!0-9]*) exit 43;; esac
 kill -0 "$p" 2>/dev/null || exit 44
done
trap 'sh {REMOTE}/restore.sh' EXIT
trap 'exit 143' HUP INT TERM
export X2D_DOOM_TRIAL=1
touch {REMOTE}/gui.stopped
stop camera-gui
n=0; while pidof camera-gui >/dev/null; do sleep 1; n=$((n+1)); [ "$n" -lt 10 ] || exit 41; done
export XDG_RUNTIME_DIR=/tmp
export XDG_CACHE_HOME={REMOTE}/cache
export QT_QPA_FONTDIR=/system/lib64/qt/lib/fonts
export QML_XHR_ALLOW_FILE_READ=1
export QML_XHR_ALLOW_FILE_WRITE=1
mkdir -p "$XDG_CACHE_HOME"
/system/bin/camera-gui -platform wayland-egl --fullscreen </dev/null &
echo $! >{REMOTE}/gui.pid
trap - EXIT
'''
    native = f'''#!/system/bin/sh
export PATH=/system/bin:/system/xbin:/sbin
[ ! -L {STAGE} ] && [ "$(cat {STAGE}/owner)" = {OWNER} ] || exit 50
export X2D_DOOM_TRIAL=1
export X2D_DOOM_IPC={IPC}
export X2D_DOOM_SECONDS={seconds}
export X2D_DOOM_FRAMES=21000
cd {IPC} || exit 51
{STAGE}/engine -iwad {STAGE}/game.wad -warp 1 1 -nomusic -config {IPC}/doom.cfg -extraconfig {IPC}/extra.cfg >{IPC}/engine.log 2>&1 &
p=$!; echo "$p" >{STAGE}/engine.pid
trap 'kill -TERM "$p" 2>/dev/null; wait "$p"; exit 143' HUP INT TERM
wait "$p"
'''
    audio = f'''#!/system/bin/sh
export PATH=/system/bin:/system/xbin:/sbin
[ ! -L {STAGE} ] && [ "$(cat {STAGE}/owner)" = {OWNER} ] || exit 60
export X2D_DOOM_TRIAL=1
export X2D_DOOM_AUDIO_BRIDGE=1
export X2D_DOOM_IPC={IPC}
export LD_PRELOAD={CODE}/libdoom_audio.so
echo $$ >{REMOTE}/audio.pid
exec /system/bin/sleep 2147483647
'''
    return {n: s.encode() for n, s in [('restore.sh', restore), ('watch.sh', watch),
                                      ('run.sh', run), ('native-run.sh', native), ('audio-run.sh', audio)]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--system', type=Path, required=True)
    p.add_argument('--engine', type=Path, required=True)
    p.add_argument('--wad', type=Path, required=True)
    p.add_argument('--audio-bridge', type=Path, required=True)
    p.add_argument('--host-checks', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--seconds', type=int, default=120)
    a = p.parse_args()
    if not 30 <= a.seconds <= 180: p.error('Trial limit must be 30–180 seconds')
    if a.out.resolve().is_relative_to(a.system.resolve()): p.error('Output must be separate from firmware')
    checks = json.loads(a.host_checks.read_text())
    for name in ['DoomPage.qml', 'doomgeneric_x2d_file.c', 'doom_sound.c', 'audio_ring.h']:
        assert checks['sourceSha256'][name] == sha((ROOT/('ui' if name.endswith('.qml') else 'native')/name).read_bytes()), 'Stale host check: ' + name
    assert checks['wadSha256'] == sha(a.wad.read_bytes()), 'Host checks used another WAD'
    for gate in ['fullPressFiresActualPistol', 'fastShutterTapFiresActualPistol',
                 'halfPressDoesNotFire', 'fullReleaseStopsFire', 'exitEndsEngine',
                 'swipeChangesActualViewAngle', 'movementAndSwipeSimultaneously', 'actualWadSoundEffectsPcm']:
        assert checks[gate] is True, gate
    engine = a.engine.read_bytes()
    metadata = json.loads(a.engine.with_name(a.engine.name + '.json').read_text())
    assert sha(engine) == metadata['sha256'] and metadata['static'] is True
    assert sha((ROOT/'native'/'doomgeneric_x2d_file.c').read_bytes()) == metadata['backendSha256']
    assert sha((ROOT/'native'/'doom_sound.c').read_bytes()) == metadata['soundSourceSha256']
    bridge = a.audio_bridge.read_bytes()
    bridge_meta = json.loads(a.audio_bridge.with_name('audio-build.json').read_text())
    assert sha(bridge) == bridge_meta['sha256']
    assert sha((ROOT/'native'/'audio_bridge.c').read_bytes()) == bridge_meta['sourceSha256']
    assert sha((ROOT/'native'/'audio_ring.h').read_bytes()) == bridge_meta['ringHeaderSha256'] == metadata['ringHeaderSha256']
    raw = (a.system/'bin/camera-gui').read_bytes(); assert sha(raw) == GUI_SHA
    elf = ELFFile(io.BytesIO(raw)); syms = list(elf.get_section_by_name('.symtab').iter_symbols())
    unit = next(s for s in syms if s.name.endswith('32_app_qml_mainmenu_MainScreen_qml7qmlDataE'))
    cache = next(s for s in syms if s.name.endswith('32_app_qml_mainmenu_MainScreen_qmlL4unitE'))
    aot = next(s for s in syms if s.name.endswith('32_app_qml_mainmenu_MainScreen_qml17aotBuiltFunctionsE'))
    sec = elf.get_section(unit['st_shndx']); at = unit['st_value'] - sec['sh_addr']
    original = sec.data()[at:at+unit['st_size']]
    candidate = build(original, 'file://' + REMOTE + '/Bootstrap.qml', 'X2dDoomLoader')
    files = {'owner': OWNER.encode(), 'bootstrap.bin': candidate, 'engine': engine,
             'game.wad': a.wad.read_bytes(), 'libdoom_audio.so': bridge, **scripts(a.seconds)}
    for name in ['DoomPage.qml', 'DoomCameraPage.qml', 'Bootstrap.qml']: files[name] = (ROOT/'ui'/name).read_bytes()
    for name in ['restore.sh', 'watch.sh', 'run.sh', 'native-run.sh', 'audio-run.sh']:
        subprocess.run(['sh', '-n'], input=files[name], check=True)
    files['checksums'] = ''.join(sha(v)+'  '+k+'\n' for k,v in sorted(files.items())).encode()
    a.out.mkdir(parents=True, exist_ok=True)
    archive = a.out/'payload.tar.gz'
    with tarfile.open(archive, 'w:gz') as tar:
        for name, data in files.items():
            item = tarfile.TarInfo(name); item.size = len(data); item.mode = 0o700 if name == 'engine' else 0o600
            tar.addfile(item, io.BytesIO(data))
    manifest = {'model': 'X2D 100C', 'firmware': '4.2.0 build 24849', 'guiSha256': GUI_SHA,
        'seconds': a.seconds, 'deviceAccess': False, 'deviceValidated': False,
        'dataVa': unit['st_value'], 'cacheVa': cache['st_value'], 'aotVa': aot['st_value'],
        'unitBytes': len(candidate), 'stockUnitSha256': sha(original), 'unitSha256': sha(candidate),
        'archiveSha256': sha(archive.read_bytes()), 'files': {n: sha(v) for n,v in files.items()},
        'audioDependencies': bridge_meta['dependencies'], 'audio': 'WAD effects, stock speaker service', 'music': False,
        'stockFunctionAndObjectLayoutPreserved': True}
    (a.out/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    (a.out/'stock-unit.bin').write_bytes(original); (a.out/'bootstrap.bin').write_bytes(candidate)
    print(json.dumps({k: manifest[k] for k in ['seconds', 'unitBytes', 'archiveSha256', 'deviceAccess']}))


if __name__ == '__main__': main()
