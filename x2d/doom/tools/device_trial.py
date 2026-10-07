#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (c) 2026 Radium Wang
"""Bounded X2D 4.2.0 RAM Doom trial; default is a plan with no USB access."""
import argparse, json, re, shutil, struct, subprocess, tarfile, time
from pathlib import Path
from prepare_trial import REMOTE, STAGE, IPC, CODE, OWNER, GUI_SHA, sha
RC_SHA='1d6a8f9e41e269be38b3fb9ba53f4c47d18007f413c90893fdfa9d7542d1f688'
SERVICE_SHA='fbcf828f73bca13f0c8b95e7dd0b95ac483ae36954ec06179098c8a1a65f9f82'
USB='rndis,mass_storage,bulk,acm'

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['launch','status','restore']);p.add_argument('--apply',action='store_true')
    p.add_argument('--payload',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--adb',type=Path,default=Path(shutil.which('adb') or 'adb'));a=p.parse_args()
    package=a.payload.resolve();meta=json.loads((package/'manifest.json').read_text())
    assert meta['guiSha256']==GUI_SHA and 30<=meta['seconds']<=180
    assert sha((package/'payload.tar.gz').read_bytes())==meta['archiveSha256']
    assert sha((package/'bootstrap.bin').read_bytes())==meta['unitSha256']
    if not a.apply:
        print(json.dumps(dict(action=a.action,deviceAccess=False,seconds=meta['seconds'],systemWrites=False,startupWrites=False)));return
    import trial_usb as usb
    a.out.mkdir(parents=True,exist_ok=True);report={'action':a.action,'events':{},'systemWrites':False,'startupWrites':False}
    def record(k,v):
        report['events'][k]=v;(a.out/(a.action+'-device.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({k:v},ensure_ascii=False),flush=True);return v
    def factory(cmd):
        assert len(cmd.encode('ascii'))<=231,cmd
        deadline=time.monotonic()+8
        while True:
            r=usb.ExistingInterface()
            try:r.__enter__();break
            except Exception:
                r.close()
                if time.monotonic()>deadline:raise
                time.sleep(.25)
        try:return r.factory_shell(cmd,capture_ms=15000).strip()
        finally:r.close()
    def check(k,cmd,expected):
        v=record(k,factory(cmd));assert v==expected,(k,v);return v
    def adb(args,timeout=30):
        r=subprocess.run([str(a.adb),'-d',*args],capture_output=True,text=True,timeout=timeout)
        if r.returncode:raise RuntimeError('ADB transport failed: '+r.stderr.strip())
        return r.stdout.strip()
    def enable_adb():
        try:factory(usb.FACTORY_ENABLE_USB_ADB_RUNTIME)
        except usb.UsbFactoryError:pass
        deadline=time.monotonic()+25
        while True:
            try:
                assert adb(['get-state'],3)=='device';break
            except Exception:
                if time.monotonic()>deadline:raise
                time.sleep(.5)
        assert adb(['shell','getprop ro.product.device;getprop ro.build.version.incremental'])=='eagle2_ec1706_native\n24849'
    def restore_usb():
        try:factory(usb.FACTORY_RESTORE_USB_NO_ADB_RUNTIME)
        except usb.UsbFactoryError:pass
        time.sleep(3)
        check('usbRestored','getprop sys.usb.config;getprop sys.usb.state',USB+'\n'+USB)
    def routing():
        v=factory('dbus-send --system --print-reply --dest=com.hasselblad.camera /camera org.freedesktop.DBus.Properties.Get string:com.hasselblad.camera string:forward_input_events')
        m=re.search(r'variant\s+(?:int32|byte|uint32)\s+(\d+)',v)
        return int(m.group(1)) if m else v
    check('target','getprop ro.product.device;getprop ro.build.version.incremental','eagle2_ec1706_native\n24849')
    check('gui','sha256sum /system/bin/camera-gui',GUI_SHA+'  /system/bin/camera-gui')
    check('service','sha256sum /system/bin/camera-service',SERVICE_SHA+'  /system/bin/camera-service')
    check('guiRc','sha256sum /system/etc/init/camera-gui.rc',RC_SHA+'  /system/etc/init/camera-gui.rc')
    for dependency in meta.get('audioDependencies',[]):
        n=dependency['name'];assert n in ['libc.so','libaudioclient.so']
        check('audioDependency-'+n,'sha256sum /system/lib64/'+n,dependency['sha256']+'  /system/lib64/'+n)
    if a.action=='status':
        record('services',factory('getprop init.svc.camera-gui;getprop sys.usb.config'))
        record('routing',routing())
        record('state',factory('cat '+IPC+'/state.json 2>/dev/null || true'))
        record('guiLog',factory('tail -n 16 '+REMOTE+'/run.log 2>/dev/null || true'))
        record('engineLog',factory('tail -n 8 '+IPC+'/engine.log 2>/dev/null || true'))
        record('audioLog',factory('tail -n 8 '+REMOTE+'/audio.log 2>/dev/null || true'))
        record('watchLog',factory('cat '+REMOTE+'/watch.log 2>/dev/null || true'));return
    if a.action=='restore':
        check('owner','test ! -L '+REMOTE+' && cat '+REMOTE+'/owner',OWNER)
        record('restore',factory('sh '+REMOTE+'/restore.sh'));time.sleep(4)
        check('stockRunning','getprop init.svc.camera-gui','running')
        check('usbRestored','getprop sys.usb.config;getprop sys.usb.state',USB+'\n'+USB)
        record('routingAfter',routing());return
    # All gates below precede the first runtime change.
    check('stockRunning','getprop init.svc.camera-gui','running')
    check('usbBefore','getprop sys.usb.config;getprop sys.usb.state',USB+'\n'+USB)
    mounts=record('mounts',factory('cat /proc/mounts|grep -E " /tmp | /system "'))
    assert 'tmpfs /tmp tmpfs ' in mounts and '/system ext4 ro,' in mounts
    startup=record('startupBefore',factory('sha256sum /system/etc/init/camera-service.rc /system/etc/init/camera-system.rc'))
    exposure=record('exposure',factory('dbus-send --system --print-reply --dest=com.hasselblad.camera /camera org.freedesktop.DBus.Properties.Get string:com.hasselblad.camera string:exposure_status'))
    m=re.search(r'variant\s+int32\s+(-?\d+)',exposure);assert m and int(m.group(1))&1299==0,'Camera busy'
    assert record('routingBefore',routing())==0,'Another page has captured camera keys'
    record('audioService',factory('getprop init.svc.dji_audio'))
    storage=record('storage',factory('df -k /blackbox /tmp'))
    for line in storage.splitlines()[1:]:
        cols=line.split();assert len(cols)>=6
        minimum=8192 if cols[-1]=='/tmp' else 100000
        assert int(cols[3])>minimum,'Insufficient trial space'
    with tarfile.open(package/'payload.tar.gz','r:gz') as tar:
        members=tar.getmembers();assert {m.name for m in members}==set(meta['files'])
        files={}
        for m in members:
            assert m.isfile() and '/' not in m.name and m.name!='..'
            files[m.name]=tar.extractfile(m).read();assert sha(files[m.name])==meta['files'][m.name]
    staged=False;started=False;paused=False;pid=''
    try:
        present=factory('test -e '+REMOTE+' && echo PRESENT || echo FREE')
        if present=='PRESENT':
            check('oldOwner','test ! -L '+REMOTE+' && cat '+REMOTE+'/owner',OWNER)
            check('oldInactive','test ! -e '+REMOTE+'/gui.pid && test ! -e '+REMOTE+'/engine.pid && test ! -e '+REMOTE+'/audio.pid && echo IDLE','IDLE')
            factory('rm -rf '+REMOTE)
        for d in [REMOTE,STAGE]:
            assert factory('test -e '+d+' && echo PRESENT || echo FREE')=='FREE','Trial directory already exists; inspect first'
            factory('mkdir '+d+' && chmod 700 '+d+' && printf %s '+OWNER+' >'+d+'/owner')
        staged=True
        enable_adb()
        adb(['push',str(package/'payload.tar.gz'),STAGE+'/payload.tar.gz'],90)
        check('archiveHash','sha256sum '+STAGE+'/payload.tar.gz',meta['archiveSha256']+'  '+STAGE+'/payload.tar.gz')
        adb(['shell','tar -xzf '+STAGE+'/payload.tar.gz -C '+STAGE])
        assert adb(['shell','cd '+STAGE+' && sha256sum -c checksums >/dev/null && echo VERIFIED'])=='VERIFIED'
        for n in ['bootstrap.bin','Bootstrap.qml','DoomPage.qml','DoomCameraPage.qml','run.sh','restore.sh','watch.sh','audio-run.sh']:
            factory('cp '+STAGE+'/'+n+' '+REMOTE+'/'+n)
            check('ram-'+n,'sha256sum '+REMOTE+'/'+n,meta['files'][n]+'  '+REMOTE+'/'+n)
        factory('mkdir '+IPC)
        mount=record('ramMount',factory('mount -t tmpfs -o size=8m,mode=0700,rootcontext=u:object_r:system_data_file:s0 tmpfs '+IPC+' 2>&1;echo STATUS:$?'))
        assert mount.endswith('STATUS:0'),mount
        ram=record('ramMountVerified',factory('cat /proc/mounts|grep " '+IPC+' "'))
        assert 'tmpfs '+IPC+' tmpfs ' in ram
        record('ramLabel',factory('ls -ldZ '+IPC))
        record('nativeLabel',adb(['shell','ls -Z '+STAGE+'/engine']))
        result=record('nativeSelftest',adb(['shell','X2D_DOOM_IPC='+IPC+' timeout 15 '+STAGE+'/engine --platform-selftest 2>&1;echo STATUS:$?'],20))
        assert result.endswith('STATUS:0'),result
        factory('rm -f '+IPC+'/input '+IPC+'/exit.request '+IPC+'/engine.done')
        # Independent factory-domain watchdog starts before the display process is touched.
        record('watchLaunch',factory('nohup sh '+REMOTE+'/watch.sh >'+REMOTE+'/watch.log 2>&1 </dev/null &echo $!'))
        time.sleep(.2)
        watch=factory('cat '+REMOTE+'/watch.pid');assert re.fullmatch(r'[1-9][0-9]*',watch)
        check('watchLive','kill -0 '+watch+' && echo LIVE','LIVE')
        started=True
        record('nativeLaunch',adb(['shell','nohup sh '+STAGE+'/native-run.sh >'+STAGE+'/native.log 2>&1 </dev/null &echo $!']))
        deadline=time.monotonic()+8
        while True:
            raw=factory('cat '+IPC+'/state.json 2>/dev/null || true')
            try:state=json.loads(raw)
            except ValueError:state={}
            if state.get('clipAmmo')==50 and state.get('frame',0)>5:break
            if time.monotonic()>deadline:raise RuntimeError('Native engine did not start: '+factory('tail -n 8 '+IPC+'/engine.log'))
            time.sleep(.2)
        record('nativeState',state)
        # Private executable RAM uses a stock file label without relabeling data files.
        factory('mkdir '+CODE)
        mount=record('audioCodeMount',factory('mount -t tmpfs -o size=1m,mode=0700,rootcontext=u:object_r:system_file:s0 tmpfs '+CODE+' 2>&1;echo STATUS:$?'))
        assert mount.endswith('STATUS:0'),mount
        factory('cp '+STAGE+'/libdoom_audio.so '+CODE+'/libdoom_audio.so')
        check('audioCodeHash','sha256sum '+CODE+'/libdoom_audio.so',meta['files']['libdoom_audio.so']+'  '+CODE+'/libdoom_audio.so')
        label=record('audioLabel',factory('ls -Z '+CODE+'/libdoom_audio.so'))
        assert label=='u:object_r:system_file:s0 '+CODE+'/libdoom_audio.so',label
        record('audioLaunch',factory('nohup sh '+REMOTE+'/audio-run.sh >'+REMOTE+'/audio.log 2>&1 </dev/null &echo $!'))
        deadline=time.monotonic()+8
        while True:
            audio=factory('cat '+REMOTE+'/audio.log')
            if 'X2D_DOOM_AUDIO_READY' in audio:break
            if time.monotonic()>deadline:raise RuntimeError('Audio bridge did not become ready: '+audio)
            time.sleep(.2)
        record('audioReady',audio)
        for name,path in [('watch',REMOTE+'/watch.pid'),('engine',STAGE+'/engine.pid'),('audio',REMOTE+'/audio.pid')]:
            live=factory('cat '+path);assert re.fullmatch(r'[1-9][0-9]*',live)
            check(name+'BeforeGui','kill -0 '+live+' && test ! -e '+IPC+'/exit.request && echo LIVE','LIVE')
        record('guiLaunch',factory('nohup sh '+REMOTE+'/run.sh >'+REMOTE+'/run.log 2>&1 </dev/null &echo $!'))
        deadline=time.monotonic()+12
        while True:
            pid=factory('cat '+REMOTE+'/gui.pid 2>/dev/null || true')
            if re.fullmatch(r'[1-9][0-9]*',pid):break
            if time.monotonic()>deadline:raise RuntimeError('GUI launch timeout')
            time.sleep(.02)
        factory('kill -STOP '+pid);paused=True
        check('domain','cat /proc/'+pid+'/attr/current|tr -d "\\000"','u:r:hbl_camera_service:s0')
        for attempt in range(50):
            maps=factory('cat /proc/'+pid+'/maps|grep /system/bin/camera-gui || true')
            match=re.search(r'(?m)^([0-9a-f]+)-[0-9a-f]+\s+r-xp\s+00000000\s+.* /system/bin/camera-gui$',maps)
            if match:
                base=int(match.group(1),16);data=base+meta['dataVa'];cache=base+meta['cacheVa']
                raw=bytes.fromhex(factory('od -An -tx1 -N24 -j '+str(cache)+' /proc/'+pid+'/mem'))
                if raw==struct.pack('<QQQ',data,base+meta['aotVa'],0):break
            factory('kill -CONT '+pid);paused=False;time.sleep(.02);factory('kill -STOP '+pid);paused=True
        else:raise RuntimeError('Stock QML relocations were not ready')
        actual=factory('dd if=/proc/'+pid+'/mem bs=1 skip='+str(data)+' count='+str(meta['unitBytes'])+' 2>/dev/null|sha256sum').split()[0]
        assert actual==meta['stockUnitSha256']
        record('ramUnitWrite',factory('busybox dd if='+REMOTE+'/bootstrap.bin of=/proc/'+pid+'/mem bs=1 seek='+str(data)+' conv=notrunc 2>&1'))
        actual=factory('dd if=/proc/'+pid+'/mem bs=1 skip='+str(data)+' count='+str(meta['unitBytes'])+' 2>/dev/null|sha256sum').split()[0]
        assert actual==meta['unitSha256']
        factory('kill -CONT '+pid);paused=False;time.sleep(1)
        check('startupAfter','sha256sum /system/etc/init/camera-service.rc /system/etc/init/camera-system.rc',startup)
        record('guiLog',factory('tail -n 16 '+REMOTE+'/run.log'))
        record('readyForMenu',True);record('secondsLimit',meta['seconds'])
    except Exception as e:
        record('error',str(e))
        if paused:
            try:factory('kill -CONT '+pid)
            except Exception:pass
        if staged:
            try:record('failureRestore',factory('sh '+REMOTE+'/restore.sh'))
            except Exception as error:record('restoreError',str(error))
        restore_usb();time.sleep(1);record('stockAfterFailure',factory('getprop init.svc.camera-gui'))
        raise
if __name__=='__main__':main()
