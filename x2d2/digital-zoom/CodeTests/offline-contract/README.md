# 数字裁切离线契约检查

本目录验证 X2D II 数字裁切候选的纯几何、控制器生命周期、C/Python 一致性、QML 安全默认值和只读字符串扫描。测试只使用合成输入，不读取固件、不连接相机、不生成安装包。

从仓库根目录运行：

```sh
python3 -B -m unittest discover -s x2d2/digital-zoom/CodeTests/offline-contract -p 'test_*.py'
```

`test_native_parity.py` 在临时目录调用主机 `cc`；没有编译器时只跳过该组。编译结果不会写入仓库。通过表示桌面端算法与接口契约一致，不表示 X2D II 预览、拍摄、RAW 或更新流程已经实机验证。
