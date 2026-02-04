HTML_PAGE = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Telegram Drop</title>
    <style>
      :root {
        --bg: #0e1014;
        --panel: #151922;
        --ink: #e9edf5;
        --muted: #96a2b8;
        --accent: #4fe3c1;
        --accent-2: #f6c453;
        --danger: #ff6b6b;
        --shadow: rgba(0, 0, 0, 0.35);
      }

      * { box-sizing: border-box; }
      body {
        margin: 0;
        font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
        background: radial-gradient(circle at 20% 20%, #1b2230 0%, #0e1014 55%);
        color: var(--ink);
        min-height: 100vh;
      }

      .shell {
        max-width: 980px;
        margin: 0 auto;
        padding: 40px 20px 60px;
        display: grid;
        gap: 24px;
      }

      header {
        display: flex;
        flex-wrap: wrap;
        gap: 16px;
        align-items: center;
        justify-content: space-between;
      }

      h1 {
        margin: 0;
        font-size: clamp(1.8rem, 4vw, 2.6rem);
        letter-spacing: 0.02em;
      }

      .status {
        font-size: 0.95rem;
        color: var(--muted);
      }

      .dropzone {
        border: 2px dashed rgba(79, 227, 193, 0.35);
        border-radius: 16px;
        padding: 32px;
        background: linear-gradient(135deg, rgba(79, 227, 193, 0.12), rgba(246, 196, 83, 0.1));
        box-shadow: 0 20px 40px var(--shadow);
        text-align: center;
        transition: transform 0.2s ease, border-color 0.2s ease;
      }

      .dropzone.dragover {
        border-color: var(--accent);
        transform: translateY(-4px);
      }

      .dropzone h2 {
        margin: 0 0 10px;
        font-size: 1.4rem;
      }

      .dropzone p {
        margin: 4px 0;
        color: var(--muted);
      }

      .dropzone button {
        margin-top: 16px;
        padding: 10px 18px;
        background: var(--accent);
        color: #081014;
        font-weight: 600;
        border: none;
        border-radius: 10px;
        cursor: pointer;
      }

      .panel {
        background: var(--panel);
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 16px 36px var(--shadow);
      }

      .panel-header {
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 12px;
      }

      .sort-bar {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
      }

      .sort-bar button {
        padding: 6px 12px;
        border-radius: 999px;
        border: 1px solid rgba(255, 255, 255, 0.12);
        background: rgba(255, 255, 255, 0.04);
        color: var(--ink);
        cursor: pointer;
      }

      .sort-bar button.active {
        border-color: var(--accent);
        color: var(--accent);
      }

      .list {
        display: grid;
        gap: 12px;
      }

      .file {
        display: grid;
        grid-template-columns: 1fr auto;
        gap: 12px;
        padding: 12px;
        background: rgba(255, 255, 255, 0.04);
        border-radius: 12px;
      }

      .file strong { display: block; }
      .file small { color: var(--muted); }

      .file a, .file button {
        color: var(--accent);
        text-decoration: none;
        font-weight: 600;
        background: none;
        border: none;
        cursor: pointer;
        padding: 0;
      }

      .file a:hover, .file button:hover { text-decoration: underline; }

      .row-actions {
        display: flex;
        gap: 12px;
        align-items: center;
      }

      .progress {
        height: 8px;
        background: rgba(255, 255, 255, 0.08);
        border-radius: 99px;
        overflow: hidden;
        margin-top: 8px;
        display: none;
      }

      .progress span {
        display: block;
        height: 100%;
        width: 0%;
        background: linear-gradient(90deg, var(--accent), var(--accent-2));
        transition: width 0.2s ease;
      }

      .progress-label {
        margin-top: 6px;
        color: var(--muted);
        font-size: 0.85rem;
        display: none;
      }

      @media (max-width: 720px) {
        .shell { padding: 28px 14px 44px; }
        .dropzone { padding: 24px; }
        .file { grid-template-columns: 1fr; }
        .row-actions {
          justify-content: flex-start;
          flex-wrap: wrap;
        }
        .row-actions button {
          padding: 8px 12px;
          border-radius: 8px;
          background: rgba(255, 255, 255, 0.06);
        }
      }

      .toast {
        display: none;
        margin-top: 12px;
        padding: 10px 12px;
        border-radius: 10px;
        background: rgba(79, 227, 193, 0.16);
        color: var(--ink);
      }

      .toast.error {
        background: rgba(255, 107, 107, 0.2);
      }
    </style>
  </head>
  <body>
    <div class="shell">
      <header>
        <div>
          <h1>Telegram Drop</h1>
          <div class="status">Drag files here to send them to your channel.</div>
        </div>
      </header>

      <section class="dropzone" id="dropzone">
        <h2>Drop files to upload</h2>
        <p>Or click the button to choose files.</p>
        <button id="pickButton">Select files</button>
        <input id="fileInput" type="file" multiple hidden />
        <div class="toast" id="toast"></div>
      </section>

      <section class="panel">
        <div class="panel-header">
          <h2>All uploads</h2>
          <div class="sort-bar" id="sortBar">
            <button data-sort="date" data-dir="desc" class="active">Date</button>
            <button data-sort="size" data-dir="asc">Size</button>
            <button data-sort="name" data-dir="asc">Alphabetic</button>
          </div>
        </div>
        <div class="list" id="fileList"></div>
      </section>
    </div>

    <script>
      const dropzone = document.getElementById("dropzone");
      const fileInput = document.getElementById("fileInput");
      const pickButton = document.getElementById("pickButton");
      const fileList = document.getElementById("fileList");
      const toast = document.getElementById("toast");

      function showToast(message, isError) {
        toast.textContent = message;
        toast.classList.toggle("error", !!isError);
        toast.style.display = "block";
        setTimeout(() => (toast.style.display = "none"), 3200);
      }

      let currentSort = "date";
      let currentDir = "desc";

      async function refreshFiles() {
        const res = await fetch(`/api/files?sort=${currentSort}&dir=${currentDir}`);
        const data = await res.json();
        if (!data.ok) {
          showToast(data.error || "Failed to load files", true);
          return;
        }
        fileList.innerHTML = "";
        if (!data.files.length) {
          fileList.innerHTML = "<p>No uploads yet.</p>";
          return;
        }
        for (const file of data.files) {
          const el = document.createElement("div");
          el.className = "file";
          const left = document.createElement("div");
          left.innerHTML = `<strong>${file.name}</strong><small>${file.size_human} | ${file.uploaded_at}</small>`;
          const progress = document.createElement("div");
          progress.className = "progress";
          const bar = document.createElement("span");
          progress.appendChild(bar);
          left.appendChild(progress);
          const progressLabel = document.createElement("div");
          progressLabel.className = "progress-label";
          left.appendChild(progressLabel);

          const right = document.createElement("div");
          right.className = "row-actions";
          const download = document.createElement("button");
          download.textContent = "Download";
          download.addEventListener("click", async () => {
            await downloadWithProgress(file, progress, bar, progressLabel);
          });

          const del = document.createElement("button");
          del.textContent = "Delete";
          del.addEventListener("click", async () => {
            if (!confirm("Delete this file from Telegram and the list?")) return;
            const resp = await fetch("/delete/" + file.id, { method: "POST" });
            const delData = await resp.json();
            if (!delData.ok) {
              showToast(delData.error || "Delete failed", true);
              return;
            }
            showToast("Deleted.");
            refreshFiles();
          });

          right.appendChild(download);
          right.appendChild(del);

          el.appendChild(left);
          el.appendChild(right);
          fileList.appendChild(el);
        }
      }

      async function downloadWithProgress(file, progressEl, bar, labelEl) {
        bar.style.width = "0%";
        progressEl.style.display = "block";
        labelEl.style.display = "block";
        labelEl.textContent = "Downloading... 0 KB/s";

        const startResp = await fetch(`/api/download/${file.id}/start`, { method: "POST" });
        const startData = await startResp.json();
        if (!startData.ok) {
          showToast(startData.error || "Download failed", true);
          progressEl.style.display = "none";
          labelEl.style.display = "none";
          return;
        }

        let lastPercent = 0;
        let lastTime = performance.now();
        const totalBytes = file.size_bytes || 0;

        const timer = setInterval(async () => {
          const statusResp = await fetch(`/api/download/${file.id}/status`);
          const statusData = await statusResp.json();
          if (!statusData.ok) {
            clearInterval(timer);
            showToast(statusData.error || "Download failed", true);
            progressEl.style.display = "none";
            labelEl.style.display = "none";
            return;
          }

          const percent = statusData.percent || 0;
          bar.style.width = percent + "%";

          const now = performance.now();
          const elapsed = (now - lastTime) / 1000;
          if (elapsed >= 0.3 && totalBytes) {
            const bytesNow = (percent / 100) * totalBytes;
            const bytesPrev = (lastPercent / 100) * totalBytes;
            const rate = (bytesNow - bytesPrev) / elapsed;
            labelEl.textContent = `Downloading... ${formatRate(rate)}`;
            lastPercent = percent;
            lastTime = now;
          }

          if (statusData.error) {
            clearInterval(timer);
            showToast(statusData.error, true);
            progressEl.style.display = "none";
            labelEl.style.display = "none";
            return;
          }

          if (statusData.done) {
            clearInterval(timer);
            bar.style.width = "100%";
            labelEl.textContent = "Downloading... done";
            window.location = "/download/" + file.id;
            setTimeout(() => {
              progressEl.style.display = "none";
              bar.style.width = "0%";
              labelEl.style.display = "none";
              labelEl.textContent = "";
            }, 400);
          }
        }, 600);
      }

      function createUploadRow(file) {
        const el = document.createElement("div");
        el.className = "file";
        const left = document.createElement("div");
        left.innerHTML = `<strong>${file.name}</strong><small>${formatBytes(file.size)} | queued</small>`;
        const progress = document.createElement("div");
        progress.className = "progress";
        const bar = document.createElement("span");
        progress.appendChild(bar);
        progress.style.display = "block";
        left.appendChild(progress);
        const progressLabel = document.createElement("div");
        progressLabel.className = "progress-label";
        progressLabel.style.display = "block";
        progressLabel.textContent = "Preparing...";
        left.appendChild(progressLabel);
        el.appendChild(left);
        fileList.prepend(el);
        return { el, progress, bar, progressLabel };
      }

      function pollTelegramUpload(taskId, row, totalBytes) {
        let lastPercent = 0;
        let lastTime = performance.now();
        let smoothRate = 0;
        const smoothing = 0.25;
        const timer = setInterval(async () => {
          const res = await fetch("/api/progress/" + taskId);
          const data = await res.json();
          if (!data.ok) {
            clearInterval(timer);
            showToast(data.error || "Upload failed", true);
            row.progress.style.display = "none";
            row.progressLabel.style.display = "none";
            return;
          }
          row.bar.style.width = data.percent + "%";
          const now = performance.now();
          const elapsed = (now - lastTime) / 1000;
          if (elapsed >= 0.3 && totalBytes) {
            const bytesNow = (data.percent / 100) * totalBytes;
            const bytesPrev = (lastPercent / 100) * totalBytes;
            const rate = Math.max(0, (bytesNow - bytesPrev) / elapsed);
            smoothRate = smoothRate ? (smoothRate * (1 - smoothing) + rate * smoothing) : rate;
            row.progressLabel.textContent = `Uploading to Telegram... ${formatRate(smoothRate)}`;
            lastPercent = data.percent;
            lastTime = now;
          }
          if (data.error) {
            showToast(data.error, true);
            clearInterval(timer);
            row.progress.style.display = "none";
            row.progressLabel.style.display = "none";
            return;
          }
          if (data.done) {
            clearInterval(timer);
            row.el.remove();
            refreshFiles();
          }
        }, 300);
      }

      function uploadSingleFile(file) {
        const clientId = (window.crypto && crypto.randomUUID) ? crypto.randomUUID() : String(Date.now() + Math.random());
        const row = createUploadRow(file);

        const form = new FormData();
        form.append("files", file);
        form.append("client_id", clientId);

        const xhr = new XMLHttpRequest();
        xhr.open("POST", "/upload", true);

        let lastBytes = 0;
        let lastTime = performance.now();

        xhr.upload.onprogress = (event) => {
          row.progressLabel.textContent = "Uploading to server...";
          if (event.lengthComputable) {
            const percent = Math.min(100, Math.round((event.loaded / event.total) * 100));
            row.bar.style.width = percent + "%";
          }
          const now = performance.now();
          const elapsed = (now - lastTime) / 1000;
          if (elapsed >= 0.2) {
            const rate = (event.loaded - lastBytes) / elapsed;
            row.progressLabel.textContent = `Uploading to server... ${formatRate(rate)}`;
            lastBytes = event.loaded;
            lastTime = now;
          }
        };

        xhr.onerror = () => {
          showToast("Upload failed", true);
          row.progress.style.display = "none";
          row.progressLabel.style.display = "none";
        };

        xhr.onload = () => {
          if (xhr.status < 200 || xhr.status >= 300) {
            showToast("Upload failed", true);
            row.progress.style.display = "none";
            row.progressLabel.style.display = "none";
            return;
          }
          let data = null;
          try {
            data = JSON.parse(xhr.responseText);
          } catch (e) {
            showToast("Upload failed", true);
            row.progress.style.display = "none";
            row.progressLabel.style.display = "none";
            return;
          }
          if (!data.ok || !data.tasks || !data.tasks.length) {
            showToast(data && data.error ? data.error : "Upload failed", true);
            row.progress.style.display = "none";
            row.progressLabel.style.display = "none";
            return;
          }
          row.progressLabel.textContent = "Processing...";
          pollTelegramUpload(data.tasks[0].task_id, row, file.size);
        };

        xhr.send(form);
      }

      function formatBytes(value) {
        const units = ["B", "KB", "MB", "GB", "TB"];
        let size = value;
        let unit = 0;
        while (size >= 1024 && unit < units.length - 1) {
          size /= 1024;
          unit += 1;
        }
        return `${size.toFixed(unit === 0 ? 0 : 1)} ${units[unit]}`;
      }

      function formatRate(bytesPerSecond) {
        if (!Number.isFinite(bytesPerSecond) || bytesPerSecond <= 0) return "0 KB/s";
        const units = ["B/s", "KB/s", "MB/s", "GB/s"];
        let value = bytesPerSecond;
        let unit = 0;
        while (value >= 1024 && unit < units.length - 1) {
          value /= 1024;
          unit += 1;
        }
        return `${value.toFixed(1)} ${units[unit]}`;
      }

      async function uploadFiles(files) {
        for (const f of files) {
          if (f.size > 0) {
            uploadSingleFile(f);
          }
        }
      }

      dropzone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropzone.classList.add("dragover");
      });

      dropzone.addEventListener("dragleave", () => {
        dropzone.classList.remove("dragover");
      });

      dropzone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropzone.classList.remove("dragover");
        if (e.dataTransfer.files.length) {
          uploadFiles(e.dataTransfer.files);
        }
      });

      pickButton.addEventListener("click", () => fileInput.click());
      fileInput.addEventListener("change", () => {
        if (fileInput.files.length) {
          uploadFiles(fileInput.files);
          fileInput.value = "";
        }
      });

      const sortBar = document.getElementById("sortBar");
      sortBar.addEventListener("click", (e) => {
        const btn = e.target.closest("button");
        if (!btn) return;
        currentSort = btn.dataset.sort;
        currentDir = btn.dataset.dir;
        sortBar.querySelectorAll("button").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        refreshFiles();
      });

      refreshFiles();
    </script>
  </body>
</html>
"""
