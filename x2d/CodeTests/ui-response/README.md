# UI 轨迹离线分析检查

属于第一代 X2D 的界面响应研究；数值报告绑定固件 4.2.0 build24849，解析器只处理显式本地文本。

[标准库测试](test_analyze_ui_trace.py)验证触摸间隔统计保留抬手空隙、时间回退与重复时间戳；CPU 只按 uptime 与同 PID/启动时刻计算，拒绝进程重启、tick 回退和重复采样；未指定 USER_HZ 不输出 CPU 百分比；保存原厂 Weston 每个统计窗口，不把空闲窗口丢弃或当成操作期均值；结果不回显任意原始行。

从仓库根目录运行：

```sh
python3 -m unittest discover -s x2d/CodeTests/ui-response -p 'test_*.py'
python3 x2d/tools/analyze_ui_trace.py /path/to/saved-trace.txt --clock-ticks 100
```

依赖 Python 3.9+；测试输入完全合成。工具读本地文件，默认 stdout 输出聚合 JSON，可用 `--output` 显式写文件；不连接设备、不执行 shell、不下载。输入应只包含一个触摸事件源，proc 记录前有对应的 `/proc/uptime` 两列采样，使用 getevent 符号输出中的 EV_SYN SYN_REPORT。95 分位采用 nearest-rank；跨时钟不做关联。

本次五项测试通过，原先保留在本地的 20 秒采样重新分析得到 2371 个报告、6.952 ms 中位间隔、31 个大于 40 ms 的空隙、GUI 单核约 34.6–37.7%、GPU 4–5%，与[报告](../../research/4.2.0/UI-RESPONSIVENESS.md)一致。原始设备记录不分发。事件间隔、CPU 平均值及 FPS 不能给出触摸到发光延迟。
