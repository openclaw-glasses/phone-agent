# Phone Agent v1.0.1 - OpenClaw 手机控制代理

让 OpenClaw 通过 HTTP 控制 Android 手机，**完整支持 30+ termux-api 功能**。

## 功能

### 🔌 termux-api 完整支持 (25+)

| 类别 | 功能 | API |
|------|------|-----|
| **短信** | 列出/发送短信 | `/api/sms/list`, `/api/sms/send` |
| **位置** | GPS/网络定位 | `/api/location` |
| **相机** | 拍照 | `/api/camera/photo` |
| **剪贴板** | 读取/写入 | `/api/clipboard/get`, `/api/clipboard/set` |
| **联系人** | 获取联系人 | `/api/contacts` |
| **通知** | 发送/移除通知 | `/api/notification`, `/api/notification/remove` |
| **传感器** | 加速度/陀螺仪等 | `/api/sensor` |
| **录音** | 录制音频 | `/api/micrecord` |
| **语音合成** | TTS 朗读 | `/api/tts` |
| **语音识别** | 语音转文字 | `/api/speech` |
| **通话** | 拨打电话 | `/api/telephony/call` |
| **WiFi** | 连接/扫描信息 | `/api/wifi/connection`, `/api/wifi/scan` |
| **指纹** | 指纹验证 | `/api/fingerprint` |
| **振动** | 控制振动 | `/api/vibrate` |
| **Toast** | 显示提示 | `/api/toast` |
| **对话框** | 各种对话框 | `/api/dialog` |
| **下载** | 下载文件 | `/api/download` |
| **分享** | 分享文件 | `/api/share` |
| **存储** | 文件选择 | `/api/storage` |
| **红外** | 发射红外 | `/api/infrared/transmit` |
| **媒体** | 播放/扫描 | `/api/media/play`, `/api/media/scan` |
| **设备信息** | CPU/内存等 | `/api/device`, `/api/cpu`, `/api/battery` |

### 🖱️ ADB 控制

| 功能 | API |
|------|-----|
| 点击坐标 | `POST /api/adb/tap` |
| 滑动 | `POST /api/adb/swipe` |
| 输入文字 | `POST /api/adb/input` |
| 按键 | `POST /api/adb/key` |
| 截图 | `GET /api/adb/screenshot` |
| UI 层级 | `GET /api/adb/dump` |

### 🤖 AutoJS 集成（视觉反馈）

```javascript
// 获取页面所有 UI 节点
GET /api/autojs/nodes

// 返回格式
{
  "success": true,
  "timestamp": "2026-02-11T15:00:00",
  "nodes_count": 50,
  "nodes": [
    {
      "class": "android.widget.EditText",
      "text": "",
      "content-desc": "搜索",
      "clickable": "true",
      "bounds": {"x1": "100", "y1": "200", "x2": "500", "y2": "300"}
    }
  ]
}
```

### 🔄 Git 自动更新

```bash
# 手动更新
POST /api/update

# 查看版本
GET /api/version
```

## 安装

```bash
# 手机 Termux 中
pkg install python git
pip install flask requests

# 克隆项目
git clone https://github.com/openclaw-glasses/phone-agent.git
cd phone-agent

# 运行
python phone_agent.py
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
  "update_interval": 3600
}
```

## 🔄 自动升级

### 检查更新

```bash
GET /api/update/check
```

返回：
```json
{
  "current_version": "v1.0.1",
  "latest_version": "v1.0.2",
  "update_available": true,
  "changelog_url": "https://github.com/openclaw-glasses/phone-agent/commits/main"
}
```

### 手动更新

```bash
POST /api/update
# Git pull 方式
```

### 自动升级

```bash
POST /api/update/auto
# 下载最新版本ZIP并自动替换
```

### 定时检查

```json
POST /api/update/schedule
{
  "interval": 3600,      // 检查间隔（秒）
  "auto_upgrade": false  // 是否自动升级
}
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

使用示例：

```json
{
  "agentId": "phone",
  "message": "获取电池状态"
}
```

## 示例：控制小红书

```bash
# 1. 打开小红书
adb shell am start -n com.xiaoshoudianping/.MainActivity

# 2. 获取 UI 节点
GET /api/adb/dump

# 3. 分析节点，找到搜索框
# 4. 点击搜索框
POST /api/adb/tap
{"x": 300, "y": 250}

# 5. 输入搜索内容
POST /api/adb/input
{"text": "美妆教程"}
```

## 自动启动

添加到 Termux 开机自启：

```bash
mkdir -p ~/.termux/boot
echo "cd ~/phone-agent && python phone_agent.py" > ~/.termux/boot/start.sh
chmod +x ~/.termux/boot/start.sh
```

## 更新日志

### v1.0.1 (2026-02-11)
- ✅ 完整支持 25+ termux-api 命令
- ✅ ADB 控制增强
- ✅ AutoJS 视觉反馈（UI 节点获取）
- ✅ UI 层级 XML 解析为 JSON
- ✅ 唤醒锁支持
- ✅ 文件操作 API
- ✅ **自动升级功能**（检查更新、Git pull、自动下载升级）

### v1.0.0 (2026-02-11)
- 初始版本
- 基础 termux-api
- ADB 控制
- HTTP Server

## License

MIT
