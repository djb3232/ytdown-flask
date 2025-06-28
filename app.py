from flask import Flask, render_template, request, send_file, redirect, url_for, flash, jsonify
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
            print(f"Cleanup failed: {e}")
    threading.Thread(target=delete_later, daemon=True).start()

def on_progress(stream, chunk, bytes_remaining):
    total_size = stream.filesize
    bytes_downloaded = total_size - bytes_remaining
    percent = int(bytes_downloaded / total_size * 100)
    progress_map[stream.default_filename] = percent

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/start-download', methods=['POST'])
def start_download():
    url = request.form['url']
    format_type = request.form['format']

    try:
        yt = YouTube(url, on_progress_callback=on_progress)
        file_id = str(uuid.uuid4())
        base_path = os.path.join(DOWNLOAD_DIR, file_id)

        if format_type == 'audio':
            stream = yt.streams.filter(only_audio=True).first()
            mp4_path = f"{base_path}.mp4"
            mp3_path = f"{base_path}.mp3"
            stream.download(filename=mp4_path)
            subprocess.run(["ffmpeg", "-y", "-i", mp4_path, "-vn", "-ab", "192k", "-ar", "44100", "-f", "mp3", mp3_path], check=True)
            os.remove(mp4_path)
            schedule_file_delete(mp3_path)
            return jsonify({"download_id": os.path.basename(mp3_path), "done": True})

        elif format_type == 'video':
            stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
            file_path = f"{base_path}.mp4"
            stream.download(filename=file_path)
            schedule_file_delete(file_path)
            return jsonify({"download_id": os.path.basename(file_path), "done": True})

        return jsonify({"error": "Unsupported format"}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/progress/<download_id>')
def get_progress(download_id):
    progress = progress_map.get(download_id, 0)
    return jsonify({"progress": progress})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')