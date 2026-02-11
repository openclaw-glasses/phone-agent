# Phone Agent - OpenClaw 手机控制代理
# 让 OpenClaw 通过 HTTP 控制 Android 手机

## 功能

- 🔌 termux-api 集成（短信、位置、相机、电池）
- 🖱️ ADB 控制（点击、滑动、输入）
- 🔄 Git 自动更新
- 📡 HTTP Server（供 OpenClaw 调用）
- 🤖 AutoJS 集成（UI 自动化）

## 安装

```bash
# 手机 Termux 中
pkg install python git
pip install flask requests

# 克隆项目
git clone https://github.com/openclaw-glasses/phone-agent.git
cd phone-agent
```

## 配置

编辑 `config.json`：

```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 8080
  },
  "adb": {
    "enabled": true,
    "wireless_ip": "192.168.1.100:5555"
  },
  "autojs": {
    "enabled": false,
    "url": "http://127.0.0.1:8088"
  },
  "openclaw": {
    "gateway_url": "http://192.168.1.4:18789"
  }
}
```

## 运行

```bash
python phone_agent.py
```

## API 接口

### 系统信息

```
GET /api/status          - 设备状态
GET /api/battery         - 电池信息
GET /api/cpu             - CPU 信息
```

### termux-api

```
GET /api/sms/list        - 列出短信
POST /api/sms/send       - 发送短信
GET /api/location        - 获取位置
GET /api/camera/photo    - 拍照
```

### ADB 控制

```
POST /api/adb/tap        - 点击 (x, y)
POST /api/adb/swipe      - 滑动 (x1, y1, x2, y2)
POST /api/adb/input      - 输入文字
POST /api/adb/key        - 按键
GET /api/adb/screenshot  - 截图
```

### AutoJS

```
POST /api/autojs/exec    - 执行脚本
GET /api/autojs/nodes    - 获取 UI 节点
```

### Git 更新

```
POST /api/update         - 更新代码
GET /api/version         - 版本信息
```

## OpenClaw 集成

在 OpenClaw 中添加 HTTP Agent：

```json
{
  "type": "http",
  "name": "phone",
  "url": "http://<手机IP>:8080"
}
```

## 自动启动

添加到 Termux 开机自启：

```bash
# 创建启动脚本
echo "cd ~/phone-agent && python phone_agent.py" > ~/.termux/boot
chmod +x ~/.termux/boot
```

## 更新日志

### v1.0.0 (2026-02-11)
- 初始版本
- termux-api 集成
- ADB 控制
- HTTP Server
- Git 自动更新

## License

MIT
