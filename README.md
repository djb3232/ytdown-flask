# YouTube Downloader (Flask + Pytube)

A simple YouTube downloader for video and audio, built with Flask.

## Features

- Download video (MP4) or audio (MP3)
- Progress bar during download
- Auto-deletes downloaded files after serving

## Run Locally

```bash
docker build -t yt-downloader .
docker run -p 5000:5000 yt-downloader
```

## Deploy on Render

1. Push this repo to GitHub
2. Go to [Render.com](https://render.com)
3. Create a new Web Service, set environment to **Docker**
4. Leave the start command blank (Docker will run CMD)
5. Deploy and test via your Render URL