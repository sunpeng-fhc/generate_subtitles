import os
import datetime
import subprocess
import time
import threading
from flask import Flask, request, jsonify, render_template, send_file
from faster_whisper import WhisperModel
import requests as http_requests

# ============================================================
# 配置
# ============================================================
OLLAMA_URL   = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:32b"

# 默认节目背景（用户可在网页上修改）
DEFAULT_CONTEXT = "这是一档英语学习播客，主持人用简单英语讨论日常生活话题，面向中级英语学习者。"

# 每批翻译句子数（32b 模型推荐 15）
BATCH_SIZE = 15

app = Flask(__name__)

# ============================================================
# 全局任务状态
# ============================================================
job_status: dict = {}


# ============================================================
# 启动 Ollama
# ============================================================
def ensure_ollama_running():
    try:
        http_requests.get("http://localhost:11434", timeout=2)
        print("✅  Ollama 已在运行")
    except Exception:
        print("⚙️   Ollama 未运行，正在自动启动...")
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(4)


# ============================================================
# 工具函数
# ============================================================
def get_audio_duration(file_path: str) -> float:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            file_path,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    try:
        return float(result.stdout)
    except ValueError:
        return 0.0


def format_time(seconds: float) -> str:
    h  = int(seconds // 3600)
    m  = int((seconds % 3600) // 60)
    s  = int(seconds % 60)
    ms = int((seconds * 1000) % 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


# ============================================================
# 批量翻译
# ============================================================
def translate_batch(texts: list, context: str) -> list:
    """
    15 句一批发给模型，有上下文，翻译更自然准确。
    """
    if not texts:
        return []

    numbered = "\n".join(f"{i+1}. {t}" for i, t in enumerate(texts))

    prompt = (
        f"背景：{context}\n\n"
        "你是一位专业的英语播客字幕翻译。\n"
        "请将以下编号的英文字幕逐条翻译成自然流畅的中文口语。\n\n"
        "翻译要求：\n"
        "- 符合中文表达习惯，不要逐字直译\n"
        "- 口语化，像中文播客一样自然流畅\n"
        "- 专有名词、人名保留英文\n"
        "- 保留原始编号，每条单独一行\n"
        "- 只输出「编号. 中文翻译」，不要任何解释或多余内容\n\n"
        "输出格式示例：\n"
        "1. 中文翻译内容\n"
        "2. 中文翻译内容\n\n"
        f"原文：\n{numbered}"
    )

    for attempt in range(3):
        try:
            resp = http_requests.post(
                OLLAMA_URL,
                json={
                    "model":  OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3, "num_predict": 2048},
                },
                timeout=180,
            )
            raw = resp.json().get("response", "").strip()

            results = {}
            for line in raw.splitlines():
                line = line.strip()
                if not line:
                    continue
                if ". " in line:
                    parts = line.split(". ", 1)
                    if parts[0].isdigit():
                        results[int(parts[0]) - 1] = parts[1].strip()

            return [results.get(i, "【翻译失败】") for i in range(len(texts))]

        except Exception as e:
            print(f"  批量翻译失败 (尝试 {attempt+1}/3): {e}")
            time.sleep(2)

    return ["【翻译失败】"] * len(texts)


# ============================================================
# 生成学习笔记
# ============================================================
def generate_study_notes(all_segments: list, context: str, level: str) -> str:
    """
    读取全文，生成适合目标水平的英语学习笔记（Markdown 格式）。
    包含：内容概要、重点词汇、重点词组短语、实用句型、语法小贴士。
    """
    full_text = " ".join(seg["text"] for seg in all_segments)

    level_map = {
        "A2": "英语入门至初级（A2 水平），刚开始学英语，只认识基础词汇和简单句型，需要详细解释",
        "B1": "英语中级（B1 水平），能理解日常对话，掌握基础语法，但遇到复杂句型仍需解释",
        "B2": "英语中高级（B2 水平），有较强语法基础，希望学习地道表达和高频短语",
    }
    level_desc = level_map.get(level, level_map["B1"])

    prompt = (
        f"背景：{context}\n\n"
        f"目标学习者：{level_desc}\n\n"
        "以下是一段英语播客的完整文本：\n\n"
        f"{full_text}\n\n"
        "请根据以上内容，用中文生成一份结构清晰的英语学习笔记，严格按照下面的格式输出：\n\n"
        "## 📖 内容概要\n"
        "用 2-3 句中文概括这期播客讲了什么内容和核心观点。\n\n"
        "## 📝 重点词汇（10-15 个）\n"
        "从文中挑选适合该水平的重点单词，每个格式如下：\n"
        "- **单词** /音标/：中文释义\n"
        "  > 原文例句 → 中文翻译\n\n"
        "## 💬 重点词组和短语（8-12 个）\n"
        "挑选文中出现的地道英语词组和短语，每个格式如下：\n"
        "- **词组/短语**：中文释义\n"
        "  > 原文例句 → 中文翻译\n\n"
        "## 🔤 实用句型（5-8 个）\n"
        "挑选文中有代表性的句型结构，每个格式如下：\n"
        "- **句型**：使用场景说明\n"
        "  > 例：原文句子 → 中文翻译\n\n"
        "## 📌 语法小贴士（2-3 个）\n"
        "针对文中出现的语法现象，用对该水平学习者友好的方式解释，举例说明。\n\n"
        "要求：内容准确，语言亲切易懂，例句尽量来自原文，不要编造。"
    )

    for attempt in range(3):
        try:
            resp = http_requests.post(
                OLLAMA_URL,
                json={
                    "model":  OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.5, "num_predict": 4096},
                },
                timeout=300,
            )
            result = resp.json().get("response", "").strip()
            if result:
                return result
        except Exception as e:
            print(f"  学习笔记生成失败 (尝试 {attempt+1}/3): {e}")
            time.sleep(2)

    return "【学习笔记生成失败，请重试】"


# ============================================================
# 后台处理任务
# ============================================================
def process_audio(
    job_id,
    audio_path,
    model_size,
    segment_time,
    output_mode,
    context="",
    study_level="B1",
    gen_notes=True,
):
    def update(stage, progress, message):
        job_status[job_id].update({
            "stage":    stage,
            "progress": progress,
            "message":  message,
        })

    podcast_context = context.strip() if context.strip() else DEFAULT_CONTEXT

    job_status[job_id] = {
        "stage": "queued", "progress": 0,
        "message": "任务已加入队列...",
        "done": False, "error": None, "files": [],
    }

    try:
        output_dir = os.path.dirname(audio_path)
        audio_name = os.path.splitext(os.path.basename(audio_path))[0]
        timestamp  = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        english_srt   = os.path.join(output_dir, f"{audio_name}_en_{timestamp}.srt")
        bilingual_srt = os.path.join(output_dir, f"{audio_name}_双语_{timestamp}.srt")
        notes_md      = os.path.join(output_dir, f"{audio_name}_学习笔记_{timestamp}.md")

        # ── Step 1：分析音频时长 ──────────────────────────────────
        update("analyzing", 5, "正在分析音频文件...")
        audio_duration = get_audio_duration(audio_path)

        # ── Step 2：长音频分段 ────────────────────────────────────
        segment_files = []
        if audio_duration > segment_time:
            update("splitting", 10,
                   f"音频较长（{audio_duration:.0f} 秒），正在分段处理...")
            pattern = os.path.join(output_dir, "part_%03d.mp3")
            subprocess.run(
                [
                    "ffmpeg", "-y", "-i", audio_path,
                    "-f", "segment",
                    "-segment_time", str(segment_time),
                    "-c", "copy", pattern,
                ],
                capture_output=True,
            )
            segment_files = sorted([
                os.path.join(output_dir, f)
                for f in os.listdir(output_dir)
                if f.startswith("part_") and f.endswith(".mp3")
            ])
        else:
            segment_files = [audio_path]

        # ── Step 3：加载 Whisper 模型 ─────────────────────────────
        update("loading_model", 20, f"正在加载 Whisper {model_size} 模型...")
        model = WhisperModel(model_size, device="auto", compute_type="auto")

        # ── Step 4：语音识别 ──────────────────────────────────────
        all_segments = []
        offset     = 0.0
        total_segs = len(segment_files)

        for idx, seg_file in enumerate(segment_files):
            pct = 20 + int((idx / total_segs) * 40)
            update("transcribing", pct,
                   f"正在识别语音... ({idx+1}/{total_segs})")
            segments, _ = model.transcribe(
                seg_file,
                beam_size=5,
                language="en",
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500),
            )
            for seg in segments:
                all_segments.append({
                    "start": seg.start + offset,
                    "end":   seg.end   + offset,
                    "text":  seg.text.strip(),
                })
            offset += segment_time

        result_files = []

        # ── Step 5：生成英文字幕 ──────────────────────────────────
        if output_mode in ("english", "both"):
            update("writing_en", 62, "正在生成英文字幕...")
            with open(english_srt, "w", encoding="utf-8") as f:
                for i, seg in enumerate(all_segments):
                    f.write(
                        f"{i+1}\n"
                        f"{format_time(seg['start'])} --> {format_time(seg['end'])}\n"
                        f"{seg['text']}\n\n"
                    )
            result_files.append(english_srt)

        # ── Step 6：批量翻译 + 双语字幕 ──────────────────────────
        if output_mode in ("bilingual", "both"):
            total = len(all_segments)
            all_translations = []

            for batch_start in range(0, total, BATCH_SIZE):
                batch_end   = min(batch_start + BATCH_SIZE, total)
                batch_texts = [all_segments[i]["text"]
                               for i in range(batch_start, batch_end)]
                pct = 65 + int((batch_start / total) * 25)
                update("translating", pct,
                       f"正在翻译字幕... ({batch_start+1}–{batch_end} / {total})")
                all_translations.extend(
                    translate_batch(batch_texts, podcast_context)
                )

            update("writing_bilingual", 92, "正在生成双语字幕文件...")
            with open(bilingual_srt, "w", encoding="utf-8") as f:
                for i, seg in enumerate(all_segments):
                    en = seg["text"]
                    zh = all_translations[i] if i < len(all_translations) else "【翻译失败】"
                    f.write(
                        f"{i+1}\n"
                        f"{format_time(seg['start'])} --> {format_time(seg['end'])}\n"
                        f"{en}\n"
                        f"{zh}\n\n"
                    )
            result_files.append(bilingual_srt)

        # ── Step 7：生成学习笔记 ──────────────────────────────────
        if gen_notes and output_mode != "english":
            update("notes", 94,
                   f"正在生成 {study_level} 级别学习笔记，请稍候（这一步约需1-2分钟）...")

            notes_header = (
                f"# 英语学习笔记\n\n"
                f"> 音频文件：{os.path.basename(audio_path)}  \n"
                f"> 生成时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}  \n"
                f"> 学习水平：{study_level}  \n\n"
                "---\n\n"
            )
            notes_content = generate_study_notes(
                all_segments, podcast_context, study_level
            )
            with open(notes_md, "w", encoding="utf-8") as f:
                f.write(notes_header + notes_content)
            result_files.append(notes_md)

        # ── 清理分段临时文件 ──────────────────────────────────────
        for seg_file in segment_files:
            if "part_" in seg_file:
                try:
                    os.remove(seg_file)
                except OSError:
                    pass

        # ── 完成 ──────────────────────────────────────────────────
        job_status[job_id] = {
            "stage": "done", "progress": 100,
            "message": "🎉 全部完成！",
            "done": True, "error": None, "files": result_files,
        }

    except Exception as e:
        job_status[job_id] = {
            "stage": "error", "progress": 0,
            "message": f"处理失败：{e}",
            "done": True, "error": str(e), "files": [],
        }


# ============================================================
# Flask 路由
# ============================================================
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    if "audio" not in request.files:
        return jsonify({"error": "没有上传文件"}), 400

    file = request.files["audio"]
    if not file.filename.lower().endswith((".mp3", ".wav", ".m4a", ".flac")):
        return jsonify({"error": "仅支持 mp3 / wav / m4a / flac 格式"}), 400

    model_size   = request.form.get("model",         "medium")
    segment_time = int(request.form.get("segment_time", 600))
    output_mode  = request.form.get("output_mode",   "both")
    context      = request.form.get("context",       "")
    study_level  = request.form.get("study_level",   "B1")
    gen_notes    = request.form.get("gen_notes",     "true").lower() == "true"

    save_dir  = os.path.join(os.path.dirname(__file__), "uploads")
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, file.filename)
    file.save(save_path)

    job_id = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
    job_status[job_id] = {
        "stage": "queued", "progress": 0,
        "message": "任务已加入队列...",
        "done": False, "error": None, "files": [],
    }

    threading.Thread(
        target=process_audio,
        args=(job_id, save_path, model_size, segment_time,
              output_mode, context, study_level, gen_notes),
        daemon=True,
    ).start()

    return jsonify({"job_id": job_id})


@app.route("/status/<job_id>")
def status(job_id):
    return jsonify(job_status.get(
        job_id, {"error": "任务不存在", "done": True}
    ))


@app.route("/download")
def download():
    path = request.args.get("path", "")
    if not path or not os.path.exists(path):
        return "文件不存在", 404
    return send_file(path, as_attachment=True)


# ============================================================
# 入口
# ============================================================
if __name__ == "__main__":
    ensure_ollama_running()
    print("\n🎙️  字幕生成工具已启动！")
    print(f"🤖  模型：{OLLAMA_MODEL}")
    print("👉  浏览器打开：http://127.0.0.1:5000\n")
    app.run(debug=False, host="127.0.0.1", port=5000)
