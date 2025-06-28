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
        for key in progress_map:
            progress_map[key] = percent
    except Exception as e:
        print(f"[PROGRESS ERROR] {e}")

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/start-download', methods=['POST'])
def start_download():
    url = request.form.get('url')
    format_type = request.form.get('format')
    if not url or not format_type:
        return jsonify({"error": "Missing URL or format"}), 400

    try:
        yt = YouTube(url, on_progress_callback=on_progress)
        file_id = str(uuid.uuid4())
        base_path = os.path.join(DOWNLOAD_DIR, file_id)
        progress_map[file_id] = 0

        # Extract clean title
        safe_title = "".join(c if c.isalnum() else "_" for c in yt.title.strip())[:60]
        tag = "[vdwn.net]"

        if format_type == 'audio':
            stream = yt.streams.filter(only_audio=True).first()
            mp4_path = f"{base_path}.mp4"
            stream.download(filename=mp4_path)

            mp3_filename = f"{safe_title}_{tag}.mp3"
            mp3_path = os.path.join(DOWNLOAD_DIR, mp3_filename)

            subprocess.run([
                "ffmpeg", "-y", "-i", mp4_path,
                "-vn", "-ab", "192k", "-ar", "44100",
                "-f", "mp3", mp3_path
            ], check=True)

            os.remove(mp4_path)
            schedule_file_delete(mp3_path)
            return jsonify({"download_id": mp3_filename}), 200

        else:
            stream = yt.streams.filter(progressive=True, file_extension='mp4')                               .order_by('resolution').desc().first()

            mp4_filename = f"{safe_title}_{tag}.mp4"
            mp4_path = os.path.join(DOWNLOAD_DIR, mp4_filename)

            stream.download(filename=mp4_path)
            schedule_file_delete(mp4_path)
            return jsonify({"download_id": mp4_filename}), 200

    except Exception as e:
        print(f"[ERROR] Download failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/progress/<download_id>')
def get_progress(download_id):
    file_id = download_id.rsplit('.', 1)[0].split('_')[0]  # strip tag and ext
    return jsonify({"progress": progress_map.get(file_id, 0)}), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')