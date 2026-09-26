// Tests the JavaScript control flow in AfcMenuController.qml with mocked Qt
// objects. This does NOT verify Qt list-property behavior or camera runtime.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, 'AfcMenuController.qml'), 'utf8');

function qmlFunction(name) {
    const start = source.indexOf(`    function ${name}(`);
    assert.notEqual(start, -1, `missing ${name}`);
    const open = source.indexOf('{', start);
    let depth = 0;
    let quote = null;
    for (let i = open; i < source.length; ++i) {
        const char = source[i];
        if (quote) {
            if (char === '\\') ++i;
            else if (char === quote) quote = null;
            continue;
        }
        if (char === '"' || char === "'") { quote = char; continue; }
        if (char === '{') ++depth;
        else if (char === '}' && --depth === 0)
            return source.slice(start, i + 1);
    }
    throw new Error(`unterminated ${name}`);
}

const methods = ['sameModel', 'replaceModel', 'publish', 'setEnabled']
    .map(qmlFunction).join('\n');

function harness(options = {}) {
    const afs = { focusMode: 1 };
    const mf = { focusMode: 3 };
    const events = [];
    const created = [];
    const state = {
        controlViewModel: { focusModeModel: options.model || [afs, mf] },
        focusPopoverOpen: false,
        CameraUI: { canChangeAfc: options.gate !== false },
        Camera: { focus_mode: 1 },
        HblmTypes: { E_FocusModes_Afs: 1, E_FocusModes_Afc: 2, E_FocusModes_Man: 3 },
        root: {},
        stockAfs: null, stockMf: null, afcItem: null,
        loaded: false, busy: false, faulted: false,
        statusMessage: '耍起功能已关闭',
        result: (...args) => events.push(args),
        afcFactory: { createObject: () => {
            const item = { focusMode: 2, destroyed: false,
                           destroy() { this.destroyed = true; } };
            created.push(item);
            return item;
        } },
        Error,
    };
    Object.defineProperty(state, 'ready', {
        get() { return !state.faulted && !!state.controlViewModel && state.CameraUI.canChangeAfc; },
    });
    vm.createContext(state);
    vm.runInContext(methods, state);
    return { state, afs, mf, events, created };
}

{
    const { state, afs, mf, created } = harness();
    assert.equal(state.setEnabled(true), true);
    assert.equal(state.loaded, true);
    assert.deepEqual(Array.from(state.controlViewModel.focusModeModel), [afs, created[0], mf]);
    state.Camera.focus_mode = state.HblmTypes.E_FocusModes_Afc;
    assert.equal(state.setEnabled(false), false);
    assert.equal(state.loaded, true);
    assert.equal(created[0].destroyed, false);
    state.Camera.focus_mode = state.HblmTypes.E_FocusModes_Afs;
    assert.equal(state.setEnabled(false), true);
    assert.deepEqual(Array.from(state.controlViewModel.focusModeModel), [afs, mf]);
    assert.equal(state.loaded, false);
    assert.equal(created[0].destroyed, true);
}
{
    const { state, afs, mf } = harness({ gate: false });
    assert.equal(state.setEnabled(true), false);
    assert.deepEqual(Array.from(state.controlViewModel.focusModeModel), [afs, mf]);
}
{
    const { state, afs, mf } = harness();
    state.focusPopoverOpen = true;
    assert.equal(state.setEnabled(true), false);
    assert.deepEqual(Array.from(state.controlViewModel.focusModeModel), [afs, mf]);
}
{
    const { state } = harness();
    assert.equal(state.setEnabled(true), true);
    state.controlViewModel.focusModeModel.push({ focusMode: 4 });
    assert.equal(state.setEnabled(false), false);
    assert.equal(state.loaded, true);
}
{
    const { state, afs, mf, created } = harness();
    const model = state.controlViewModel.focusModeModel;
    let failOnce = true;
    model.push = function (item) {
        if (item.focusMode === 2 && failOnce) {
            failOnce = false;
            throw new Error('injected transient list failure');
        }
        return Array.prototype.push.call(this, item);
    };
    assert.equal(state.setEnabled(true), false);
    assert.equal(state.faulted, false);
    assert.equal(state.loaded, false);
    assert.deepEqual(Array.from(model), [afs, mf]);
    assert.equal(created[0].destroyed, true);
}
{
    const { state } = harness();
    const model = state.controlViewModel.focusModeModel;
    model.push = () => { throw new Error('injected persistent list failure'); };
    assert.equal(state.setEnabled(true), false);
    assert.equal(state.faulted, true);
    assert.equal(state.ready, false);
    assert.equal(state.setEnabled(true), false);
}

console.log('controller logic mock OK: enable, verified disable, AF-C/gate/popup guards, external-mutation guard, transient rollback, persistent fault lock');
