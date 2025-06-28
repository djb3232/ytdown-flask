<!DOCTYPE html>
<html>
<head>
    <title>YouTube Downloader</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
</head>
<body class="bg-light">
<div class="container mt-5">
    <h2>YouTube Video & Audio Downloader</h2>
    <form action="/start-download" method="POST">
        <div class="mb-3">
            <label class="form-label">YouTube URL</label>
            <input type="url" name="url" class="form-control" required>
        </div>
        <div class="mb-3">
            <label class="form-label">Format</label><br>
            <div class="form-check form-check-inline">
                <input class="form-check-input" type="radio" name="format" value="video" checked>
                <label class="form-check-label">Video (MP4)</label>
            </div>
            <div class="form-check form-check-inline">
                <input class="form-check-input" type="radio" name="format" value="audio">
                <label class="form-check-label">Audio (MP3)</label>
            </div>
        </div>
        <button type="submit" class="btn btn-primary">Download</button>
    </form>
    <div class="progress mt-3" style="height: 25px;">
        <div id="progressBar" class="progress-bar" role="progressbar" style="width: 0%;">0%</div>
    </div>
</div>

<script>
document.querySelector("form").onsubmit = function (e) {
    e.preventDefault();
    const form = e.target;
    const data = new FormData(form);
    const progressBar = document.getElementById("progressBar");

    fetch("/start-download", {
        method: "POST",
        body: data
    }).then(res => res.json())
      .then(json => {
        const downloadId = json.download_id;
        const poll = setInterval(() => {
          fetch(`/progress/${downloadId}`)
            .then(res => res.json())
            .then(data => {
              let percent = data.progress;
              progressBar.style.width = percent + "%";
              progressBar.textContent = percent + "%";
              if (percent >= 100) {
                clearInterval(poll);
                window.location = "/downloads/" + downloadId;
              }
            });
        }, 1000);
    });
}
</script>
</body>
</html>
