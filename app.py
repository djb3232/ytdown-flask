from flask import Flask, render_template, request, send_file, jsonify
import os
import uuid
import threading
import time
import subprocess
import traceback
from pytubefix import YouTube  # fallback if yt-dlp fails

app = Flask(__name__)
app.secret_key = "supersecret"
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
progress_map = {}

def schedule_file_delete(path: str, delay_sec: int = 10):
    def delete_later():
        time.sleep(delay_sec)
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception as e:
            print(f"[CLEANUP ERROR] {e}")
    threading.Thread(target=delete_later, daemon=True).start()

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/start-download', methods=['POST'])
def start_download():
    url = request.form.get('url')
    fmt = request.form.get('format')
    quality = request.form.get('quality', 'high')
    audio_fmt = request.form.get('audio_format', 'mp3')

    print(f"[DEBUG] url={url}, format={fmt}, quality={quality}, audio_format={audio_fmt}")

    if not url or ("youtube.com/watch?v=" not in url and "youtu.be/" not in url):
        return jsonify({"error": "Please enter a valid YouTube video URL."}), 400

    try:
        file_id = str(uuid.uuid4())
        safe_title = file_id
        tag = "[vdwn.net]"
        progress_map[file_id] = 0

        output_path = os.path.join(DOWNLOAD_DIR, f"{file_id}_{tag}.%(ext)s")

        # Determine yt-dlp format
        ytdlp_format = "bestaudio/best" if fmt == "audio" else "bestvideo+bestaudio"
        audio_args = []
        if fmt == "audio":
            audio_args = [
                "--extract-audio",
                "--audio-format", audio_fmt,
                "--audio-quality", "0"
            ]

        # Run yt-dlp
        try:
            result = subprocess.run([
                "yt-dlp", "-f", ytdlp_format,
                "-o", output_path,
                *audio_args,
                url
            ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            print("[YT-DLP OUTPUT]", result.stdout)
            print("[YT-DLP ERROR]", result.stderr)
        except subprocess.CalledProcessError as e:
            print("[YT-DLP FAILED]", e.stderr)
            print("[FALLING BACK TO PYTUBEFIX]")
            return fallback_download(url, fmt, quality, audio_fmt)

        # Find the output file
        matched_files = [f for f in os.listdir(DOWNLOAD_DIR) if f.startswith(f"{file_id}_{tag}")]
        if not matched_files:
            return jsonify({"error": "yt-dlp did not produce any file"}), 500

        final_file = os.path.join(DOWNLOAD_DIR, matched_files[0])
        schedule_file_delete(final_file)
        return jsonify({"download_id": matched_files[0]}), 200

    except Exception as e:
        print("[ERROR] yt-dlp + fallback failed:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

def fallback_download(url, fmt, quality, audio_fmt):
    try:
        yt = YouTube(url)
        file_id = str(uuid.uuid4())
        base_path = os.path.join(DOWNLOAD_DIR, file_id)
        safe_title = "".join(c if c.isalnum() else "_" for c in yt.title.strip())[:60]
        tag = "[vdwn.net]"

        if fmt == 'audio':
            stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()
            temp_path = f"{base_path}.mp4"
            stream.download(filename=temp_path)

            final_filename = f"{file_id}_{safe_title}_{tag}.{audio_fmt}"
            final_path = os.path.join(DOWNLOAD_DIR, final_filename)

            subprocess.run([
                "ffmpeg", "-y", "-i", temp_path,
                "-vn", "-ar", "44100",
                final_path
            ], check=True)

            os.remove(temp_path)
            schedule_file_delete(final_path)
            return jsonify({"download_id": final_filename}), 200

        else:
            stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
            final_filename = f"{file_id}_{safe_title}_{tag}.mp4"
            final_path = os.path.join(DOWNLOAD_DIR, final_filename)
            stream.download(filename=final_path)
            schedule_file_delete(final_path)
            return jsonify({"download_id": final_filename}), 200

    except Exception as fallback_err:
        print("[FALLBACK FAILED]", fallback_err)
        traceback.print_exc()
        return jsonify({"error": "Both yt-dlp and fallback failed"}), 500

@app.route('/progress/<download_id>')
def get_progress(download_id):
    file_id = download_id.split('_')[0]
    return jsonify({"progress": progress_map.get(file_id, 0)}), 200

@app.route('/status')
def status():
    return jsonify({
        "active_downloads": len(progress_map),
        "progress_map": progress_map
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
