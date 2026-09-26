import QtQuick
import com.hasselblad.types
import com.hasselblad.proxies
import com.hasselblad.uiproxies
import "qrc:/app/qml/components" as StockComponents

// Runtime model experiment. This never writes /proc/mem or camera files.
// It is deliberately fail-closed until an exact two-item stock model and
// CameraUI.canChangeAfc are visible through ControlDrawer.
Item {
    id: root
    objectName: "X2dAfcMenuController"
    visible: false
    width: 0
    height: 0

    property var controlViewModel: null
    property bool focusPopoverOpen: false
    property var stockAfs: null
    property var stockMf: null
    property var afcItem: null
    property bool loaded: false
    property bool busy: false
    property bool faulted: false
    property string statusMessage: "AF-C 尚未开启"
    readonly property bool ready: !faulted && controlViewModel !== null && CameraUI.canChangeAfc
    signal result(bool loaded, bool busy, string message)

    Component {
        id: afcFactory
        StockComponents.FocusModeListItem {
            focusMode: HblmTypes.E_FocusModes_Afc
            valid: CameraUI.canChangeAfc
            icon: "image://svg/ic_controlscreen_focus_mode_AF-C"
            text: "Continuous Autofocus"
        }
    }

    function sameModel(items) {
        if (!controlViewModel || controlViewModel.focusModeModel.length !== items.length)
            return false
        for (var i = 0; i < items.length; ++i) {
            if (controlViewModel.focusModeModel[i] !== items[i])
                return false
        }
        return true
    }

    function replaceModel(items) {
        // A list property is mutable in QML. Read back every entry: a silent
        // append/conversion must never be reported as a successful switch.
        controlViewModel.focusModeModel.length = 0
        for (var i = 0; i < items.length; ++i)
            controlViewModel.focusModeModel.push(items[i])
        return sameModel(items)
    }

    function publish(message) {
        statusMessage = message
        result(loaded, busy, message)
    }

    function setEnabled(enable) {
        if (busy || faulted)
            return false
        if (enable === loaded) {
            publish(loaded ? "AF-C 菜单扩展已加载" : "AF-C 尚未开启")
            return true
        }
        if (enable && !ready) {
            publish("AF-C 条件未满足，未加载")
            return false
        }
        if (focusPopoverOpen) {
            publish("请先关闭对焦模式弹窗")
            return false
        }
        if (!enable && Camera.focus_mode === HblmTypes.E_FocusModes_Afc) {
            publish("请先切换到 AF-S 或 MF，再关闭耍起功能")
            return false
        }
        if (!enable && !sameModel([stockAfs, afcItem, stockMf])) {
            publish("对焦列表被其他代码修改，拒绝卸载")
            return false
        }

        busy = true
        var didMutate = false
        try {
            if (enable) {
                var model = controlViewModel.focusModeModel
                if (model.length !== 2 ||
                    model[0].focusMode !== HblmTypes.E_FocusModes_Afs ||
                    model[1].focusMode !== HblmTypes.E_FocusModes_Man) {
                    throw new Error("原厂对焦列表不是预期的 AF-S/MF 两项")
                }
                stockAfs = model[0]
                stockMf = model[1]
                afcItem = afcFactory.createObject(root)
                didMutate = true
                if (!afcItem || !replaceModel([stockAfs, afcItem, stockMf]))
                    throw new Error("AF-C 条目插入后回读不一致")
                loaded = true
                publish("AF-C 菜单扩展已加载")
            } else {
                didMutate = true
                if (!replaceModel([stockAfs, stockMf]))
                    throw new Error("恢复原厂两项后回读不一致")
                loaded = false
                afcItem.destroy()
                afcItem = null
                publish("AF-C 尚未开启")
            }
            return true
        } catch (error) {
            // Keep the AF-C object alive if the list still references it.
            // A failed rollback is reported, never shown as OFF.
            if (didMutate && stockAfs && stockMf) {
                try {
                    if (replaceModel([stockAfs, stockMf])) {
                        loaded = false
                        if (afcItem) afcItem.destroy()
                        afcItem = null
                    } else {
                        faulted = true
                    }
                } catch (recoveryError) {
                    faulted = true
                }
            }
            publish(faulted ? "对焦列表状态不确定；请重启 GUI：" + error :
                    didMutate ? "切换未生效，已恢复原厂列表：" + error :
                                "未加载：" + error)
            return false
        } finally {
            busy = false
            result(loaded, busy, statusMessage)
        }
    }
}
