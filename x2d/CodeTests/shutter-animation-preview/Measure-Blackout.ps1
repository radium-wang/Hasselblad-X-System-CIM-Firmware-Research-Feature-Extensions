param(
    [ValidateSet('Plan','Arm','Read','Watch')][string]$Mode='Plan',
    [ValidateRange(5,60)][int]$Seconds=30,
    [string]$OutputDirectory=(Join-Path $PSScriptRoot 'outputs/blackout-probe')
)
$ErrorActionPreference='Stop'
# 默认只显示计划；Arm/Read 显式读取设备。无拍摄、进程跟踪、设备文件写入或服务重启。
$expectedGui='16391452abdc69de9e0807e065c0f4ab3f1ccb5fc288f6fc4e6f5cb3bdca12e0'
$logCommand='logcat -d -v monotonic camera-gui:I camera-service:I "*:S" | grep -E "Main state:|liveview state:|Handling.*ShowMode|dcamcaptureengine.cpp.*evt:" | tail -24'
if($Mode -eq 'Plan') {
    'X2D 100C / 4.2.0：Arm 记录起点；用户手动拍摄；Read 读取原厂日志。仅输出软件状态时间，不代表光学黑屏实测。'
    return
}
if($Mode -eq 'Watch') {
    # 仅在主机循环读；失败立即停止，不重试不确定的 USB 请求。
    & $PSCommandPath -Mode Arm -OutputDirectory $OutputDirectory
    $watch=[Diagnostics.Stopwatch]::StartNew()
    $seen=[Collections.Generic.HashSet[string]]::new()
    $collected=[Collections.Generic.List[object]]::new()
    $anyTruncated=$false
    $recordPath=Join-Path ([IO.Path]::GetFullPath($OutputDirectory)) 'events.json'
    'PASSIVE_WATCH_READY'
    $firstFinished=$null
    try {
        while($watch.Elapsed.TotalSeconds -lt $Seconds) {
            & $PSCommandPath -Mode Read -OutputDirectory $OutputDirectory | Out-Null
            $snapshot=Get-Content -LiteralPath $recordPath -Raw | ConvertFrom-Json
            $anyTruncated=$anyTruncated -or $snapshot.possiblyTruncated
            foreach($event in $snapshot.events) {
                $key=('{0}|{1}|{2}' -f $event.timeMs,$event.kind,$event.value)
                if($seen.Add($key)) {
                    $collected.Add($event)
                    if($event.kind -eq 'sequence_event' -and $event.value -like 'ExposureFinished:*'){$firstFinished=$watch.Elapsed.TotalSeconds}
                }
            }
            # 曝光结束后再留五秒，收集恢复事件；最长由 Seconds 约束。
            if($null -ne $firstFinished -and $watch.Elapsed.TotalSeconds-$firstFinished -ge 5){break}
            Start-Sleep -Milliseconds 150
        }
    } finally {
        if($snapshot) {
            $snapshot.events=@($collected | Sort-Object timeMs)
            $snapshot.possiblyTruncated=$anyTruncated
            $snapshot | Add-Member -NotePropertyName acquisition -NotePropertyValue 'host_polling_stock_log' -Force
            $snapshot | Add-Member -NotePropertyName coverageGuaranteed -NotePropertyValue $false -Force
            $snapshot | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $recordPath -Encoding utf8
        }
    }
    'PASSIVE_WATCH_FINISHED count='+$collected.Count
    return
}
. (Join-Path $PSScriptRoot '../temporary_af_speed_probe/Usb.ps1')
$null=[X2DTemporaryUi.TemporaryUiUsb]::SelfTestShell()
$info=Read-ReviewedUsb @('sha256sum /system/bin/camera-gui','cat /proc/uptime; pidof camera-gui; pidof camera-service')
if($info[0].Trim().Split(' ')[0] -ne $expectedGui){throw 'GUI hash mismatch; no measurement.'}
$stateLines=@($info[1].Trim() -split '\r?\n')
if($stateLines.Count -ne 3 -or $stateLines[0] -notmatch '^([0-9]+\.[0-9]+) '){throw 'Invalid process/uptime response.'}
$uptime=[double]::Parse($Matches[1],[Globalization.CultureInfo]::InvariantCulture)
if($stateLines[1] -notmatch '^\d+$' -or $stateLines[2] -notmatch '^\d+$'){throw 'Expected one GUI and one service process.'}
$directory=[IO.Path]::GetFullPath($OutputDirectory)
$baselinePath=Join-Path $directory 'baseline.json'
if($Mode -eq 'Arm') {
    [void][IO.Directory]::CreateDirectory($directory)
    [ordered]@{model='X2D 100C';firmware='4.2.0';guiSha256=$expectedGui;startUptime=$uptime;guiPid=[int]$stateLines[1];servicePid=[int]$stateLines[2]} |
        ConvertTo-Json | Set-Content -LiteralPath $baselinePath -Encoding utf8
    'PASSIVE_PROBE_ARMED: user operates shutter; no capture command sent.'
    return
}
if(-not (Test-Path -LiteralPath $baselinePath)){throw 'Arm before Read.'}
$baseline=Get-Content -LiteralPath $baselinePath -Raw | ConvertFrom-Json
if($uptime -lt $baseline.startUptime -or [int]$stateLines[1] -ne $baseline.guiPid -or [int]$stateLines[2] -ne $baseline.servicePid){throw 'Processes or boot changed; Arm again.'}
$text=@(Read-ReviewedUsb @($logCommand))[0]
$events=@()
foreach($line in ($text -split '\r?\n')) {
    if($line -notmatch '^\s*(\d+\.\d+)\s+(\d+)\s+\d+\s+[A-Z]\s+(camera-gui|camera-service):\s+(.*)$'){continue}
    $stamp=[double]::Parse($Matches[1],[Globalization.CultureInfo]::InvariantCulture)
    $processId=[int]$Matches[2];$tag=$Matches[3];$body=$Matches[4]
    if($stamp -lt $baseline.startUptime){continue}
    $kind=$null;$value=$null
    if($tag -eq 'camera-gui' -and $processId -eq $baseline.guiPid -and $body -match 'Main state: ([a-z_]+)\s*$'){$kind='gui_state';$value=$Matches[1]}
    elseif($tag -eq 'camera-gui' -and $processId -eq $baseline.guiPid -and $body -match 'liveview state: ([a-z_]+)\s*$'){$kind='liveview_state';$value=$Matches[1]}
    elseif($tag -eq 'camera-service' -and $processId -eq $baseline.servicePid -and $body -match 'Handling.*show: LiveviewControl::(ShowMode[A-Za-z]+)'){$kind='show_request';$value=$Matches[1]}
    elseif($tag -eq 'camera-service' -and $processId -eq $baseline.servicePid -and $body -match 'dcamcaptureengine\.cpp.*evt: SequenceResource::([A-Za-z]+) next task: SequenceResource::([A-Za-z]+)'){$kind='sequence_event';$value=$Matches[1]+':'+$Matches[2]}
    if($kind){$events += [ordered]@{timeMs=[math]::Round($stamp*1000);kind=$kind;value=$value}}
}
# 只保存白名单事件，不保存原始日志、照片路径、设备标识或命令回显。
$record=[ordered]@{schemaVersion=1;model=$baseline.model;firmware=$baseline.firmware;guiSha256=$expectedGui;startUptime=$baseline.startUptime;readUptime=$uptime;source='stock_logcat_monotonic';physicalBlackoutMeasured=$false;tailLimit=24;possiblyTruncated=(@($text -split '\r?\n' | Where-Object {$_.Trim()}).Count -ge 24);events=@($events)}
$record | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $directory 'events.json') -Encoding utf8
'PASSIVE_EVENTS_SAVED count='+$events.Count
