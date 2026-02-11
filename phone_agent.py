#!/usr/bin/env python3
"""
Phone Agent - OpenClaw 手机控制代理
功能：让 OpenClaw 通过 HTTP 控制 Android 手机
版本：v1.0.1 - 完整支持 termux-api + ADB + AutoJS
"""

import os
import sys
import json
import time
import subprocess
import threading
import base64
from datetime import datetime
from flask import Flask, request, jsonify, send_file
import requests

app = Flask(__name__)

# 配置
CONFIG_FILE = "config.json"

def load_config():
    """加载配置"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {
        "server": {"host": "0.0.0.0", "port": 8080},
        "adb": {"enabled": True, "wireless_ip": None},
        "autojs": {"enabled": False, "url": "http://127.0.0.1:8088"},
        "update_interval": None
    }

def save_config(config):
    """保存配置"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def run_cmd(cmd, timeout=10):
    """运行命令并返回结果"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return {"success": True, "stdout": result.stdout, "stderr": result.stderr}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Timeout"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def adb_cmd(cmd):
    """执行 ADB 命令"""
    config = load_config()
    adb_prefix = "adb "
    
    if config['adb']['wireless_ip']:
        adb_prefix = f"adb -s {config['adb']['wireless_ip']} "
    
    return run_cmd(f"{adb_prefix}{cmd}")

# ==================== API 端点 ====================

@app.route('/')
def index():
    return jsonify({
        "name": "Phone Agent",
        "version": "2.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "system": ["/api/status", "/api/battery", "/api/cpu", "/api/device"],
            "termux_api": [
                "/api/sms/list", "/api/sms/send",
                "/api/location",
                "/api/camera/photo",
                "/api/clipboard/get", "/api/clipboard/set",
                "/api/contacts",
                "/api/notification",
                "/api/sensor", "/api/micrecord",
                "/api/tts", "/api/speech",
                "/api/telephony/call",
                "/api/wifi/connection", "/api/wifi/scan",
                "/api/fingerprint", "/api/vibrate", "/api/toast",
                "/api/dialog", "/api/download", "/api/share",
                "/api/storage", "/api/infrared"
            ],
            "adb": ["/api/adb/tap", "/api/adb/swipe", "/api/adb/input", 
                    "/api/adb/key", "/api/adb/screenshot", "/api/adb/dump"],
            "autojs": ["/api/autojs/exec", "/api/autojs/nodes"],
            "tools": ["/api/wake-lock", "/api/file"],
            "update": ["/api/update", "/api/version"]
        }
    })

@app.route('/api/status')
def api_status():
    """设备状态"""
    return jsonify({
        "status": "online",
        "timestamp": datetime.now().isoformat(),
        "uptime": time.time(),
        "version": "2.0.0"
    })

@app.route('/api/version')
def api_version():
    """版本信息"""
    return jsonify({
        "version": "2.0.0",
        "last_update": datetime.now().isoformat()
    })

# ==================== 系统信息 ====================

@app.route('/api/battery')
def api_battery():
    """电池信息"""
    result = run_cmd("termux-battery-status")
    if result['success']:
        try:
            return jsonify(json.loads(result['stdout']))
        except:
            return jsonify({"raw": result['stdout']})
    return jsonify({"error": result['error']})

@app.route('/api/cpu')
def api_cpu():
    """CPU 信息"""
    result = run_cmd("cat /proc/cpuinfo | head -10")
    return jsonify({"cpu_info": result['stdout']})

@app.route('/api/device')
def api_device():
    """设备信息"""
    results = {
        "android_version": run_cmd("getprop ro.build.version.release"),
        "device_model": run_cmd("getprop ro.product.model"),
        "manufacturer": run_cmd("getprop ro.product.manufacturer"),
        "imei": run_cmd("termux-telephony-deviceinfo | grep imei"),
    }
    return jsonify(results)

# ==================== termux-api 完整支持 ====================

# --- 短信 ---
@app.route('/api/sms/list')
def api_sms_list():
    """列出短信"""
    result = run_cmd("termux-sms-list")
    if result['success']:
        try:
            return jsonify(json.loads(result['stdout']))
        except:
            return jsonify([])
    return jsonify({"error": result['error']})

@app.route('/api/sms/send', methods=['POST'])
def api_sms_send():
    """发送短信"""
    data = request.json or {}
    number = data.get('number', '')
    message = data.get('message', '')
    
    result = run_cmd(f'termux-sms-send -n "{number}" "{message}"')
    return jsonify(result)

# --- 位置 ---
@app.route('/api/location')
def api_location():
    """获取位置"""
    provider = request.args.get('provider', 'gps')  # gps, network, passive
    result = run_cmd(f"termux-location -p {provider}")
    if result['success']:
        try:
            return jsonify(json.loads(result['stdout']))
        except:
            return jsonify({"raw": result['stdout']})
    return jsonify({"error": result['error']})

# --- 相机 ---
@app.route('/api/camera/photo')
def api_camera_photo():
    """拍照"""
    camera = request.args.get('camera', '0')
    output = f"/sdcard/photo_{int(time.time())}.jpg"
    result = run_cmd(f"termux-camera-photo -c {camera} {output}")
    
    return jsonify({
        "success": result['success'],
        "path": output,
        "error": result.get('error')
    })

# --- 剪贴板 ---
@app.route('/api/clipboard/get')
def api_clipboard_get():
    """获取剪贴板"""
    result = run_cmd("termux-clipboard-get")
    return jsonify({"clipboard": result['stdout'].strip()})

@app.route('/api/clipboard/set', methods=['POST'])
def api_clipboard_set():
    """设置剪贴板"""
    data = request.json or {}
    text = data.get('text', '')
    result = run_cmd(f'termux-clipboard-set "{text}"')
    return jsonify(result)

# --- 联系人 ---
@app.route('/api/contacts')
def api_contacts():
    """联系人列表"""
    result = run_cmd("termux-contact-list")
    if result['success']:
        try:
            return jsonify(json.loads(result['stdout']))
        except:
            return jsonify([])
    return jsonify({"error": result['error']})

# --- 通知 ---
@app.route('/api/notification', methods=['POST'])
def api_notification():
    """发送通知"""
    data = request.json or {}
    title = data.get('title', 'Phone Agent')
    content = data.get('content', '')
    priority = data.get('priority', 'default')
    
    result = run_cmd(f'termux-notification -t "{title}" -c "{content}" --priority {priority}')
    return jsonify(result)

@app.route('/api/notification/remove', methods=['POST'])
def api_notification_remove():
    """移除通知"""
    data = request.json or {}
    notif_id = data.get('id', '')
    result = run_cmd(f"termux-notification-remove {notif_id}")
    return jsonify(result)

# --- 传感器 ---
@app.route('/api/sensor')
def api_sensor():
    """获取传感器数据"""
    sensor = request.args.get('sensor', 'all')
    result = run_cmd(f"termux-sensor -s {sensor}")
    if result['success']:
        try:
            return jsonify(json.loads(result['stdout']))
        except:
            return jsonify({"raw": result['stdout']})
    return jsonify({"error": result['error']})

# --- 录音 ---
@app.route('/api/micrecord', methods=['POST'])
def api_micrecord():
    """开始录音"""
    data = request.json or {}
    duration = data.get('duration', 5)  # 秒
    output = data.get('output', f"/sdcard/recording_{int(time.time())}.3gp")
    
    result = run_cmd(f"termux-micrecord -d {duration} -o {output}")
    return jsonify({"success": result['success'], "path": output})

# --- 语音合成 (TTS) ---
@app.route('/api/tts', methods=['POST'])
def api_tts():
    """文字转语音"""
    data = request.json or {}
    text = data.get('text', '')
    lang = data.get('lang', 'en')
    
    result = run_cmd(f'termux-tts-speak -l {lang} "{text}"')
    return jsonify(result)

# --- 语音识别 ---
@app.route('/api/speech')
def api_speech():
    """语音转文字"""
    result = run_cmd("termux-speech-to-text")
    if result['success']:
        return jsonify({"text": result['stdout'].strip()})
    return jsonify({"error": result['error']})

# --- 通话 ---
@app.route('/api/telephony/call', methods=['POST'])
def api_telephony_call():
    """拨打电话"""
    data = request.json or {}
    number = data.get('number', '')
    result = run_cmd(f"termux-telephony-call {number}")
    return jsonify(result)

@app.route('/api/telephony/deviceinfo')
def api_telephony_info():
    """设备信息"""
    result = run_cmd("termux-telephony-deviceinfo")
    if result['success']:
        try:
            return jsonify(json.loads(result['stdout']))
        except:
            return jsonify({"raw": result['stdout']})
    return jsonify({"error": result['error']})

# --- WiFi ---
@app.route('/api/wifi/connection')
def api_wifi_connection():
    """WiFi 连接信息"""
    result = run_cmd("termux-wifi-connectioninfo")
    if result['success']:
        try:
            return jsonify(json.loads(result['stdout']))
        except:
            return jsonify({"raw": result['stdout']})
    return jsonify({"error": result['error']})

@app.route('/api/wifi/scan')
def api_wifi_scan():
    """WiFi 扫描结果"""
    result = run_cmd("termux-wifi-scaninfo")
    if result['success']:
        try:
            return jsonify(json.loads(result['stdout']))
        except:
            return jsonify([])
    return jsonify({"error": result['error']})

# --- 指纹 ---
@app.route('/api/fingerprint')
def api_fingerprint():
    """指纹验证"""
    result = run_cmd("termux-fingerprint")
    if result['success']:
        try:
            return jsonify(json.loads(result['stdout']))
        except:
            return jsonify({"raw": result['stdout']})
    return jsonify({"error": result['error']})

# --- 振动 ---
@app.route('/api/vibrate', methods=['POST'])
def api_vibrate():
    """振动"""
    data = request.json or {}
    duration = data.get('duration', 100)  # 毫秒
    result = run_cmd(f"termux-vibrate -d {duration}")
    return jsonify(result)

# --- Toast ---
@app.route('/api/toast', methods=['POST'])
def api_toast():
    """显示 Toast"""
    data = request.json or {}
    text = data.get('text', '')
    gravity = data.get('gravity', 'short')  # short, long
    result = run_cmd(f'termux-toast -g {gravity} "{text}"')
    return jsonify(result)

# --- 对话框 ---
@app.route('/api/dialog', methods=['POST'])
def api_dialog():
    """显示对话框"""
    data = request.json or {}
    dialog_type = data.get('type', 'input')  # input, confirm, checkbox, radio, sheet
    title = data.get('title', 'Dialog')
    text = data.get('text', '')
    
    cmd = f'termux-dialog -t "{title}"'
    if text:
        cmd += f' -i "{text}"'
    cmd += f' -d {dialog_type}'
    
    result = run_cmd(cmd)
    return jsonify(result)

# --- 下载 ---
@app.route('/api/download', methods=['POST'])
def api_download():
    """下载文件"""
    data = request.json or {}
    url = data.get('url', '')
    title = data.get('title', 'Download')
    result = run_cmd(f'termux-download -t "{title}" "{url}"')
    return jsonify(result)

# --- 分享 ---
@app.route('/api/share', methods=['POST'])
def api_share():
    """分享文件/文本"""
    data = request.json or {}
    file = data.get('file', '')
    text = data.get('text', '')
    
    cmd = "termux-share"
    if file:
        cmd += f' -f "{file}"'
    if text:
        cmd += f' -t "{text}"'
    
    result = run_cmd(cmd)
    return jsonify(result)

# --- 存储 ---
@app.route('/api/storage', methods=['POST'])
def api_storage():
    """获取存储文件"""
    data = request.json or {}
    action = data.get('action', 'get')  # get, create
    title = data.get('title', 'Select file')
    
    result = run_cmd(f"termux-storage-{action} -t '{title}'")
    return jsonify({"path": result['stdout'].strip()})

# --- 红外 ---
@app.route('/api/infrared/frequencies')
def api_ir_frequencies():
    """红外频率"""
    result = run_cmd("termux-infrared-frequencies")
    return jsonify({"frequencies": result['stdout']})

@app.route('/api/infrared/transmit', methods=['POST'])
def api_ir_transmit():
    """发射红外"""
    data = request.json or {}
    frequency = data.get('frequency', '38000')
    pattern = data.get('pattern', '')
    
    result = run_cmd(f'termux-infrared-transmit -f {frequency} -p "{pattern}"')
    return jsonify(result)

# ==================== 官方完整命令支持 ====================

# --- 手电筒 ---
@app.route('/api/torch', methods=['POST', 'DELETE'])
def api_torch():
    """手电筒"""
    action = "on" if request.method == "POST" else "off"
    result = run_cmd(f"termux-torch {action}")
    return jsonify(result)

# --- 壁纸 ---
@app.route('/api/wallpaper', methods=['POST'])
def api_wallpaper():
    """设置壁纸"""
    data = request.json or {}
    file = data.get('file', '')
    result = run_cmd(f'termux-wallpaper -f "{file}"')
    return jsonify(result)

# --- TTS 引擎 ---
@app.route('/api/tts/engines')
def api_tts_engines():
    """TTS 引擎列表"""
    result = run_cmd("termux-tts-engines")
    return jsonify({"engines": result['stdout']})

# --- 通话记录 ---
@app.route('/api/call/log')
def api_call_log():
    """通话记录"""
    result = run_cmd("termux-call-log")
    if result['success']:
        try:
            return jsonify(json.loads(result['stdout']))
        except:
            return jsonify({"raw": result['stdout']})
    return jsonify({"error": result['error']})

# --- 亮度 ---
@app.route('/api/brightness', methods=['POST'])
def api_brightness():
    """设置亮度"""
    data = request.json or {}
    level = data.get('level', 50)  # 0-255
    result = run_cmd(f"termux-brightness {level}")
    return jsonify(result)

# --- 音频信息 ---
@app.route('/api/audio/info')
def api_audio_info():
    """音频信息"""
    result = run_cmd("termux-audio-info")
    if result['success']:
        try:
            return jsonify(json.loads(result['stdout']))
        except:
            return jsonify({"raw": result['stdout']})
    return jsonify({"error": result['error']})

# --- NFC ---
@app.route('/api/nfc')
def api_nfc():
    """NFC 状态"""
    result = run_cmd("termux-nfc")
    return jsonify({"nfc": result['stdout'].strip()})

# --- 通知列表 ---
@app.route('/api/notification/list')
def api_notification_list():
    """通知列表"""
    result = run_cmd("termux-notification-list")
    if result['success']:
        try:
            return jsonify(json.loads(result['stdout']))
        except:
            return jsonify([])
    return jsonify({"error": result['error']})

# --- SAF 文件操作 ---
@app.route('/api/saf/ls', methods=['POST'])
def api_saf_ls():
    """SAF 列出文件"""
    data = request.json or {}
    uri = data.get('uri', '')
    result = run_cmd(f'termux-saf-ls -u "{uri}"')
    return jsonify({"files": result['stdout']})

@app.route('/api/saf/read', methods=['POST'])
def api_saf_read():
    """SAF 读取文件"""
    data = request.json or {}
    uri = data.get('uri', '')
    result = run_cmd(f'termux-saf-read -u "{uri}"')
    return jsonify({"content": result['stdout']})

@app.route('/api/saf/write', methods=['POST'])
def api_saf_write():
    """SAF 写入文件"""
    data = request.json or {}
    uri = data.get('uri', '')
    content = data.get('content', '')
    result = run_cmd(f'termux-saf-write -u "{uri}" <<< "{content}"')
    return jsonify(result)

# --- 任务调度 ---
@app.route('/api/job/schedule', methods=['POST'])
def api_job_schedule():
    """安排后台任务"""
    data = request.json or {}
    script = data.get('script', '')
    timeout = data.get('timeout', 60)
    result = run_cmd(f'termux-job-scheduler -s "{script}" -t {timeout}')
    return jsonify(result)

# --- 密钥库 ---
@app.route('/api/keystore', methods=['POST'])
def api_keystore():
    """密钥库操作"""
    data = request.json or {}
    action = data.get('action', 'get')
    key = data.get('key', '')
    value = data.get('value', '')
    
    cmd = f"termux-keystore --{action} {key}"
    if value:
        cmd += f' "{value}"'
    
    result = run_cmd(cmd)
    return jsonify({"result": result['stdout']})

# --- 媒体播放器增强 ---
@app.route('/api/media/info')
def api_media_info():
    """媒体信息"""
    result = run_cmd("termux-media-player info")
    return jsonify({"info": result['stdout']})

# ==================== 媒体 ====================
    data = request.json or {}
    file = data.get('file', '')
    result = run_cmd(f'termux-media-player play "{file}"')
    return jsonify(result)

@app.route('/api/media/scan', methods=['POST'])
def api_media_scan():
    """扫描媒体"""
    data = request.json or {}
    path = data.get('path', '/sdcard')
    result = run_cmd(f'termux-media-scan "{path}"')
    return jsonify(result)

# ==================== ADB 控制 ====================

@app.route('/api/adb/tap', methods=['POST'])
def api_adb_tap():
    """点击坐标"""
    data = request.json
    x = data.get('x', 0)
    y = data.get('y', 0)
    
    result = adb_cmd(f"shell input tap {x} {y}")
    return jsonify(result)

@app.route('/api/adb/swipe', methods=['POST'])
def api_adb_swipe():
    """滑动"""
    data = request.json
    x1 = data.get('x1', 0)
    y1 = data.get('y1', 0)
    x2 = data.get('x2', 0)
    y2 = data.get('y2', 0)
    duration = data.get('duration', 300)
    
    result = adb_cmd(f"shell input swipe {x1} {y1} {x2} {y2} {duration}")
    return jsonify(result)

@app.route('/api/adb/input', methods=['POST'])
def api_adb_input():
    """输入文字"""
    data = request.json
    text = data.get('text', '')
    # 处理特殊字符
    text = text.replace(' ', '%s').replace('"', '\\"')
    
    result = adb_cmd(f"shell input text \"{text}\"")
    return jsonify(result)

@app.route('/api/adb/key', methods=['POST'])
def api_adb_key():
    """按键"""
    data = request.json
    key = data.get('key', 'ENTER')
    
    key_map = {
        'ENTER': '66',
        'BACK': '4',
        'HOME': '3',
        'MENU': '82',
        'VOLUME_UP': '24',
        'VOLUME_DOWN': '25',
        'POWER': '26'
    }
    
    key_code = key_map.get(key, key)
    result = adb_cmd(f"shell input keyevent {key_code}")
    return jsonify(result)

@app.route('/api/adb/screenshot')
def api_adb_screenshot():
    """截图"""
    output = f"/sdcard/screen_{int(time.time())}.png"
    result = adb_cmd(f"shell screencap -p {output}")
    
    if result['success']:
        return jsonify({"success": True, "path": output})
    return jsonify({"error": result['error']})

@app.route('/api/adb/dump')
def api_adb_dump():
    """获取 UI 层级"""
    result = adb_cmd("shell uiautomator dump")
    result2 = adb_cmd("pull /sdcard/window_dump.xml /tmp/")
    
    # 读取 XML
    xml_content = ""
    if os.path.exists("/tmp/window_dump.xml"):
        with open("/tmp/window_dump.xml", 'r') as f:
            xml_content = f.read()
    
    return jsonify({
        "success": result['success'],
        "xml_path": "/tmp/window_dump.xml",
        "content": xml_content
    })

@app.route('/api/adb/screenshot/view')
def api_adb_screenshot_view():
    """查看截图"""
    path = request.args.get('path', '')
    if path and os.path.exists(path):
        return send_file(path, mimetype='image/png')
    return jsonify({"error": "File not found"})

# ==================== AutoJS ====================

@app.route('/api/autojs/exec', methods=['POST'])
def api_autojs_exec():
    """执行 AutoJS 脚本"""
    config = load_config()
    if not config['autojs']['enabled']:
        return jsonify({"error": "AutoJS not enabled"})
    
    data = request.json
    script = data.get('script', '')
    url = config['autojs']['url']
    
    try:
        response = requests.post(f"{url}/rpc", json={"script": script})
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/autojs/nodes')
def api_autojs_nodes():
    """获取 UI 节点 - AutoJS 视觉反馈"""
    # 使用 uiautomator2 获取节点
    result = adb_cmd("shell uiautomator dump")
    result2 = adb_cmd("shell cat /sdcard/window_dump.xml")
    
    # 解析 XML 为 JSON
    xml = result2['stdout']
    nodes = []
    
    try:
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml)
        
        def parse_node(elem, depth=0):
            if elem is None:
                return
            
            # 提取节点信息
            bounds = elem.get('bounds', '')
            # 解析 bounds="[0,0][1080,1920]" -> {"x1":0,"y1":0,"x2":1080,"y2":1920}
            bounds_match = bounds.split('][')
            bounds_parsed = {}
            if len(bounds_match) == 2:
                bounds_parsed = {
                    "x1": bounds_match[0].strip('['),
                    "y1": bounds_match[1].split(',')[0],
                    "x2": bounds_match[1].split(',')[1].strip(']'),
                    "y2": bounds_match[1].split(',')[2].strip(']')
                }
            
            node = {
                "class": elem.get('class', ''),
                "text": elem.get('text', ''),
                "content-desc": elem.get('content-desc', ''),
                "resource-id": elem.get('resource-id', ''),
                "clickable": elem.get('clickable', 'false'),
                "depth": depth,
                "bounds": bounds_parsed
            }
            nodes.append(node)
            
            for child in elem:
                parse_node(child, depth + 1)
        
        if root:
            parse_node(root)
    except Exception as e:
        return jsonify({"error": str(e), "raw_xml": xml})
    
    return jsonify({
        "success": True,
        "timestamp": datetime.now().isoformat(),
        "nodes_count": len(nodes),
        "nodes": nodes[:100]  # 限制返回数量
    })

# ==================== 工具 ====================

@app.route('/api/wake-lock', methods=['POST', 'DELETE'])
def api_wake_lock():
    """保持唤醒锁"""
    action = "acquire" if request.method == "POST" else "release"
    data = request.json or {}
    lock_type = data.get('type', '')  # partial, screen, bright
    
    result = run_cmd(f"termux-wake-lock --{action} {lock_type}")
    return jsonify(result)

@app.route('/api/file', methods=['GET', 'POST', 'DELETE'])
def api_file():
    """文件操作"""
    data = request.args if request.method == "GET" else request.json or {}
    path = data.get('path', '')
    action = data.get('action', 'read')  # read, write, delete, list
    
    if request.method == "DELETE" or action == "delete":
        if path and os.path.exists(path):
            os.remove(path)
            return jsonify({"success": True})
        return jsonify({"error": "File not found"})
    
    if action == "list":
        if os.path.isdir(path):
            files = os.listdir(path)
            return jsonify({"files": files})
        return jsonify({"error": "Not a directory"})
    
    if action == "write":
        content = data.get('content', '')
        mode = data.get('mode', 'w')
        with open(path, mode) as f:
            f.write(content)
        return jsonify({"success": True, "path": path})
    
    # read
    if path and os.path.exists(path):
        with open(path, 'r') as f:
            content = f.read()
        return jsonify({"path": path, "content": content})
    return jsonify({"error": "File not found"})

# ==================== Git 更新 ====================

GITHUB_REPO = "openclaw-glasses/phone-agent"
CURRENT_VERSION = "v1.0.3"

@app.route('/api/version')
def api_version():
    """版本信息"""
    return jsonify({
        "version": CURRENT_VERSION,
        "last_update": datetime.now().isoformat()
    })

@app.route('/api/update/check')
def api_update_check():
    """检查更新"""
    try:
        # 获取 GitHub 最新版本
        import urllib.request
        url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/README.md"
        response = urllib.request.urlopen(url, timeout=10)
        content = response.read().decode('utf-8')
        
        # 从 README 提取版本号
        import re
        version_match = re.search(r'version:?.*?v(\d+\.\d+\.\d+)', content, re.IGNORECASE)
        latest_version = version_match.group(1) if version_match else None
        
        # 比较版本
        current = [int(x) for x in CURRENT_VERSION.replace('v', '').split('.')]
        latest = [int(x) for x in latest_version.split('.')] if latest_version else current
        
        update_available = latest > current
        
        return jsonify({
            "current_version": CURRENT_VERSION,
            "latest_version": f"v{latest_version}" if latest_version else CURRENT_VERSION,
            "update_available": update_available,
            "changelog_url": f"https://github.com/{GITHUB_REPO}/commits/main"
        })
    except Exception as e:
        return jsonify({
            "error": str(e),
            "current_version": CURRENT_VERSION,
            "update_available": False
        })

@app.route('/api/update', methods=['POST'])
def api_update():
    """手动更新代码"""
    result = run_cmd("git pull origin main")
    return jsonify(result)

@app.route('/api/update/auto', methods=['POST'])
def api_auto_update():
    """自动升级（下载最新版本，优雅重启）"""
    try:
        import urllib.request
        import zipfile
        import io
        import shutil
        import os
        
        # 1. 创建升级脚本
        upgrade_script = """#!/bin/bash
# 等待主进程退出
sleep 2

# 备份旧版本
BACKUP_DIR="/data/data/com.termux/files/home/phone-agent-backup-$(date +%s)"
cp -r /data/data/com.termux/files/home/phone-agent "$BACKUP_DIR"

# 下载新版本
cd /data/data/com.termux/files/home
rm -rf phone-agent-new
wget -q https://github.com/openclaw-glasses/phone-agent/archive/refs/heads/main.zip -O phone-agent.zip
unzip -q phone-agent.zip
rm phone-agent.zip

# 替换
rm -rf phone-agent-old
mv phone-agent phone-agent-old
mv phone-agent-main phone-agent

# 启动新版本
cd phone-agent
nohup python phone_agent.py > /dev/null 2>&1 &
echo "Upgrade complete. New version started."
"""
        
        script_path = "/data/data/com.termux/files/home/phone-agent-upgrade.sh"
        with open(script_path, 'w') as f:
            f.write(upgrade_script)
        os.chmod(script_path, 0o755)
        
        # 2. 后台执行升级
        subprocess.Popen(
            ["sh", script_path],
            stdout=open("/data/data/com.termux/files/home/phone-agent-upgrade.log", "w"),
            stderr=subprocess.STDOUT
        )
        
        return jsonify({
            "success": True,
            "message": "Upgrade started. Service will restart shortly.",
            "log_file": "/data/data/com.termux/files/home/phone-agent-upgrade.log"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/restart', methods=['POST'])
def api_restart():
    """重启服务"""
    try:
        # 记录当前 PID
        pid = os.getpid()
        
        # 创建重启脚本
        restart_script = """#!/bin/bash
sleep 1
cd /data/data/com.termux/files/home/phone-agent
nohup python phone_agent.py > /dev/null 2>&1 &
"""
        script_path = "/data/data/com.termux/files/home/phone-agent-restart.sh"
        with open(script_path, 'w') as f:
            f.write(restart_script)
        os.chmod(script_path, 0o755)
        
        # 后台启动新进程
        subprocess.Popen(["sh", script_path])
        
        # 退出当前进程
        return jsonify({
            "success": True,
            "message": "Restarting...",
            "old_pid": pid
        })
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/update/schedule', methods=['POST'])
def api_update_schedule():
    """定时更新配置"""
    data = request.json
    interval = data.get('interval', 3600)
    auto_upgrade = data.get('auto_upgrade', False)
    
    config = load_config()
    config['update_interval'] = interval
    config['auto_upgrade'] = auto_upgrade
    save_config(config)
    
    return jsonify({"success": True, "interval": interval, "auto_upgrade": auto_upgrade})

# ==================== 启动 ====================

def start_http_server(config):
    """启动 HTTP 服务器"""
    host = config['server']['host']
    port = config['server']['port']
    
    print(f"🚀 Phone Agent v1.0.1 启动中...")
    print(f"📡 服务器: http://{host}:{port}")
    print(f"🔗 状态页: http://{host}:{port}/")
    
    app.run(host=host, port=port, debug=False, threaded=True)

def auto_update_thread():
    """自动更新线程"""
    config = load_config()
    interval = config.get('update_interval', 3600)
    
    while True:
        time.sleep(interval)
        run_cmd("git pull origin main")

if __name__ == '__main__':
    # 加载配置
    config = load_config()
    
    # 启动自动更新线程
    if config.get('update_interval'):
        t = threading.Thread(target=auto_update_thread)
        t.daemon = True
        t.start()
    
    # 启动服务器
    start_http_server(config)
