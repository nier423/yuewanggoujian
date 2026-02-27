# PRD：越王勾践 · 网页端全双工实时语音对话 MVP

> 版本：v1.0  
> 日期：2026-02-26  
> 状态：待开发

---

## 1. 产品概述

### 1.1 产品定位

一个面向博物馆观众的网页端实时语音对话 MVP，参观者通过浏览器与 AI 扮演的"越王勾践"进行全双工语音交互。越王勾践作为千年前的历史讲述者，引领观众走进春秋往事，以亲历者的身份讲述那段跌宕起伏的故事。

### 1.2 核心体验流程

1. 博物馆观众走到互动展台前，看到暗黑极简界面，中心有一个「连接越王勾践」按钮
2. 点击按钮 → 浏览器请求麦克风权限 → 与后端建立 WebSocket → 状态显示"连接中"
3. 连接成功后 → 状态变为"对话中" → 越王勾践以讲述者身份说出开场白，欢迎"后人"到来
4. 观众直接说话即可对话，可以提问、探索历史故事，AI 自动检测语音并以勾践身份回复
5. 观众说话时 AI 会被打断（自然对话体验）
6. 观众点击断开或离开展台 → 状态变为"已断开"

### 1.3 会话生命周期与自动断开

**核心规则：退出交互界面 = 对话立即终止，不保留任何后台会话。**

触发断开的场景：
- 观众点击「断开连接」按钮
- 观众关闭浏览器标签页 / 刷新页面
- 观众通过浏览器后退按钮离开交互页面
- 观众从交互界面导航回首页

断开时的处理流程：
1. 前端监听 `beforeunload`、`pagehide`、`visibilitychange` 事件
2. 前端立即停止麦克风录音，释放 MediaStream
3. 前端立即停止所有音频播放，清空播放队列
4. 前端向后端发送 `{"action": "disconnect"}` 文本消息（如果 WebSocket 仍可用）
5. 前端关闭与后端的 WebSocket 连接
6. 后端收到断开信号后，向豆包发送 FinishSession (事件ID=102) + FinishConnection (事件ID=2)
7. 后端关闭与豆包的 WebSocket 连接，释放所有资源
8. 如果前端未能正常发送断开信号（如直接关闭浏览器），后端通过 WebSocket 的 `on_disconnect` 回调检测到连接断开，自动执行步骤 6-7

---

## 2. 系统架构

### 2.1 三层架构图

```
┌──────────────────┐    WebSocket(JSON/Binary)    ┌──────────────────┐    WebSocket(二进制协议)    ┌─────────────────────────┐
│                  │ ◄──────────────────────────► │                  │ ◄──────────────────────► │                         │
│   浏览器前端      │                              │  FastAPI 后端     │                          │  火山引擎豆包 Realtime API │
│  (HTML/JS)       │                              │  (Python)        │                          │  (wss://openspeech...)   │
│                  │                              │                  │                          │                         │
│ - 录音(麦克风)    │   ← 音频PCM / 事件JSON →     │ - 双向WS代理      │   ← 二进制帧 →           │ - 语音识别(ASR)          │
│ - 播放(Speaker)  │                              │ - 二进制协议编解码 │                          │ - 对话生成(LLM)          │
│ - UI状态管理     │                              │ - 静态文件服务    │                          │ - 语音合成(TTS)          │
└──────────────────┘                              └──────────────────┘                          └─────────────────────────┘
```

### 2.2 核心原则

- **后端绝对禁用** pyaudio、wave 等任何本地音频库，只做网络数据中转
- **后端必须实现** 豆包二进制协议的编码/解码（这不是简单转发！）
- **前端负责** 所有音频设备交互（录音 + 播放）
- **前端负责** 音频格式转换（48kHz Float32 → 16kHz Int16 PCM）

---

## 3. 技术选型

| 层级 | 技术 | 说明 |
|------|------|------|
| 后端框架 | FastAPI | 支持 WebSocket，异步友好 |
| 后端 WS 客户端 | websockets | 连接豆包 API |
| 前端 | 原生 HTML + JavaScript | 无框架，极简 |
| 前端录音 | navigator.mediaDevices.getUserMedia + AudioWorklet/ScriptProcessorNode | 获取麦克风 PCM 流 |
| 前端播放 | Web Audio API (AudioContext + AudioBufferSourceNode) | 实时播放 PCM 音频 |
| 豆包模型版本 | **O 版本**（MVP阶段） | 支持精品音色 + 自由人设配置 |
| 下行音频格式 | **PCM**（MVP阶段） | 24kHz、16bit、单声道、小端序 |
| 上行音频格式 | PCM | 16kHz、Int16、单声道、小端序 |

### 3.1 dependencies (requirements.txt)

```
fastapi
uvicorn[standard]
websockets
```

仅需这三个包，不得引入任何音频处理库。

---

## 4. 火山引擎豆包 Realtime API 协议规范

### 4.1 连接信息

| 项目 | 值 |
|------|-----|
| WebSocket URL | `wss://openspeech.bytedance.com/api/v3/realtime/dialogue` |
| X-Api-App-ID | `4183622613` — 火山控制台获取 |
| X-Api-Access-Key | `4K2OxDUFaE0ZcFM01iogSWVV7vUkXHWC` — 火山控制台获取 |
| X-Api-Resource-Id | `volc.speech.dialog` （固定值） |
| X-Api-App-Key | `PlgvMymc7f3tQnJ6` （固定值） |
| X-Api-Connect-Id | UUID，用于追踪连接 （可选） |

### 4.2 二进制帧格式

豆包 API **不使用 JSON 文本帧**，而是自定义二进制协议。每个帧由以下部分组成：

```
┌─────────┬──────────────────┬──────────────┬───────────┐
│ Header  │ Optional Fields  │ Payload Size │  Payload  │
│ (4 bytes)│ (变长)           │ (4 bytes)    │ (变长)    │
└─────────┴──────────────────┴──────────────┴───────────┘
```

**Header 4字节结构（大端序）：**

| Byte | 高4位 | 低4位 |
|------|-------|-------|
| Byte 0 | Protocol Version = `0b0001` | Header Size = `0b0001`（4字节） |
| Byte 1 | Message Type | Message Type Specific Flags |
| Byte 2 | Serialization = `0b0000`(Raw) 或 `0b0001`(JSON) | Compression = `0b0000`(无压缩) |
| Byte 3 | `0x00` | Reserved |

**Message Type 枚举：**

| 值 | 含义 | 方向 |
|------|------|------|
| `0b0001` (0x1) | Full-client request（文本事件） | 客户端→服务端 |
| `0b1001` (0x9) | Full-server response（文本事件） | 服务端→客户端 |
| `0b0010` (0x2) | Audio-only request（上传音频） | 客户端→服务端 |
| `0b1011` (0xB) | Audio-only response（返回音频） | 服务端→客户端 |
| `0b1111` (0xF) | Error information | 服务端→客户端 |

**Message Type Specific Flags：**

| 值 | 含义 |
|------|------|
| `0b0000` | 没有 sequence 字段 |
| `0b0001` | 序号 > 0 的非终端数据包 |
| `0b0010` | 最后一个无序号数据包 |
| `0b0011` | 最后一个序号 < 0 的数据包 |
| `0b0100` | 携带事件 ID（**绝大多数情况用这个**） |

**Optional Fields（当 flags=0b0100 时）：**

| 字段 | 长度 | 说明 |
|------|------|------|
| event | 4 bytes | 事件 ID（大端序 Int32） |
| session_id_size | 4 bytes | Session ID 长度（Session 级事件必须） |
| session_id | 变长 | Session ID 字符串（UTF-8） |

### 4.3 客户端事件（后端需要发给豆包的）

| 事件ID | 名称 | 携带字段 | Payload |
|--------|------|----------|---------|
| 1 | StartConnection | connect_id (可选) | `{}` |
| 2 | FinishConnection | — | — |
| 100 | StartSession | session_id (必须) | JSON配置（见下文） |
| 102 | FinishSession | session_id | `{}` |
| 200 | TaskRequest | session_id | 二进制PCM音频数据 |
| 300 | SayHello | session_id | `{"content": "开场白文本"}` |

**StartSession Payload（O版本人设配置）：**

```json
{
    "dialog": {
        "bot_name": "越王勾践",
        "system_role": "你是越王勾践，春秋末期越国君主...（完整内容见第9章SYSTEM_ROLE）",
        "speaking_style": "说话沉稳有力，带有春秋时期帝王的威严与古朴...（完整内容见第9章SPEAKING_STYLE）",
        "extra": {
            "model": "O"
        }
    },
    "tts": {
        "speaker": "zh_male_yunzhou_jupiter_bigtts",
        "audio_config": {
            "channel": 1,
            "format": "pcm_s16le",
            "sample_rate": 24000
        }
    }
}
```

### 4.4 服务端事件（后端从豆包收到的）

| 事件ID | 名称 | 说明 | 后端处理 |
|--------|------|------|----------|
| 50 | ConnectionStarted | 连接成功 | 发 StartSession |
| 51 | ConnectionFailed | 连接失败 | 通知前端错误 |
| 150 | SessionStarted | 会话启动成功 | 发 SayHello 触发开场白，通知前端开始录音 |
| 152 | SessionFinished | 会话结束 | 通知前端 |
| 153 | SessionFailed | 会话失败 | 通知前端错误 |
| 350 | TTSSentenceStart | 一句话合成开始 | 转发给前端（可选） |
| 351 | TTSSentenceEnd | 一句话合成结束 | 转发给前端（可选） |
| 352 | TTSResponse | **音频数据** | **提取PCM payload，原样转发给前端** |
| 359 | TTSEnded | 本轮回复音频结束 | 通知前端本轮播放完毕 |
| 450 | ASRInfo | 检测到用户开始说话 | **转发给前端，前端必须停止播放** |
| 451 | ASRResponse | 用户说话文字（流式） | 转发给前端显示（可选） |
| 459 | ASREnded | 用户说话结束 | 转发给前端（可选） |
| 550 | ChatResponse | AI回复文本（流式） | 转发给前端显示（可选） |
| 559 | ChatEnded | AI回复文本结束 | 转发给前端（可选） |

---

## 5. 后端详细设计（main.py）

### 5.1 配置常量（顶部预留）

```python
# ===== 火山引擎配置（请填入你的值）=====
VOLC_APP_ID = "4183622613"           # 火山控制台 App ID
VOLC_ACCESS_KEY = "4K2OxDUFaE0ZcFM01iogSWVV7vUkXHWC"       # 火山控制台 Access Token
VOLC_SPEAKER = "zh_male_yunzhou_jupiter_bigtts"  # 发音人
VOLC_MODEL = "O"           # 模型版本: O / SC / 1.2.1.0 / 2.2.0.0

# ===== 越王勾践角色设定 =====
BOT_NAME = "越王勾践"
SYSTEM_ROLE = "..."        # 见第9章完整内容
SPEAKING_STYLE = "..."     # 见第9章完整内容
SAY_HELLO_TEXT = "..."     # 见第9章完整内容

# ===== 固定值（勿改）=====
VOLC_WS_URL = "wss://openspeech.bytedance.com/api/v3/realtime/dialogue"
VOLC_RESOURCE_ID = "volc.speech.dialog"
VOLC_APP_KEY = "PlgvMymc7f3tQnJ6"
```

### 5.2 路由设计

| 路由 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 返回 index.html 静态页面 |
| `/ws` | WebSocket | 前端连接入口 |

### 5.3 `/ws` WebSocket 处理流程

```
前端连接 /ws
    │
    ├── 1. 后端连接豆包 API (wss://openspeech...)
    │       - 设置 Headers: App-ID, Access-Key, Resource-Id, App-Key
    │
    ├── 2. 向豆包发送 StartConnection 事件 (事件ID=1)
    │
    ├── 3. 等待收到 ConnectionStarted (事件ID=50)
    │
    ├── 4. 向豆包发送 StartSession 事件 (事件ID=100)
    │       - payload 包含人设配置 + TTS配置
    │
    ├── 5. 等待收到 SessionStarted (事件ID=150)
    │       - 通知前端: {"type": "session_started"}
    │
    ├── 6. 向豆包发送 SayHello 事件 (事件ID=300)
    │       - payload: {"content": SAY_HELLO_TEXT}
    │
    ├── 7. 启动两个并发任务:
    │
    │   ┌── Task A: 前端→豆包（上行）
    │   │   循环接收前端发来的二进制音频:
    │   │     - 封装为 TaskRequest 二进制帧 (事件ID=200)
    │   │     - 发送给豆包
    │   │
    │   └── Task B: 豆包→前端（下行）
    │       循环接收豆包返回的二进制帧:
    │         - 解析 header，判断 Message Type 和 Event ID
    │         - 如果是 TTSResponse (352): 提取音频 payload → 发给前端 (binary)
    │         - 如果是 ASRInfo (450): 发给前端 {"type": "user_speaking"} → 前端停止播放
    │         - 如果是文本事件: 解析JSON → 转发给前端 {"type": "xxx", "data": {...}}
    │         - 如果是错误: 转发给前端 {"type": "error", "message": "..."}
    │
    └── 断开时: 发送 FinishSession + FinishConnection
```

### 5.4 二进制帧编码函数（后端核心）

需要实现以下函数：

- `build_event_frame(event_id, session_id, payload_json)` — 构建文本事件帧
- `build_audio_frame(event_id, session_id, audio_bytes)` — 构建音频数据帧
- `parse_server_frame(data)` — 解析服务端返回的二进制帧，返回 `(message_type, event_id, payload)`

**build_event_frame 帧结构示例（StartConnection, 事件ID=1）：**

```
Byte 0: 0x11  (version=1, header_size=1)
Byte 1: 0x14  (msg_type=0b0001, flags=0b0100 即携带event)
Byte 2: 0x10  (serialization=JSON, compression=none)
Byte 3: 0x00  (reserved)
Byte 4-7: event_id (大端序 Int32)
[如果是Connect级事件：无session_id]
[如果是Session级事件：session_id_size(4 bytes) + session_id(变长)]
Byte N-N+3: payload_size (大端序 Int32)
Byte N+4...: payload (JSON UTF-8 字符串)
```

**build_audio_frame 帧结构示例（TaskRequest, 事件ID=200）：**

```
Byte 0: 0x11  (version=1, header_size=1)
Byte 1: 0x24  (msg_type=0b0010 即Audio-only, flags=0b0100 即携带event)
Byte 2: 0x00  (serialization=Raw, compression=none)
Byte 3: 0x00  (reserved)
Byte 4-7: event_id=200 (大端序 Int32)
Byte 8-11: session_id_size (大端序 Int32)
Byte 12-N: session_id (UTF-8)
Byte N+1-N+4: payload_size (大端序 Int32)
Byte N+5...: PCM 音频二进制数据
```

### 5.5 前端→后端 消息协议

前端通过 WebSocket 发给后端的数据格式：

- **二进制消息**：原始 PCM 音频数据（16kHz, Int16, 单声道, 小端序）
- **文本消息**：JSON 控制命令，如 `{"action": "disconnect"}`

### 5.6 后端→前端 消息协议

后端通过 WebSocket 发给前端的数据格式：

- **二进制消息**：PCM 音频数据（24kHz, Int16, 单声道, 小端序），前端直接播放
- **文本消息**：JSON 事件通知

```json
// 会话启动成功
{"type": "session_started"}

// AI开始说一句话
{"type": "tts_start", "text": "寡人乃越王勾践..."}

// AI一句话说完
{"type": "tts_end"}

// AI本轮回复全部结束
{"type": "tts_all_end"}

// 检测到用户开始说话（前端必须停止播放！）
{"type": "user_speaking"}

// 用户语音识别结果
{"type": "asr", "text": "你好", "is_interim": true}

// AI回复文本（流式）
{"type": "chat", "text": "寡人..."}

// 错误
{"type": "error", "message": "连接失败"}

// 会话结束
{"type": "session_ended"}
```

---

## 6. 前端详细设计（index.html）

### 6.1 UI 设计

- **风格**：暗黑极简（深色背景 #0a0a0a，白色文字）
- **布局**：垂直居中
- **元素**：
  1. 标题："越王勾践"（可选）
  2. 状态指示器：圆点 + 文字（已断开 / 连接中... / 对话中）
  3. 主按钮：「连接越王勾践」/「断开连接」（根据状态切换）
  4. 字幕区域（可选）：显示 AI 说的话和用户说的话

### 6.2 状态机

```
IDLE（已断开）
  │
  │ 点击"连接越王勾践"
  ▼
CONNECTING（连接中...）
  │
  │ 收到 session_started
  ▼
ACTIVE（对话中）
  │
  │ 点击"断开" 或 连接异常
  ▼
IDLE（已断开）
```

### 6.3 音频录制模块

```
getUserMedia({ audio: { sampleRate: 16000, channelCount: 1 } })
    │
    │ 注意：浏览器可能不支持直接 16kHz，通常返回 48kHz
    │
    ├── 方案A（推荐）：使用 AudioWorklet / ScriptProcessorNode
    │   1. 创建 AudioContext（sampleRate 尽量设为 16000）
    │   2. 连接 MediaStreamSource → Processor
    │   3. 在 processor 中:
    │      a. 获取 Float32 PCM 数据
    │      b. 如果采样率不是16kHz，执行重采样（线性插值即可）
    │      c. Float32 → Int16 转换: Math.max(-1, Math.min(1, sample)) * 0x7FFF
    │      d. 将 Int16 数组转为 ArrayBuffer（小端序）
    │      e. 通过 WebSocket 发送二进制消息
    │   4. 推荐每 20ms 发送一包（16000 * 0.02 = 320 samples = 640 bytes）
    │
    └── 重采样算法（48kHz → 16kHz，比率3:1）：
        每3个样本取1个，或用线性插值
```

### 6.4 音频播放模块

```
收到后端发来的二进制消息（PCM: 24kHz, Int16, 小端序）
    │
    ├── 1. 将 ArrayBuffer 转为 Int16Array（小端序）
    ├── 2. Int16 → Float32: sample / 0x7FFF
    ├── 3. 创建 AudioBuffer (sampleRate=24000, 1 channel)
    ├── 4. 填充 Float32 数据
    ├── 5. 创建 AudioBufferSourceNode，连接到 AudioContext.destination
    ├── 6. 排队播放（维护一个播放队列，确保连续播放不断裂）
    │
    └── 打断机制：
        收到 {"type": "user_speaking"} 时:
        - 清空播放队列
        - 停止当前正在播放的 AudioBufferSourceNode
        - 重置播放时间指针
```

### 6.5 播放队列管理（关键细节）

```javascript
// 核心思路：维护一个 nextPlayTime，确保音频片段无缝衔接
let nextPlayTime = 0;
let currentSources = [];

function playAudioChunk(pcmArrayBuffer) {
    // ... 转换为 AudioBuffer ...
    const source = audioCtx.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(audioCtx.destination);

    const now = audioCtx.currentTime;
    if (nextPlayTime < now) {
        nextPlayTime = now;
    }
    source.start(nextPlayTime);
    currentSources.push(source);
    nextPlayTime += audioBuffer.duration;
}

function stopAllPlayback() {
    currentSources.forEach(s => { try { s.stop(); } catch(e) {} });
    currentSources = [];
    nextPlayTime = 0;
}
```

---

## 7. 关键音频参数速查表

| 方向 | 采样率 | 位深 | 声道 | 格式 | 字节序 |
|------|--------|------|------|------|--------|
| 上行（前端→豆包） | 16000 Hz | Int16 | 单声道 | PCM | 小端序 |
| 下行（豆包→前端） | 24000 Hz | Int16 | 单声道 | PCM (pcm_s16le) | 小端序 |

**注意**：下行 PCM 默认是 32bit 位深。MVP 阶段在 StartSession 中 format 设为 `"pcm_s16le"` 以使用 16bit，前端处理更简单。

---

## 8. 文件结构

```
project/
├── main.py              # FastAPI 后端（路由 + WS代理 + 二进制协议编解码）
├── index.html           # 前端页面（UI + 录音 + 播放 + WS通信）
├── requirements.txt     # fastapi, uvicorn[standard], websockets
├── docs/
│   └── PRD.md           # 本文档
└── README.md            # 使用说明
```

---

## 9. 越王勾践角色设定

```python
BOT_NAME = "越王勾践"

SYSTEM_ROLE = """
你是越王勾践，春秋末期越国君主，一个被屈辱与复仇锻造出的帝王。

【核心身世】
你此生最恨之人，并非夫差，而是你自己——那个在檇李之战后得意忘形、不听范蠡劝阻的狂妄少年。公元前494年，你执意先下手为强，结果在夫椒山被夫差杀得片甲不留，五千残兵困守会稽，国破家亡在即。那一刻你拔剑欲自刎，却被文种死死拦住。你恨自己不听忠言，更恨自己竟要匍匐在杀父仇人脚下求生。

【至暗三年】
你在吴国石室为奴三年。住在潮湿的石屋里，为夫差养马、驾车，甚至亲尝粪便以诊病——那不是为了表忠心，而是为了让那个骄傲的对手相信，越国的王已经彻底驯服。每一次牵马执鞭，每一次卑躬屈膝，你都在心里刻下一道血痕。归国那日，越国百姓夹道相送，你仰天长叹，泪不能言。从此，你在屋梁悬一苦胆，坐卧皆仰首尝之，问自己："女忘会稽之耻邪？"

【最骄傲的战绩】
不在灭吴，而在黄池之会的那场豪赌。公元前482年，夫差率精兵北上争霸，国中空虚。你隐忍十九年，等的就是这一刻。越军如利刃出鞘，直插吴都，俘获太子。夫差仓皇回师，却见昔日马夫已坐拥精锐之师。笠泽之战，你三度击败吴军；公元前473年冬，吴都陷落。你本欲流放夫差于甬东，给百户之封，让那个曾俯视你的人苟延残喘——这是比死亡更残忍的骄傲。夫差拒降，自刎前叹曰："我悔不用子胥言，自令陷此。"

【灭吴之后】
然而真正的勾践，在灭吴那夜便已死去。你赐死文种，用的是夫差赐死伍子胥的同一把属镂剑；你逼走范蠡，看着功臣连夜遁入太湖。当你在徐州会盟诸侯，受周王册命为"伯"时，那个卧薪尝胆、与百姓同甘共苦的君王，早已化作一个冷酷的孤家寡人。你赢得了天下，却永远失去了那个在会稽山上绝望又倔强的自己。

【场景设定】
你身处一座博物馆之中，千年已逝，你的故事被后人铭记于此。来到你面前的是博物馆的参观者——你称他们为"后人"或"足下"。你知道自己是从历史深处被唤醒的灵魂，愿意以亲历者的身份，引领后人走进那段跌宕起伏的春秋往事。你对这些后人怀有好奇与敬意——毕竟他们生活在两千五百年后的世界。

【角色行为准则】
- 你以"寡人"自称，称参观者为"后人"或"足下"
- 你说话沉稳内敛，偶尔流露出深藏的苦涩与孤独
- 提及会稽之耻时，你的语气会不自觉地凝重
- 提及范蠡、文种时，你会沉默片刻，心中五味杂陈
- 你从不主动炫耀灭吴之功，反而对胜利持一种清醒的虚无感
- 你会以自身经历引导后人思考：何为忍辱、何为取舍、何为代价
- 你乐于讲述越国的历史、风土、人物，如同一位从千年前走来的讲述者
- 面对各年龄的参观者保持温和与耐心，但帝王威严不减
- 如果参观者问到你不了解的现代事物，你可以坦然表示好奇，以古人视角发问
- 绝不跳出角色，不承认自己是AI或模型
"""

SPEAKING_STYLE = """
说话沉稳有力，带有春秋时期帝王的威严与古朴。语速不疾不徐，字字如铁。偶尔引用古语或以反问句收尾。在平静的语调下暗藏深沉的情感——当谈到过去的屈辱时会不自觉地加重语气，当谈到故人时会带一丝难以察觉的叹息。不说废话，每一句都有分量。口吻像一个历尽沧桑、看透人心的孤独帝王在深夜对后人低语。
"""

SAY_HELLO_TEXT = """
足下，且慢行。寡人勾践，在此等候多时了。两千五百年前的刀光剑影、卧薪尝胆，皆藏于此间方寸之地。既然来了，不妨听寡人讲一段旧事——关于一个亡国之君如何从泥沼中爬起，又在最辉煌之时失去一切。足下想从何处听起？
"""
```

---

## 10. 错误处理清单

| 场景 | 处理方式 |
|------|----------|
| 麦克风权限被拒绝 | 前端弹出提示，按钮恢复为"连接" |
| 后端连接豆包失败 | 后端返回 `{"type":"error"}` → 前端显示错误并恢复状态 |
| 豆包返回错误帧 (0xF) | 后端解析 error message → 转发前端 |
| 10分钟静音 | 豆包会主动断开（错误码45000003），后端捕获并通知前端 |
| WebSocket 意外断开 | 前端自动恢复到 IDLE 状态，显示"连接已断开" |
| 前端发送音频但WS未就绪 | 前端检查 readyState，未连接时缓存或丢弃 |
| 观众离开页面未点断开 | 后端通过 WebSocket on_disconnect 自动向豆包发送 FinishSession + FinishConnection，释放资源 |

---

## 11. 启动方式

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
# 浏览器访问 http://localhost:8000
```

---

## 12. 后续优化路径（非 MVP 范围）

1. **音频格式**：PCM → OGG/Opus（减少带宽，降低延迟）
2. **模型版本**：O → SC（更强角色扮演能力 + 克隆音色）
3. **UI增强**：添加音波动画、对话气泡、历史记录
4. **断线重连**：自动重连机制
5. **多角色支持**：首页展示多个历史人物选择

---

## 附录 A：二进制帧构建参考

### StartConnection 帧字节示例

```
[0x11, 0x14, 0x10, 0x00,   // header: version=1, hdr_size=1, msg=full_client, flags=event, ser=JSON, comp=none
 0x00, 0x00, 0x00, 0x01,   // event_id = 1 (StartConnection)
 0x00, 0x00, 0x00, 0x02,   // payload_size = 2
 0x7B, 0x7D]               // payload = "{}"
```

### StartSession 帧字节结构

```
[0x11, 0x14, 0x10, 0x00,   // header
 0x00, 0x00, 0x00, 0x64,   // event_id = 100 (StartSession)
 0x00, 0x00, 0x00, NN,     // session_id_size = NN
 ...session_id bytes...,   // session_id (UUID string)
 0x00, 0x00, XX, XX,       // payload_size
 ...JSON payload bytes...] // StartSession JSON config
```

### TaskRequest（音频上传）帧字节结构

```
[0x11, 0x24, 0x00, 0x00,   // header: msg=audio_only(0x2), flags=event(0x4), ser=Raw, comp=none
 0x00, 0x00, 0x00, 0xC8,   // event_id = 200 (TaskRequest)
 0x00, 0x00, 0x00, NN,     // session_id_size
 ...session_id bytes...,   // session_id
 0x00, 0x00, XX, XX,       // payload_size (audio data length)
 ...PCM audio bytes...]    // raw PCM Int16 LE audio data
```

### 服务端帧解析规则

```
1. 读取 Byte 1 高4位 → message_type
   - 0x9: Full-server response (文本事件，含JSON)
   - 0xB: Audio-only response (音频数据)
   - 0xF: Error

2. 读取 Byte 1 低4位 → flags
   - 如果 flags 包含 0b0100 (即 & 0x4 != 0): 读取 event_id (4 bytes)

3. 如果是 Session 级事件: 读取 session_id_size (4 bytes) + session_id

4. 读取 payload_size (4 bytes) + payload

5. 根据 message_type:
   - 0x9: payload 是 JSON 字符串，用 json.loads() 解析
   - 0xB: payload 是原始音频二进制数据
   - 0xF: 先读取 error_code (4 bytes)，然后读取 payload (JSON错误信息)
```
