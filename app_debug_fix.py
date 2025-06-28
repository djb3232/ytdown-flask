from flask import Flask, render_template, request, send_file, jsonify
from pytube import YouTube
import os
import uuid
import threading
import time
import subprocess

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

def on_progress(stream, chunk, bytes_remaining):
    try:
        total = stream.filesize or 1
        downloaded = total - bytes_remaining
        percent = int(downloaded / total * 100)
        for key in list(progress_map.keys()):
            progress_map[key] = percent
            if percent >= 100:
                progress_map.pop(key, None)
    except Exception as e:
        print(f"[PROGRESS ERROR] {e}")

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

    if not url or not fmt:
        return jsonify({"error": "Missing URL or format"}), 400

    try:
        yt = YouTube(url, on_progress_callback=on_progress)
        file_id = str(uuid.uuid4())
        base_path = os.path.join(DOWNLOAD_DIR, file_id)
        progress_map[file_id] = 0

        safe_title = "".join(c if c.isalnum() else "_" for c in yt.title.strip())[:60]
        tag = "[vdwn.net]"

        if fmt == 'audio':
            audio_streams = yt.streams.filter(only_audio=True).order_by('abr').desc()
            if quality == 'low':
                stream = audio_streams.last()
            elif quality == 'medium':
                mid = len(audio_streams) // 2
                stream = audio_streams[mid]
            else:
                stream = audio_streams.first()

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
            video_streams = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution')
            if quality == 'low':
                stream = video_streams.first()
            elif quality == 'medium':
                mid = len(video_streams) // 2
                stream = video_streams[mid]
            else:
                stream = video_streams.last()

            final_filename = f"{file_id}_{safe_title}_{tag}.mp4"
            final_path = os.path.join(DOWNLOAD_DIR, final_filename)

            stream.download(filename=final_path)
            schedule_file_delete(final_path)
            return jsonify({"download_id": final_filename}), 200

    except Exception as e:
        print(f"[ERROR] Download failed: {e}")
        return jsonify({"error": str(e)}), 500

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