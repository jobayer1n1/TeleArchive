const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("fileInput");
const pickButton = document.getElementById("pickButton");
const fileList = document.getElementById("fileList");
const searchInput = document.getElementById("searchInput");
const logoutBtn = document.getElementById("logoutBtn");
const toast = document.getElementById("toast");

const escapeHtml = (value) =>
  String(value).replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));

const apiFetch = (url, options = {}) => {
  return fetch(url, { ...options, credentials: "same-origin" });
};

function showToast(message, isError) {
  toast.textContent = message;
  toast.classList.toggle("error", !!isError);
  toast.style.display = "block";
  setTimeout(() => {
    toast.style.display = "none";
  }, 3200);
}

logoutBtn.addEventListener("click", () => {
  window.location = "/logout";
});

let currentSort = "date";
let currentDir = "desc";
let allFiles = [];
let currentQuery = "";

async function refreshFiles() {
  const res = await apiFetch(`/api/files?sort=${currentSort}&dir=${currentDir}`);
  const data = await res.json();
  if (!data.ok) {
    showToast(data.error || "Failed to load files", true);
    return;
  }
  allFiles = data.files || [];
  renderFiles();
}

function renderFiles() {
  const q = currentQuery.trim().toLowerCase();
  const visibleFiles = q ? allFiles.filter((f) => f.name.toLowerCase().includes(q)) : allFiles;
  fileList.innerHTML = "";
  if (!visibleFiles.length) {
    fileList.innerHTML = allFiles.length ? "<div class='empty'>No matching files.</div>" : "<div class='empty'>No uploads yet.</div>";
    return;
  }
  for (const file of visibleFiles) {
    const el = document.createElement("div");
    el.className = "file";

    const left = document.createElement("div");
    left.innerHTML = `<strong title="${escapeHtml(file.name)}">${escapeHtml(file.name)}</strong><small>${file.size_human} | ${file.uploaded_at}</small>`;
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
      const resp = await apiFetch("/delete/" + file.id, { method: "POST" });
      const delData = await resp.json();
      if (!delData.ok) {
        showToast(delData.error || "Delete failed", true);
        return;
      }
      showToast("Deleted.");
      refreshFiles();
    });

    const share = document.createElement("button");
    if (file.share_token) {
      share.textContent = "Revoke";
      share.addEventListener("click", async () => {
        const resp = await apiFetch("/api/share/" + file.id + "/revoke", { method: "POST" });
        const data = await resp.json();
        if (!data.ok) {
          showToast(data.error || "Revoke failed", true);
          return;
        }
        showToast("Share link revoked.");
        refreshFiles();
      });
    } else {
      share.textContent = "Share";
      share.addEventListener("click", async () => {
        const resp = await apiFetch("/api/share/" + file.id, { method: "POST" });
        const data = await resp.json();
        if (!data.ok) {
          showToast(data.error || "Share failed", true);
          return;
        }
        try {
          await navigator.clipboard.writeText(data.link);
          showToast("Share link copied!");
        } catch (e) {
          const input = document.createElement("input");
          input.value = data.link;
          document.body.appendChild(input);
          input.select();
          input.setSelectionRange(0, input.value.length);
          try {
            document.execCommand("copy");
            showToast("Share link copied!");
          } catch (err) {
            showToast(data.link);
          }
          input.remove();
        }
        refreshFiles();
      });
    }

    right.appendChild(download);
    right.appendChild(share);
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

  const startResp = await apiFetch(`/api/download/${file.id}/start`, { method: "POST" });
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
    const statusResp = await apiFetch(`/api/download/${file.id}/status`);
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
  left.innerHTML = `<strong title="${escapeHtml(file.name)}">${escapeHtml(file.name)}</strong><small>${formatBytes(file.size)} | queued</small>`;
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
    const res = await apiFetch("/api/progress/" + taskId);
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
      smoothRate = smoothRate ? smoothRate * (1 - smoothing) + rate * smoothing : rate;
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
  const clientId = window.crypto && crypto.randomUUID ? crypto.randomUUID() : String(Date.now() + Math.random());
  const row = createUploadRow(file);

  const form = new FormData();
  form.append("files", file);
  form.append("client_id", clientId);

  const xhr = new XMLHttpRequest();
  xhr.open("POST", "/upload", true);
  xhr.withCredentials = true;

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

searchInput.addEventListener("input", (e) => {
  currentQuery = e.target.value || "";
  renderFiles();
});

refreshFiles();
