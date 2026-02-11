# Phone Agent v2.0.0 - OpenClaw 手机控制代理

**精简版**：只保留通用接口，支持 termux-api v0.53+

## 架构

```
OpenClaw (Skill)
    ↓ JSON
Phone Agent
    ↓
termux-api / ADB
```

## 安装

```bash
# 手机 Termux 中
pkg install python git
pip install flask requests

git clone https://github.com/openclaw-glasses/phone-agent.git
cd phone-agent

python phone_agent.py
```

## 通用接口

### termux-api

```bash
POST /api/termux
{
  "command": "termux-sms-list",
  "args": ["-l", "10"]
}
```

返回：
```json
{
  "success": true,
  "stdout": "[{...}]",
  "parsed": [{...}],
  "command": "termux-sms-list -l 10"
}
```

### ADB

```bash
POST /api/adb
{
  "subcommand": "input",
  "args": ["tap", "500", "500"]
}
```

## 快捷 ADB

| 接口 | 功能 |
|------|------|
| `POST /api/adb/tap` | 点击 `{x, y}` |
| `POST /api/adb/swipe` | 滑动 `{x1, y1, x2, y2, duration}` |
| `POST /api/adb/input` | 输入 `{text}` |
| `POST /api/adb/key` | 按键 `{key}` |
| `GET /api/adb/screenshot` | 截图 |
| `GET /api/adb/dump` | UI 层级 |
| `POST /api/adb/start` | 启动 App `{package, activity}` |

## 更新

```bash
# 检查更新
GET /api/update/check

# 手动更新
POST /api/update

# 自动升级（推荐）
POST /api/update/auto

# 重启
POST /api/restart
```

## 配合 OpenClaw Skill 使用

```json
{
  "type": "http",
  "name": "phone",
  "url": "http://<手机IP>:8080"
}
```

详见 Skill：`phone-agent-skill`

## 版本历史

### v2.0.0 (2026-02-11)
- ✅ 精简版，只保留通用接口
- ✅ 支持 termux-api v0.53+
- ✅ 支持所有 ADB 命令
- ✅ 自动升级功能
- ✅ 优雅重启

### v1.x.x
- 旧版本，固定 API 过多
