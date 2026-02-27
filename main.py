import asyncio
import json
import struct
import uuid
import logging
import os
from typing import Tuple, Optional, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
import websockets
from websockets.exceptions import ConnectionClosed

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("main")

# ===== 火山引擎配置 =====
VOLC_APP_ID = os.environ.get("VOLC_APP_ID", "4183622613")
VOLC_ACCESS_KEY = os.environ.get("VOLC_ACCESS_KEY", "4K2OxDUFaE0ZcFM01iogSWVV7vUkXHWC")
VOLC_SPEAKER = os.environ.get("VOLC_SPEAKER", "zh_male_yunzhou_jupiter_bigtts")
VOLC_MODEL = os.environ.get("VOLC_MODEL", "O")
VOLC_APP_KEY = os.environ.get("VOLC_APP_KEY", "PlgvMymc7f3tQnJ6") # Fixed value from original code

if not VOLC_APP_ID or not VOLC_ACCESS_KEY:
    logger.warning("Warning: VOLC_APP_ID or VOLC_ACCESS_KEY is not set in environment variables. Using default/fallback values (if any) or service may fail.")

# ===== 越王勾践角色设定 =====
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

# ===== 固定值 =====
VOLC_WS_URL = "wss://openspeech.bytedance.com/api/v3/realtime/dialogue"
VOLC_RESOURCE_ID = "volc.speech.dialog"
# VOLC_APP_KEY = "PlgvMymc7f3tQnJ6" # Moved to env var

app = FastAPI()

# ==============================================================================
# 协议处理函数
# ==============================================================================

def build_header(msg_type: int, flags: int, serialization: int, compression: int = 0) -> bytes:
    """
    构建 4 字节 Header
    Byte 0: Protocol Version (0b0001) | Header Size (0b0001) -> 0x11
    Byte 1: Message Type (4 bits) | Flags (4 bits)
    Byte 2: Serialization (4 bits) | Compression (4 bits)
    Byte 3: Reserved (0x00)
    """
    byte0 = 0x11
    byte1 = (msg_type << 4) | flags
    byte2 = (serialization << 4) | compression
    byte3 = 0x00
    return struct.pack(">BBBB", byte0, byte1, byte2, byte3)

def build_event_frame(event_id: int, session_id: Optional[str] = None, payload_json: dict = None) -> bytes:
    """
    构建文本事件帧 (Full-client request, 0x1)
    """
    msg_type = 0x1
    flags = 0b0100  # 携带 event_id
    serialization = 0x1  # JSON
    
    header = build_header(msg_type, flags, serialization)
    
    body = bytearray()
    body.extend(struct.pack(">I", event_id))  # Event ID (4 bytes)
    
    if session_id:
        session_id_bytes = session_id.encode('utf-8')
        body.extend(struct.pack(">I", len(session_id_bytes))) # Session ID Size
        body.extend(session_id_bytes) # Session ID
        
    payload_bytes = json.dumps(payload_json).encode('utf-8') if payload_json else b"{}"
    body.extend(struct.pack(">I", len(payload_bytes))) # Payload Size
    body.extend(payload_bytes) # Payload
    
    return header + body

def build_audio_frame(event_id: int, session_id: str, audio_bytes: bytes) -> bytes:
    """
    构建音频数据帧 (Audio-only request, 0x2)
    """
    msg_type = 0x2
    flags = 0b0100  # 携带 event_id
    serialization = 0x0  # Raw
    
    header = build_header(msg_type, flags, serialization)
    
    body = bytearray()
    body.extend(struct.pack(">I", event_id))  # Event ID
    
    session_id_bytes = session_id.encode('utf-8')
    body.extend(struct.pack(">I", len(session_id_bytes)))
    body.extend(session_id_bytes)
    
    body.extend(struct.pack(">I", len(audio_bytes)))
    body.extend(audio_bytes)
    
    return header + body

def parse_server_frame(data: bytes) -> Tuple[int, int, Any]:
    """
    解析服务端返回的二进制帧
    返回: (message_type, event_id, payload)
    """
    if len(data) < 4:
        raise ValueError("Frame too short")
        
    # Header
    # byte0 = data[0] # version & header_size
    byte1 = data[1]
    msg_type = (byte1 >> 4) & 0x0F
    flags = byte1 & 0x0F
    # byte2 = data[2] # serialization & compression
    
    offset = 4
    event_id = 0
    
    if flags & 0b0100:
        event_id = struct.unpack(">I", data[offset:offset+4])[0]
        offset += 4
        
    # Check for session_id (Session-level events usually have session_id)
    # 根据 PRD 4.2，服务端返回的帧结构解析规则：
    # "如果是 Session 级事件: 读取 session_id_size + session_id"
    # 这里我们通过 event_id 范围或 msg_type 来判断是否包含 session_id 会比较复杂
    # 但根据 PRD 4.4，大部分服务端事件都隐含 session 上下文，
    # 实际上豆包协议中，Audio-only response (0xB) 和 Full-server response (0x9) 的结构
    # 通常都包含 session_id 如果它是 session 相关的。
    # 让我们根据 msg_type 和 event_id 来尝试解析。
    
    # 为了简化，我们假设除了 ConnectionStarted(50)/ConnectionFailed(51) 外，
    # 其他事件（150+）都包含 session_id。
    # 实际上，根据 PRD 4.2 "Optional Fields"，这些字段的存在取决于 flags=0b0100。
    # 而 session_id 是否存在，取决于具体的事件定义。
    # 在 4.2 中提到 "Session ID 长度（Session 级事件必须）"。
    
    # 让我们采用一种更通用的方式：
    # 如果是 Connection 级事件 (1-99)，通常没有 session_id
    # 如果是 Session 级事件 (100+)，通常有 session_id
    
    has_session_id = event_id >= 100
    
    if has_session_id:
        if offset + 4 > len(data):
             # 某些错误帧可能没有 session_id，即使 ID 很大？
             # 或者数据不完整。暂且假设按照 ID 判断。
             pass
        else:
            session_id_size = struct.unpack(">I", data[offset:offset+4])[0]
            offset += 4
            # session_id = data[offset:offset+session_id_size] # 我们不需要使用它，直接跳过
            offset += session_id_size
            
    if offset + 4 > len(data):
        return msg_type, event_id, None
        
    payload_size = struct.unpack(">I", data[offset:offset+4])[0]
    offset += 4
    
    payload = data[offset:offset+payload_size]
    
    if msg_type == 0x9: # Full-server response (JSON)
        try:
            payload = json.loads(payload.decode('utf-8'))
        except:
            pass
    elif msg_type == 0xF: # Error
        # Error payload structure: error_code (4 bytes) + error_data (JSON)
        error_code = struct.unpack(">I", payload[:4])[0]
        try:
            error_data = json.loads(payload[4:].decode('utf-8'))
            payload = {"code": error_code, "data": error_data}
        except:
            payload = {"code": error_code, "raw": payload[4:]}
            
    return msg_type, event_id, payload

# ==============================================================================
# FastAPI 路由
# ==============================================================================

@app.get("/")
async def get_index():
    return FileResponse("index.html")

@app.websocket("/ws")
async def websocket_endpoint(client_ws: WebSocket):
    await client_ws.accept()
    logger.info("Client connected")
    
    # 生成 Session ID
    session_id = str(uuid.uuid4())
    
    # 连接豆包
    volc_ws_url = VOLC_WS_URL
    headers = {
        "X-Api-App-Id": VOLC_APP_ID,
        "X-Api-Access-Key": VOLC_ACCESS_KEY,
        "X-Api-Resource-Id": VOLC_RESOURCE_ID,
        "X-Api-App-Key": VOLC_APP_KEY,
    }
    
    try:
        async with websockets.connect(volc_ws_url, additional_headers=headers) as volc_ws:
            logger.info("Connected to Volcengine")
            
            # 2. 发送 StartConnection (Event 1)
            await volc_ws.send(build_event_frame(1, None, {}))
            
            # 3. 等待 ConnectionStarted (Event 50)
            # 我们需要在一个循环中读取，直到收到 50
            while True:
                data = await volc_ws.recv()
                msg_type, event_id, payload = parse_server_frame(data)
                if event_id == 50:
                    logger.info("Connection Started")
                    break
                elif event_id == 51:
                    logger.error(f"Connection Failed: {payload}")
                    await client_ws.send_json({"type": "error", "message": "Connection Failed"})
                    return
            
            # 4. 发送 StartSession (Event 100)
            start_session_payload = {
                "dialog": {
                    "bot_name": BOT_NAME,
                    "system_role": SYSTEM_ROLE,
                    "speaking_style": SPEAKING_STYLE,
                    "extra": {"model": VOLC_MODEL}
                },
                "tts": {
                    "speaker": VOLC_SPEAKER,
                    "audio_config": {
                        "channel": 1,
                        "format": "pcm_s16le", # MVP 阶段使用 16bit
                        "sample_rate": 24000
                    }
                }
            }
            await volc_ws.send(build_event_frame(100, session_id, start_session_payload))
            
            # 5. 等待 SessionStarted (Event 150)
            while True:
                data = await volc_ws.recv()
                msg_type, event_id, payload = parse_server_frame(data)
                if event_id == 150:
                    logger.info("Session Started")
                    await client_ws.send_json({"type": "session_started"})
                    break
                elif event_id == 153:
                    logger.error(f"Session Failed: {payload}")
                    await client_ws.send_json({"type": "error", "message": "Session Failed"})
                    return
            
            # 6. 发送 SayHello (Event 300)
            await volc_ws.send(build_event_frame(300, session_id, {"content": SAY_HELLO_TEXT}))
            
            # 7. 启动双向转发
            
            # Task A: 前端 -> 豆包
            async def client_to_volc():
                try:
                    while True:
                        message = await client_ws.receive()
                        if "bytes" in message:
                            # 二进制 PCM 数据
                            audio_data = message["bytes"]
                            # 封装为 TaskRequest (200)
                            frame = build_audio_frame(200, session_id, audio_data)
                            await volc_ws.send(frame)
                        elif "text" in message:
                            # 文本控制消息
                            data = json.loads(message["text"])
                            if data.get("action") == "disconnect":
                                return
                except Exception as e:
                    logger.error(f"Client read error: {e}")
                    raise
            
            # Task B: 豆包 -> 前端
            async def volc_to_client():
                try:
                    while True:
                        data = await volc_ws.recv()
                        msg_type, event_id, payload = parse_server_frame(data)
                        
                        if msg_type == 0xB: # Audio-only response
                            if event_id == 352: # TTSResponse
                                await client_ws.send_bytes(payload)
                                
                        elif msg_type == 0x9: # Full-server response
                            if event_id == 450: # ASRInfo (User Speaking)
                                await client_ws.send_json({"type": "user_speaking"})
                            elif event_id == 350: # TTSSentenceStart
                                await client_ws.send_json({"type": "tts_start", "text": payload.get("text", "")})
                            elif event_id == 359: # TTSEnded
                                await client_ws.send_json({"type": "tts_end"})
                            elif event_id == 451: # ASRResponse
                                await client_ws.send_json({"type": "asr", "text": payload.get("text", ""), "is_interim": True})
                            elif event_id == 550: # ChatResponse
                                await client_ws.send_json({"type": "chat", "text": payload.get("text", "")})
                            elif event_id == 152: # SessionFinished
                                await client_ws.send_json({"type": "session_ended"})
                                return
                        
                        elif msg_type == 0xF: # Error
                            logger.error(f"Volc Error: {payload}")
                            await client_ws.send_json({"type": "error", "message": str(payload)})
                            
                except Exception as e:
                    logger.error(f"Volc read error: {e}")
                    raise

            # 并发运行
            try:
                done, pending = await asyncio.wait(
                    [asyncio.create_task(client_to_volc()), asyncio.create_task(volc_to_client())],
                    return_when=asyncio.FIRST_COMPLETED
                )
                for task in pending:
                    task.cancel()
            except Exception as e:
                logger.error(f"Task error: {e}")
                
            # 断开连接处理
            try:
                # Send FinishSession (102)
                await volc_ws.send(build_event_frame(102, session_id, {}))
                # Send FinishConnection (2)
                await volc_ws.send(build_event_frame(2, None, {}))
            except:
                pass

    except Exception as e:
        logger.error(f"Connection error: {e}")
        try:
            await client_ws.send_json({"type": "error", "message": str(e)})
        except:
            pass
    finally:
        logger.info("Client disconnected")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
