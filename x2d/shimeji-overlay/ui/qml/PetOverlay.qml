// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (c) 2026 Radium Wang.
import QtQuick
import QtQuick.Window
Item {
    id:root
    objectName:"X2dShimejiTrial"
    width:1024;height:768
    focus:false
    required property string dataRoot // file URL ending in /
    required property string controlRoot // file URL ending in /
    required property string assetRoot // file URL of character/img; no trailing /
    property bool metricsEnabled:false
    signal exitRequested()
    property var petState:({x:360,y:200,ax:64,ay:128,image:"/shime1.png",visible:true,right:false,mirror:false,dragging:false,input:-1})
    property var hitMasks:({})
    property int tickNumber:-1
    property double requestNumber:Date.now()
    property double releaseSequence:-1
    property bool readPending:false
    property bool dragging:false
    property bool dragHold:false
    readonly property bool directDrag:dragging||dragHold
    property bool exiting:false
    property real touchX:360
    property real touchY:220
    property real dragLeft:296
    property real dragTop:72
    property real grabX:0
    property real grabY:0
    property int secondsLeft:600
    property int renderFrames:0
    property int reads:0
    property int dragMoves:0
    property real readLatency:0
    property real maxDragError:0
    property double metricStamp:Date.now()
    property real stageScale:Math.min(width/720,height/540)
    function clamp(value,limit){return Math.max(0,Math.min(limit,value))}
    function put(path,text){var r=new XMLHttpRequest();r.open("PUT",path);r.send(text)}
    function sendInput(behavior) {
        var n=++requestNumber
        put(dataRoot+"input",n+" "+touchX+" "+touchY+" "+(dragging?1:0)+" "+(behavior||"-")+" "+dragLeft+" "+dragTop+"\n")
        return n
    }
    function requestExit() {
        if(exiting)return
        exiting=true;dragging=false
        put(controlRoot+"exit.request","X2D_SHIMEJI_EXIT\n")
        exitRequested()
    }
    function refresh() {
        if(readPending||exiting)return
        readPending=true
        var started=Date.now(),r=new XMLHttpRequest()
        r.onreadystatechange=function(){
            if(r.readyState!==XMLHttpRequest.DONE)return
            readPending=false
            try {
                var next=JSON.parse(r.responseText)
                if(next.tick!==tickNumber){petState=next;tickNumber=next.tick;reads++;readLatency+=Date.now()-started}
                if(dragHold && next.input>=releaseSequence && !next.dragging)dragHold=false
            }catch(e){}
        }
        r.open("GET",dataRoot+"state.json?tick="+Date.now());r.send()
    }
    function spriteContains(point) {
        var mask=hitMasks[petState.image]
        if(!mask)return false // Wait for the alpha mask; do not block the menu.
        var x=Math.floor(point.x),y=Math.floor(point.y)
        if(x<0||y<0||x>=mask.w||y>=mask.h)return false
        if(pet.mirror)x=mask.w-1-x
        var runs=mask.rows[y]
        for(var i=0;i<runs.length;i+=2)if(x>=runs[i]&&x<runs[i+1])return true
        return false
    }
    Timer{interval:16;repeat:true;running:root.visible&&!root.exiting;onTriggered:root.refresh()}
    Timer{interval:16;repeat:true;running:root.dragging;onTriggered:root.sendInput("-")}
    Timer{interval:1000;repeat:true;running:!root.exiting;onTriggered:{root.secondsLeft--;if(root.secondsLeft<=0)root.requestExit()}}
    Connections{target:root.Window.window;function onFrameSwapped(){root.renderFrames++}}
    Timer {
        interval:1000;repeat:true;running:root.metricsEnabled&&!root.exiting
        onTriggered:{
            var elapsed=Date.now()-root.metricStamp
            root.put(root.dataRoot+"metrics.json",JSON.stringify({fps:root.renderFrames*1000/elapsed,readsPerSecond:root.reads*1000/elapsed,meanReadMs:root.reads?root.readLatency/root.reads:0,dragMoves:root.dragMoves,maxDragError:root.maxDragError,nativeTick:root.tickNumber,dragging:root.dragging})+"\n")
            root.metricStamp=Date.now();root.renderFrames=0;root.reads=0;root.readLatency=0
        }
    }
    Item {
        id:stage
        objectName:"ShimejiStage"
        width:720;height:540
        x:(root.width-width*root.stageScale)/2;y:(root.height-height*root.stageScale)/2
        scale:root.stageScale;transformOrigin:Item.TopLeft
        Image {
            id:pet
            objectName:"ShimejiSprite"
            source:root.assetRoot+root.petState.image
            visible:root.petState.visible&&!root.exiting
            smooth:true;cache:true;asynchronous:false
            width:implicitWidth;height:implicitHeight
            x:root.directDrag?root.dragLeft:root.clamp(root.petState.x-(root.petState.right?width-root.petState.ax:root.petState.ax),720-width)
            y:root.directDrag?root.dragTop:root.clamp(root.petState.y-root.petState.ay,540-height)
            mirror:root.petState.mirror
            Behavior on x{enabled:!root.directDrag;NumberAnimation{duration:18;easing.type:Easing.Linear}}
            Behavior on y{enabled:!root.directDrag;NumberAnimation{duration:18;easing.type:Easing.Linear}}
            MouseArea {
                id:touch
                objectName:"ShimejiTouch"
                anchors.fill:parent
                enabled:!root.exiting
                preventStealing:true
                containmentMask:QtObject{function contains(point:point):bool{return root.spriteContains(point)}}
                onPressed:function(mouse){
                    var p=touch.mapToItem(stage,mouse.x,mouse.y)
                    root.touchX=root.clamp(p.x,720);root.touchY=root.clamp(p.y,540)
                    root.grabX=mouse.x;root.grabY=mouse.y
                    root.dragLeft=pet.x;root.dragTop=pet.y
                    root.dragHold=false;root.dragging=true;root.sendInput("-")
                }
                onPositionChanged:function(mouse){
                    if(!root.dragging)return
                    var p=touch.mapToItem(stage,mouse.x,mouse.y)
                    root.touchX=root.clamp(p.x,720);root.touchY=root.clamp(p.y,540)
                    root.dragLeft=root.clamp(p.x-root.grabX,720-pet.width)
                    root.dragTop=root.clamp(p.y-root.grabY,540-pet.height)
                    root.dragMoves++
                    root.maxDragError=Math.max(root.maxDragError,Math.abs(pet.x-root.dragLeft),Math.abs(pet.y-root.dragTop))
                }
                onReleased:{root.dragging=false;root.dragHold=true;root.releaseSequence=root.sendInput("-")}
                onCanceled:{root.dragging=false;root.dragHold=true;root.releaseSequence=root.sendInput("-")}
                onDoubleClicked:root.sendInput("StandBlush")
            }
        }
    }
    Rectangle {
        id:exitButton
        objectName:"ShimejiExit"
        anchors.right:parent.right;anchors.rightMargin:12;y:12
        width:74;height:44;radius:9;color:press.pressed?"#b0303238":"#9930353d"
        visible:!root.exiting
        Text{anchors.centerIn:parent;text:"Exit";color:"white";font.pixelSize:21}
        MouseArea{id:press;anchors.fill:parent;onClicked:root.requestExit()}
    }
    Component.onCompleted:{
        var r=new XMLHttpRequest()
        r.onreadystatechange=function(){if(r.readyState===XMLHttpRequest.DONE){try{hitMasks=JSON.parse(r.responseText)}catch(e){}}}
        r.open("GET",controlRoot+"hit-masks.json");r.send()
        sendInput("-");console.log("X2D_SHIMEJI_TRANSPARENT_READY")
    }
}
