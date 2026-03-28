# 🎙️ Auto Subtitle + Study Notes Generator
### 自动字幕 + 英语学习笔记生成工具

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python" />
  <img src="https://img.shields.io/badge/Whisper-faster--whisper-green" />
  <img src="https://img.shields.io/badge/LLM-Qwen2.5-orange" />
  <img src="https://img.shields.io/badge/License-MIT-lightgrey" />
  <img src="https://img.shields.io/badge/Platform-macOS%20%7C%20Linux-informational" />
</p>

> 本地运行，完全免费，无需任何 API Key。  
> Runs fully locally — no API key, no cloud, no cost.

---

## ✨ 功能特点 Features

- 🎵 **支持多种音频格式** — MP3 / WAV / M4A / FLAC
- 🗣️ **Whisper 语音识别** — 自动提取英文字幕，准确率高
- 🌐 **批量翻译** — 基于 Ollama 本地大模型（Qwen2.5），15 句一批有上下文，翻译自然流畅
- 📚 **自动生成学习笔记** — 按 A2 / B1 / B2 水平，总结重点词汇、词组、句型和语法
- 💻 **网页操作界面** — 拖拽上传，实时进度，一键下载
- 🔒 **完全本地运行** — 音频和字幕数据不上传任何服务器

---

## 📸 界面预览 Screenshot

> *(可在此处放截图)*

---

## 🚀 快速开始 Quick Start

### 环境要求 Requirements

| 工具 | 版本 | 说明 |
|------|------|------|
| Python | 3.10+ | |
| ffmpeg | 任意 | 音频处理 |
| Ollama | 最新版 | 本地大模型运行环境 |
| 内存 RAM | 建议 16GB+ | 运行 14b/32b 模型 |

---

### 第一步：安装依赖 Install Dependencies

**macOS：**
```bash
brew install ffmpeg
```

**Ubuntu / Debian：**
```bash
sudo apt install ffmpeg
```

**安装 Python 依赖：**
```bash
pip install -r requirements.txt
```

---

### 第二步：安装 Ollama 并拉取模型

前往 [ollama.com](https://ollama.com) 下载安装，然后：

```bash
# 推荐：质量和速度均衡（需要约 10GB 内存）
ollama pull qwen2.5:14b

# 最高质量（需要约 20GB 内存，适合 32GB RAM 设备）
ollama pull qwen2.5:32b
```

---

### 第三步：启动应用

```bash
python app.py
```

打开浏览器访问：**http://127.0.0.1:5000**

---

## ⚙️ 配置说明 Configuration

打开 `app.py`，修改顶部配置项：

```python
# 翻译模型（根据你的内存选择）
OLLAMA_MODEL = "qwen2.5:14b"   # 推荐，速度快
# OLLAMA_MODEL = "qwen2.5:32b" # 质量更高，速度较慢

# 每批翻译句子数（越大速度越快，但需要更多内存）
BATCH_SIZE = 20

# 默认节目背景（可在网页上实时修改）
DEFAULT_CONTEXT = "这是一档英语学习播客，主持人用简单英语讨论日常生活话题。"
```

---

## 📂 输出文件说明 Output Files

处理完成后会在 `uploads/` 目录生成以下文件：

| 文件 | 说明 |
|------|------|
| `xxx_en_时间戳.srt` | 英文字幕文件 |
| `xxx_双语_时间戳.srt` | 中英双语字幕文件 |
| `xxx_学习笔记_时间戳.md` | 英语学习笔记（Markdown 格式） |

学习笔记包含：
- 📖 内容概要
- 📝 重点词汇（带音标和例句）
- 💬 重点词组和短语
- 🔤 实用句型
- 📌 语法小贴士

---

## 🏎️ 速度优化建议 Performance Tips

| 场景 | 建议 |
|------|------|
| 追求速度 | 使用 `qwen2.5:14b`，Whisper 选 `small` |
| 追求质量 | 使用 `qwen2.5:32b`，Whisper 选 `medium` 或 `large-v3` |
| 内存不足 | 降低 `BATCH_SIZE`（改为 10），使用 7b 模型 |
| 长音频（>30分钟）| 调大 `segment_time`（改为 1800） |

---

## 🗂️ 项目结构 Project Structure

```
auto-subtitle/
├── app.py               # 主程序（Flask 后端）
├── requirements.txt     # Python 依赖
├── templates/
│   └── index.html       # 前端页面
├── uploads/             # 上传文件及生成结果（自动创建，不提交 Git）
├── .gitignore
├── LICENSE
└── README.md
```

---

## 🛠️ 技术栈 Tech Stack

- **[faster-whisper](https://github.com/SYSTRAN/faster-whisper)** — 高性能 Whisper 语音识别
- **[Ollama](https://ollama.com)** — 本地大模型推理
- **[Qwen2.5](https://github.com/QwenLM/Qwen2.5)** — 阿里巴巴开源大语言模型
- **[Flask](https://flask.palletsprojects.com)** — Python Web 框架
- **[ffmpeg](https://ffmpeg.org)** — 音频处理

---

## 🤝 贡献 Contributing

欢迎提交 Issue 和 Pull Request！

1. Fork 本项目
2. 创建你的分支：`git checkout -b feature/your-feature`
3. 提交改动：`git commit -m 'Add some feature'`
4. 推送分支：`git push origin feature/your-feature`
5. 提交 Pull Request

---

## 📄 许可证 License

[MIT License](./LICENSE) © 2025
