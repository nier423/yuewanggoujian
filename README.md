# 越王勾践 · 沉浸式历史对话 (King Goujian Immersive Interaction)

> "卧薪尝胆，三千越甲可吞吴。"

这是一个结合了**生成式艺术 (Generative Art)** 与 **AI 实时语音交互** 的 Web 实验项目。通过 WebSocket 连接火山引擎豆包模型，让用户能够跨越 2500 年的历史长河，与越王勾践进行一场沉浸式的实时语音对话。

## 🎨 视觉设计

本项目采用了 **Makemepulse** 风格的新中式极简设计：

*   **流体时光 (Flow Field)**: 基于 Simplex Noise 的动态粒子流场，模拟水墨与时光的流动。
*   **液态金属文字**: 使用 SVG `feTurbulence` 滤镜实现的标题动态效果，呈现青铜熔铸的质感。
*   **交互式印章**: "叩问"与"断"的印章交互，控制对话的开启与结束。
*   **音频可视化**: 粒子流场会随着语音能量产生扰动，实现视觉与听觉的共鸣。

## 🛠️ 技术栈

*   **Frontend**: HTML5 Canvas, Web Audio API, WebSocket
*   **Backend**: Python FastAPI, Uvicorn
*   **AI Service**: Volcengine (火山引擎) - 语音识别 (ASR) + 语音合成 (TTS) + 大模型对话 (LLM)

## 🚀 快速开始

### 1. 环境准备
确保已安装 Python 3.8+。

```bash
# 克隆仓库
git clone https://github.com/nier423/yuewanggoujian.git
cd yuewanggoujian

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量 (可选)
项目默认包含测试用的 Key，但建议在生产环境中配置自己的火山引擎密钥：

Windows (PowerShell):
```powershell
$env:VOLC_APP_ID="your_app_id"
$env:VOLC_ACCESS_KEY="your_access_key"
```

### 3. 启动服务
```bash
# Windows 一键启动
start.bat

# 或者手动启动
python -m uvicorn main:app --host 0.0.0.0 --port 8001
```

### 4. 体验
浏览器访问: `http://localhost:8001`

## 📂 目录结构

*   `index.html`: 前端入口，包含 Canvas 动画逻辑与 WebSocket 通信。
*   `main.py`: 后端服务，处理 WebSocket 连接与火山引擎接口转发。
*   `integration_test.py`: 自动化集成测试脚本。
*   `Procfile`: Render 部署配置文件。

## 📜 License
MIT
