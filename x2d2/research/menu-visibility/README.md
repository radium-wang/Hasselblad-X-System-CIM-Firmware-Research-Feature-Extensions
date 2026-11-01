# X2D II sub-menu row visibility: the row filter contract

English first, then the same content in Chinese. / 先英文，后同内容中文。

Scope: Hasselblad X2D II 100C, firmware 1.1.9.2, 1.3.16.2 and 1.3.18.1. Static
analysis of a stock `camera-gui` that the reader supplies, plus one labelled
device observation. Vendor firmware and extracted QML are not distributed here.
Addresses are for 1.3.18.1 unless stated otherwise, and are not an external call
interface or an installation step. First-generation cameras have their own menu
units; none of these addresses or offsets transfer.

Input identity (our own extractions, SHA-256 of `camera-gui`):

| Firmware | SHA-256 |
| --- | --- |
| 1.1.9.2 | `41f85a203934d14011bcc1bf58f7282eae6f0c6b54a176872ab2edc2324f042a` |
| 1.3.16.2 | `b1b643cb36176cd5a49129dd9bb2be480aa045a96ed1c35c30a779ab5af0801b` |
| 1.3.18.1 | `ea2cf8a5f6209f301971f55dd1ef86882c09db04b2e60371d2a243b79f1d8098` |

## How this relates to the existing menu research here

The menu work already in this repository targets the top-level `MainScreen` grid
and `FavoriteModel` on the first-generation camera. This note is a different
model on a different camera: the rows **inside** a sub-menu page on the X2D II,
served by `SubMenuModel` and filtered by `FilteredSubMenuModel`. It does not
change anything in the twelfth-entry analysis, which routes around `menuFile`
and never reaches this filter. It answers a narrower question: once a sub-menu
page is open, what must a row satisfy to be drawn at all.

## The menu tree is built in C++ at static-init time

Seventeen constructor symbols carry it: the `MenuItem` base constructor plus 16
subclass constructors covering 14 element types, `DropDown` and `ValueSwitch`
each having two overloads. Every one of them takes `GuiTypes::E_MenuAvail` and a
`bool` as construction arguments, and `MenuItem` exposes no setter for either, so
the construction sites are a complete account of both gates.

Counts from a scan that locates the constructors by mangled name and emulates
each definition function (see Reproduction):

| Firmware | Definition functions | Entries | Demo-flagged |
| --- | ---: | ---: | ---: |
| 1.1.9.2 | 20 | 550 | 45 |
| 1.3.16.2 | 20 | 553 | 45 |
| 1.3.18.1 | 20 | 553 | 45 |

Those totals are binary-wide. One `camera-gui` serves more than one camera
configuration, and three of the twenty definition functions are per-configuration
units. The X2D II's own unit is `_GLOBAL__sub_I_menux2d.cpp`, with **111 entries
of which 14 are demo-flagged**, identical in all three firmware versions. The
other two configurations are outside this repository's stated scope and are not
characterised here.

`MenuItem`'s base constructor is at `0x1732e38`. The demangled symbol gives the
parameter order directly, with the `bool` sitting between `E_Proxy` and
`E_MenuRW`. Object layout, `sizeof(MenuItem) == 0x130`:

| Offset | Field |
| ---: | --- |
| `0x00` | `E_MenuElem` |
| `0x08` / `0x10` / `0x18` | id `QString` (char16 data pointer at `0x10`) |
| `0xf8` | `E_Proxy` |
| `0xfc` | demo `bool`, stored as `and w10, w7, 1` then `strb w10, [x0, 0xfc]` |
| `0x100` | `E_MenuRW` |
| `0x104` | `E_MenuAvail` |
| `0x114` | `E_MenuOption` |

Re-derive these offsets per build from the base constructor rather than assuming
them: the three enum arguments arrive on the stack and are stored to `0x100`,
`0x104` and `0x114` in that order.

## Role numbering

`SubMenuModel::data(QModelIndex const&, int) const` is at `0x172ea60`. Its
dispatch does `sub w8, role, 0x100` then `cmp w8, 0xd`, so it accepts 14 role
values, `0x100` to `0x10d`.

The names and the values are read rather than inferred. The QML-facing interface
class `SubmenuModelIf` is registered as a QML element and carries a `Roles` enum
in its metaobject. Decoding the enum key pairs in
`qt_meta_data_ZN14SubmenuModelIfE` (`0x256d060`) and resolving each key's string
index against `qt_meta_stringdata_ZN14SubmenuModelIfE` (`0x256fe74`) gives the
whole table, 14 keys with no gaps:

| Value | Name | Value | Name |
| ---: | --- | ---: | --- |
| `0x100` | `ElemRole` | `0x107` | `ValidRole` |
| `0x101` | `NameRole` | `0x108` | `OptionsRole` |
| `0x102` | `Text1Role` | `0x109` | `DemoRole` |
| `0x103` | `Text2Role` | `0x10a` | `SectionNameRole` |
| `0x104` | `DescriptionRole` | `0x10b` | `PropValueRole` |
| `0x105` | `ProxyRole` | `0x10c` | `ItemValuesRole` |
| `0x106` | `EnabledRole` | `0x10d` | `SubLevelRole` |

Three of them are cross-checked against what `SubMenuModel::data` actually
loads, which is what ties the interface enum to this implementation:

| Role | What that case loads |
| --- | --- |
| `0x100` `ElemRole` | member `0x00`, the `E_MenuElem` |
| `0x107` `ValidRole` | member `0x104`, then calls `Menu::conditionValid(GuiTypes::E_MenuAvail)` at `0x1722520` |
| `0x109` `DemoRole` | member `0xfc` |

`SubMenuModel::data` is the only menu function that reads `0xfc`.

One method note, because it cost us an error in the opposite direction while
writing this: `rabin2 -s` and radare2's string index do not surface these names,
because they sit inside a metaobject string blob as NUL-separated entries rather
than as symbols or as indexed strings. A raw byte search finds them. Failing to
find such a name with `is` or `iz` is not evidence that it is absent.

## The filter

`FilteredSubMenuModel::filterAcceptsRow(int, QModelIndex const&) const` is at
`0x171f010`, 392 bytes. It reads `GuiObject::demo_mode()` (`0x10cfaa8`) through
`GuiObjectImpl::instance()`, then the two roles above, and computes:

```
demoMode = GuiObject::demo_mode()
isDemo   = data(index, 0x109).toBool()
elem     = data(index, 0x100).toInt()

if ((elem & ~1) == 12)              return false
if (!data(index, 0x107).toBool())   return false
return demoMode || !isDemo
```

The first test is `and w8, w21, 0xfffffffe` then `cmp w8, 0xc`, so it rejects
`E_MenuElem` 12 and 13 together. Four `E_MenuElem` values are confirmed from the
constructors: `Switch` 4, `StorageInfo` 11, `SubHeader` 12, `Separator` 13. The
remaining values were not read.

### Three consequences

**1. Headings and separators are never rows.** They are rejected before any gate
is consulted, so an entry inserted as a `SubHeader` will not appear as a row
whatever else is set on it. Headings are carried by the section mechanism
instead: `SectionNameRole` (`0x10a`) is a role of this very model, and the binary
also carries `isSectionFirstInList`, `separatorTopPadding`,
`separatorBottomPadding` and Qt's `QQuickViewSection`. The rejection is proven
from the disassembly; the section routing is read off those names and was not
traced call by call.

**2. Two independent gates, and a row needs both.** `E_MenuAvail` through
`Menu::conditionValid`, and the per-entry demo `bool` against the single global
`demo_mode`. The permissive defaults are `E_MenuAvail_None` and `false`.

**3. A section whose rows are all filtered out produces nothing.** Since a
heading is not a row, there is no row left for the view to attach a section to,
so neither the rows nor the heading appear. Evidence levels differ across that
sentence: the first half is static analysis, the second half is static analysis
that one **device observation** (实机观察) is consistent with. On one retail
X2D II at 1.3.18.1 the owner saw nothing at all at the position where this
reading puts a heading group whose rows do not pass, and no empty heading left
behind. That corroborates the static map rather than independently proving the
section behaviour, since it presupposes the map is right about which entries are
defined there. One camera, one firmware version, one menu page. No camera
setting was changed and nothing was installed to obtain it.

## The demo axis

The `bool` every constructor takes is the second visibility axis, independent of
`E_MenuAvail`, and it is the larger of the two tiers: 45 entries binary-wide, 14
in the X2D II unit.

`demo_mode` itself is a persisted `GuiSettings` property with the same generated
shape as `diagonal_joystick_enabled` in
[the MCU joystick input path note](../../joystick-eight-way/research/INPUT-PATH.md):
`GuiSettings::demo_mode() const`, `GuiSettings::setDemo_mode(bool, bool)`,
`resetDemo_mode`, a changed signal and a `demo_mode` settings key. It ships
false.

A `Switch` whose settings key is `demo_mode` does exist among the developer rows,
with `E_MenuAvail_None`, so nothing gates it on availability. But its own demo
`bool` is 1, and by the filter above that makes it visible only when demo mode is
already on. The user interface therefore exposes no path to turn it on. This note
states that as a limit and does not describe any other path.

One dead end worth recording so nobody else walks it: the GUI resources contain a
`DemoMarker.qml` component, a translucent overlay documented in its own source as
a way to mark an item that is not finished. Nothing in the shipping resources
instantiates it, and the only references to its own `showMarker` property are its
declaration and its own binding. The live mechanism is the row filter above, not
that component.

## Reproduction

Firmware is not included. With a `camera-gui` extracted from one of the releases
above, from the repository root:

```
rabin2 -s camera-gui > syms.txt
grep -E '_ZN8MenuItemC2E|_ZN6ButtonC2E|_ZN9SubHeaderC2E' syms.txt
r2 -q -e scr.color=0 -c 'is~filterAcceptsRow' camera-gui
r2 -q -e scr.color=0 -c 'af @ 0x171f010; pdf @ 0x171f010' camera-gui
r2 -q -e scr.color=0 -c 'af @ 0x172ea60; pdf @ 0x172ea60' camera-gui
```

Locating the constructors by mangled name means no address table has to be
carried from build to build. The layout comes out of the base constructor, the
accepted role range out of the `SubMenuModel::data` jump table, and the role
names and values out of the `SubmenuModelIf` metaobject: read the enum key pairs
from `qt_meta_data_ZN14SubmenuModelIfE` as little-endian `uint32` and resolve
each key's string index against the `{offset, size}` header of
`qt_meta_stringdata_ZN14SubmenuModelIfE`.

Three traps, all of which cost us time:

- `E_MenuAvail` is the last **register** argument for most of these
  constructors, but it lands on the **stack** for the `DropDown` overload that
  takes a `QVariant` by value, because the `QVariant` consumes a register as a
  hidden pointer. For that overload the `bool` is in `w6`.
- Several of these addresses carry more than one symbol because of
  identical-code folding. Resolve by symbol name, never by address alone.
- A constructor the compiler inlined is invisible to call-site scanning, and at
  least one inlined menu entry exists in this binary. The entry totals above are
  therefore a floor, not a proven total. The filter contract itself does not
  depend on them.

The scanner that produced the counts reports how many constructors it located
and how many call sites it could not resolve; the figures here are from runs that
were clean on both lines for all three firmware versions. It is not part of this
change. It can be contributed under `x2d2/tools/` as a follow-up if that is
wanted.

## Independent verification of figures already published here

Checked against our own extractions, not against copies of this repository:

- `camera-gui` 1.3.18.1 SHA-256 matches the hash published in
  [the MCU joystick input path note](../../joystick-eight-way/research/INPUT-PATH.md)
  byte for byte, as does `exMCU_hb722.cont`
  (`f4ffdae8350d7a7f536940f8965f26e24a9d6bfe6337dc8a031b9a81bbb64d11`).
- All three addresses cited in that note resolve to the symbols it names in our
  copy: `0x10c9508` `GuiSettings::diagonal_joystick_enabled() const`,
  `0x17741b8` `JoystickInput::onJoystickEvent(JoystickInput::E_JoystickDirection)`,
  `0x1694e80` `CommonConstants::stepFocusPoint(QPointF, QSizeF, HblmTypes::E_CropMode, int, int) const`.
  `0x10c9508` carries more than one symbol in our copy, so resolve that one by
  name.
- Our own 1.3.16.2 to 1.3.18.1 comparison, by a different method, also found
  nothing attributable to the release note about the rear display in low light.
  That is consistent with
  [the exMCU version comparison](../exmcu/VERSION-COMPARISON.md). The point in
  that note about the MCU display symbols being named for the sub/top LCD also
  corrected how we had read an earlier observation of our own.

## Evidence boundary

Static analysis of a stock binary throughout, except the single device
observation labelled above. No camera was modified, no firmware was written, and
nothing here is a persistence, installation or write path. Reading the filter
does not establish that any particular row can be added, that a backend exists
behind it, or that a row which passes the filter is also selectable: menu
visibility, option selectability and backend effect are separate questions and
need separate verification.

---

# X2D II 子菜单条目可见性：行过滤契约

范围：Hasselblad X2D II 100C，固件 1.1.9.2、1.3.16.2、1.3.18.1。以下为读者自备
原厂 `camera-gui` 的静态分析，另含一项单独标注的实机观察。原厂固件与提取的 QML
不随库分发。除注明外地址对应 1.3.18.1，不作为外部调用接口或安装步骤。第一代机型
有各自的菜单单元，本文地址与偏移均不适用。

输入身份（本方自行提取，`camera-gui` 的 SHA-256）：

| 固件 | SHA-256 |
| --- | --- |
| 1.1.9.2 | `41f85a203934d14011bcc1bf58f7282eae6f0c6b54a176872ab2edc2324f042a` |
| 1.3.16.2 | `b1b643cb36176cd5a49129dd9bb2be480aa045a96ed1c35c30a779ab5af0801b` |
| 1.3.18.1 | `ea2cf8a5f6209f301971f55dd1ef86882c09db04b2e60371d2a243b79f1d8098` |

## 与本库现有菜单研究的关系

本库已有的菜单研究面向第一代机型的顶层 `MainScreen` 网格与 `FavoriteModel`。本文
是另一个模型、另一个机型：X2D II **子菜单页内部**的条目，由 `SubMenuModel` 提供
数据、`FilteredSubMenuModel` 过滤。第十二格分析绕开 `menuFile`，不经过本过滤器，
本文不改变其结论。本文只回答一个更窄的问题：子菜单页打开之后，一行要满足什么条件
才会被绘制。

## 菜单树在 C++ 静态初始化阶段构建

承载它的构造函数共 17 个符号：`MenuItem` 基类构造函数，加 16 个子类构造函数，覆盖
14 种元素类型（`DropDown` 与 `ValueSwitch` 各有两个重载）。每一个都以
`GuiTypes::E_MenuAvail` 和一个 `bool` 作为构造参数，且 `MenuItem` 对两者都没有
setter，因此构造点就是两道门的完整账目。

以下计数来自按符号名定位构造函数、逐个仿真定义函数的扫描（见复现一节）：

| 固件 | 定义函数 | 条目 | 带 demo 标记 |
| --- | ---: | ---: | ---: |
| 1.1.9.2 | 20 | 550 | 45 |
| 1.3.16.2 | 20 | 553 | 45 |
| 1.3.18.1 | 20 | 553 | 45 |

上述总数是整个二进制的。一份 `camera-gui` 服务多于一种机型配置，20 个定义函数中有
三个是按配置划分的单元。X2D II 自己的单元为 `_GLOBAL__sub_I_menux2d.cpp`，
**111 条，其中 14 条带 demo 标记**，三个固件版本完全一致。另外两种配置不在本库既定
范围内，本文不作描述。

`MenuItem` 基类构造函数位于 `0x1732e38`。反修饰后的符号直接给出参数顺序，该 `bool`
位于 `E_Proxy` 与 `E_MenuRW` 之间。对象布局，`sizeof(MenuItem) == 0x130`：

| 偏移 | 字段 |
| ---: | --- |
| `0x00` | `E_MenuElem` |
| `0x08` / `0x10` / `0x18` | id `QString`（char16 数据指针在 `0x10`） |
| `0xf8` | `E_Proxy` |
| `0xfc` | demo `bool`，以 `and w10, w7, 1` 后 `strb w10, [x0, 0xfc]` 写入 |
| `0x100` | `E_MenuRW` |
| `0x104` | `E_MenuAvail` |
| `0x114` | `E_MenuOption` |

换版本时请从基类构造函数重新推导这些偏移，不要沿用：三个枚举参数经栈传入，依次写入
`0x100`、`0x104`、`0x114`。

## 角色编号

`SubMenuModel::data(QModelIndex const&, int) const` 位于 `0x172ea60`。其分派为
`sub w8, role, 0x100` 后 `cmp w8, 0xd`，即接受 14 个角色取值，`0x100` 至 `0x10d`。

名称与取值是读出的，不是推断的。面向 QML 的接口类 `SubmenuModelIf` 注册为 QML
元素，其元对象中带有 `Roles` 枚举。解码 `qt_meta_data_ZN14SubmenuModelIfE`
（`0x256d060`）中的枚举键值对，再把每个键的字符串索引对照
`qt_meta_stringdata_ZN14SubmenuModelIfE`（`0x256fe74`）解析，可得完整表格，14 个键
且无空缺：

| 取值 | 名称 | 取值 | 名称 |
| ---: | --- | ---: | --- |
| `0x100` | `ElemRole` | `0x107` | `ValidRole` |
| `0x101` | `NameRole` | `0x108` | `OptionsRole` |
| `0x102` | `Text1Role` | `0x109` | `DemoRole` |
| `0x103` | `Text2Role` | `0x10a` | `SectionNameRole` |
| `0x104` | `DescriptionRole` | `0x10b` | `PropValueRole` |
| `0x105` | `ProxyRole` | `0x10c` | `ItemValuesRole` |
| `0x106` | `EnabledRole` | `0x10d` | `SubLevelRole` |

其中三个与 `SubMenuModel::data` 各分支实际读取的内容互相印证，这也是把该接口枚举
与本实现绑定起来的依据：

| 角色 | 该分支读取什么 |
| --- | --- |
| `0x100` `ElemRole` | 成员 `0x00`，即 `E_MenuElem` |
| `0x107` `ValidRole` | 成员 `0x104`，随后调用 `0x1722520` 的 `Menu::conditionValid(GuiTypes::E_MenuAvail)` |
| `0x109` `DemoRole` | 成员 `0xfc` |

`SubMenuModel::data` 是唯一读取 `0xfc` 的菜单函数。

一条方法提示，因为写本文时我们在相反方向上犯过一次错：`rabin2 -s` 与 radare2 的
字符串索引都不会呈现这些名称，因为它们位于元对象字符串块内部，以 NUL 分隔，既不是
符号也不是被索引的字符串。原始字节搜索可以找到。用 `is` 或 `iz` 找不到这类名称，
不能作为其不存在的证据。

## 过滤器

`FilteredSubMenuModel::filterAcceptsRow(int, QModelIndex const&) const` 位于
`0x171f010`，长 392 字节。它经 `GuiObjectImpl::instance()` 读取 `0x10cfaa8` 的
`GuiObject::demo_mode()`，再读上表两个角色，然后计算：

```
demoMode = GuiObject::demo_mode()
isDemo   = data(index, 0x109).toBool()
elem     = data(index, 0x100).toInt()

if ((elem & ~1) == 12)              return false
if (!data(index, 0x107).toBool())   return false
return demoMode || !isDemo
```

第一项判断为 `and w8, w21, 0xfffffffe` 后 `cmp w8, 0xc`，即把 `E_MenuElem` 12 与
13 一并拒绝。由构造点确认的 `E_MenuElem` 取值有四个：`Switch` 4、`StorageInfo` 11、
`SubHeader` 12、`Separator` 13。其余取值未读取。

### 三项推论

**1. 标题与分隔线从来不是行。** 它们在任何门之前就被拒绝，因此以 `SubHeader` 形式
加入的条目无论其他字段如何设置都不会作为行出现。标题改由分节机制承载：
`SectionNameRole`（`0x10a`）就是本模型自己的一个角色，二进制中另有
`isSectionFirstInList`、`separatorTopPadding`、`separatorBottomPadding` 以及 Qt 的
`QQuickViewSection`。拒绝这一项由反汇编证明；分节路由则是按上述名称读出的，未逐个
调用追踪。

**2. 两道互相独立的门，一行必须同时通过。** 一道是经 `Menu::conditionValid` 的
`E_MenuAvail`，另一道是每条自己的 demo `bool` 与唯一的全局 `demo_mode` 比对。宽松
默认值为 `E_MenuAvail_None` 与 `false`。

**3. 行全部被过滤掉的分节不产生任何输出。** 既然标题不是行，就没有行可供视图挂接
分节，于是行和标题都不出现。这句话的两半证据等级不同：前半是静态分析，后半是静态
分析，并有一项**实机观察**与之一致：在一台零售 X2D II、1.3.18.1 上，本文读法所指
的、其下各行均不通过的标题分组位置，机主看到的是完全没有显示，也不留空标题。该观察
是对静态读法的印证，而不是对分节行为的独立证明，因为它以该读法对此处已定义条目的
判断为前提。一台相机、一个固件版本、一个菜单页。取得该观察未改动任何相机设置，也未
安装任何东西。

## demo 这条轴

每个构造函数都接收的那个 `bool` 是第二条可见性轴，与 `E_MenuAvail` 互相独立，而且是
两层中较大的一层：整个二进制 45 条，X2D II 单元内 14 条。

`demo_mode` 本身是持久化的 `GuiSettings` 属性，其生成形态与
[MCU 摇杆输入链](../../joystick-eight-way/research/INPUT-PATH.md)中的
`diagonal_joystick_enabled` 相同：`GuiSettings::demo_mode() const`、
`GuiSettings::setDemo_mode(bool, bool)`、`resetDemo_mode`、changed 信号，以及一个
`demo_mode` 设置键。出厂为 false。

开发者相关条目中确实存在一个设置键为 `demo_mode` 的 `Switch`，其 `E_MenuAvail` 为
`None`，可用性上没有门。但它自己的 demo `bool` 为 1，按上述过滤器，只有在 demo 模式
已经开启时它才可见。因此界面上不存在开启它的路径。本文把这一点作为限制写出，不描述
其他路径。

另记一条死路，以免他人重走：GUI 资源中存在 `DemoMarker.qml` 组件，是一个半透明覆盖
层，其源码自述用于标记尚未完成的项目。出厂资源中没有任何地方实例化它，对其
`showMarker` 属性的引用只有声明与自身绑定两处。真正起作用的机制是上面的行过滤器，
不是该组件。

## 复现

固件不随库提供。准备好上表某个版本中提取的 `camera-gui` 后，在仓库根目录执行：

```
rabin2 -s camera-gui > syms.txt
grep -E '_ZN8MenuItemC2E|_ZN6ButtonC2E|_ZN9SubHeaderC2E' syms.txt
r2 -q -e scr.color=0 -c 'is~filterAcceptsRow' camera-gui
r2 -q -e scr.color=0 -c 'af @ 0x171f010; pdf @ 0x171f010' camera-gui
r2 -q -e scr.color=0 -c 'af @ 0x172ea60; pdf @ 0x172ea60' camera-gui
```

按符号名定位构造函数，可以不在版本之间携带地址表。对象布局由基类构造函数得出，可
接受的角色取值范围由 `SubMenuModel::data` 的跳转表得出，角色名称与取值则由
`SubmenuModelIf` 的元对象得出：把 `qt_meta_data_ZN14SubmenuModelIfE` 中的枚举键值
对按小端 `uint32` 读出，再用 `qt_meta_stringdata_ZN14SubmenuModelIfE` 的
`{offset, size}` 头部解析每个键的字符串索引。

三个坑，都曾让我们付出时间：

- 对多数此类构造函数，`E_MenuAvail` 是最后一个**寄存器**参数；但对按值接收
  `QVariant` 的 `DropDown` 重载，它落在**栈**上，因为该 `QVariant` 以隐藏指针占用
  了一个寄存器。该重载的 `bool` 在 `w6`。
- 由于相同代码折叠，上述若干地址挂有多个符号。请按符号名解析，不要仅凭地址。
- 被编译器内联的构造函数对调用点扫描不可见，而本二进制中至少存在一条内联的菜单
  条目。因此上表条目总数是下界，不是已证明的总量。过滤契约本身不依赖这些计数。

产生这些计数的扫描器会报告定位到的构造函数数量与未能解析的调用点数量；本文数字取自
三个固件版本上两项均干净的运行。该扫描器不包含在本次改动中，如需要可作为后续提交
放入 `x2d2/tools/`。

## 对本库已公布数据的独立核对

以下核对基于本方自行提取的原厂文件，而非本库的副本：

- `camera-gui` 1.3.18.1 的 SHA-256 与
  [MCU 摇杆输入链](../../joystick-eight-way/research/INPUT-PATH.md)中公布的哈希
  逐字节一致，`exMCU_hb722.cont`
  （`f4ffdae8350d7a7f536940f8965f26e24a9d6bfe6337dc8a031b9a81bbb64d11`）同样一致。
- 该文引用的三个地址在本方副本中都解析到其所命名的符号：`0x10c9508`
  `GuiSettings::diagonal_joystick_enabled() const`、`0x17741b8`
  `JoystickInput::onJoystickEvent(JoystickInput::E_JoystickDirection)`、
  `0x1694e80`
  `CommonConstants::stepFocusPoint(QPointF, QSizeF, HblmTypes::E_CropMode, int, int) const`。
  其中 `0x10c9508` 在本方副本中挂有多个符号，请按名称解析。
- 本方以不同方法做的 1.3.16.2 → 1.3.18.1 比较，同样没有找到可归因于后屏弱光改善
  说明的变化，与[exMCU 两版比较](../exmcu/VERSION-COMPARISON.md)的结论一致。该文
  关于 MCU 显示符号按 sub/top 屏命名的提醒，也纠正了本方此前对自己一项观察的读法。

## 证据边界

除上面单独标注的实机观察外，全文均为原厂二进制的静态分析。未改动相机、未写入固件，
文中也不包含任何持久化、安装或写入路径。读出过滤器并不等于证明某一行可以被添加、
其后端存在，或通过过滤的行同时可选：菜单可见、选项可选与后端有效是三个问题，必须
分别验证。
