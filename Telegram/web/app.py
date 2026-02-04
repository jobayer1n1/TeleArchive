import os
import time
import uuid
import threading
from io import BytesIO

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_file, Response
from werkzeug.utils import secure_filename

from Telegram.teleBot import TelegramFileClient
from Telegram.web.storage import WebStore
from Telegram.web.ui import HTML_PAGE


def _format_bytes(value):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024:
            return f"{value:.1f} {unit}" if unit != "B" else f"{value} {unit}"
        value = value / 1024
    return f"{value:.1f} PB"


def _format_time(ts):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))


def create_app():
    load_dotenv()

    api_id_raw = os.getenv("APP_ID")
    api_id = int(api_id_raw) if api_id_raw else None
    api_hash = os.getenv("APP_HASH")
    channel_link = os.getenv("CHANNEL_LINK")
    session_name = os.getenv("SESSION_NAME")

    if not all([api_id, api_hash, channel_link, session_name]):
        raise RuntimeError("Missing Telegram credentials. Check .env values.")

    client = TelegramFileClient(session_name, api_id, api_hash, channel_link)
    store = WebStore(os.getenv("WEB_DB_PATH", "telegram_web.db"))

    app = Flask(__name__)
    max_upload = os.getenv("WEB_MAX_UPLOAD_BYTES")
    if max_upload:
        app.config["MAX_CONTENT_LENGTH"] = int(max_upload)

    upload_progress = {}
    download_progress = {}
    store_lock = threading.Lock()
    download_lock = threading.Lock()

    @app.get("/")
    def index():
        return HTML_PAGE

    @app.get("/api/files")
    def list_files():
        limit = int(request.args.get("limit", "50"))
        sort = request.args.get("sort", "date")
        direction = request.args.get("dir", "desc")
        if sort not in ("date", "size", "name"):
            sort = "date"
        if direction not in ("asc", "desc"):
            direction = "desc"
        with store_lock:
            rows = store.list_files(limit, sort, direction)
        files = [
            {
                "id": row[0],
                "name": row[1],
                "size_bytes": row[2],
                "size_human": _format_bytes(row[2]),
                "uploaded_at": _format_time(row[3]),
            }
            for row in rows
        ]
        return jsonify(ok=True, files=files)

    @app.get("/api/progress/<task_id>")
    def get_progress(task_id):
        info = upload_progress.get(task_id)
        if not info:
            return jsonify(ok=False, error="Task not found"), 404
        return jsonify(
            ok=True,
            percent=info["percent"],
            done=info["done"],
            error=info.get("error"),
        )

    @app.post("/upload")
    def upload():
        files = request.files.getlist("files")
        if not files:
            return jsonify(ok=False, error="No files provided"), 400
        client_id = request.form.get("client_id")

        def upload_worker(raw, safe_name, fh, task_id):
            try:
                def progress_cb(sent, total, tid=task_id):
                    if total:
                        upload_progress[tid]["percent"] = int((sent / total) * 100)

                telegram_msgs = client.upload_file(
                    BytesIO(raw),
                    fh,
                    safe_name,
                    progress_cb=progress_cb,
                )
                msg_ids = [msg.id for msg in telegram_msgs]
                with store_lock:
                    store.add_file(safe_name, msg_ids, len(raw))
                upload_progress[task_id]["percent"] = 100
                upload_progress[task_id]["done"] = True
            except Exception as exc:
                upload_progress[task_id]["error"] = str(exc)
                upload_progress[task_id]["done"] = True

        tasks = []
        for idx, file in enumerate(files):
            raw = file.read()
            if not raw:
                continue
            safe_name = secure_filename(file.filename) or f"upload_{int(time.time())}.bin"
            fh = int(time.time() * 1000) + idx
            task_id = uuid.uuid4().hex
            upload_progress[task_id] = {"percent": 0, "done": False}
            threading.Thread(
                target=upload_worker,
                args=(raw, safe_name, fh, task_id),
                daemon=True,
            ).start()
            task = {"task_id": task_id, "name": safe_name}
            if client_id:
                task["client_id"] = client_id
            tasks.append(task)

        if not tasks:
            return jsonify(ok=False, error="All provided files were empty"), 400

        return jsonify(ok=True, count=len(tasks), tasks=tasks)

    @app.post("/api/download/<int:file_id>/start")
    def start_download(file_id):
        with store_lock:
            row = store.get_file(file_id)
        if not row:
            return jsonify(ok=False, error="File not found"), 404

        cached = client.get_cached_file(file_id)
        with download_lock:
            existing = download_progress.get(file_id)
            if cached is not None:
                download_progress[file_id] = {"percent": 100, "done": True}
                return jsonify(ok=True, status="cached")
            if existing and not existing.get("done"):
                return jsonify(ok=True, status="in_progress")
            download_progress[file_id] = {"percent": 0, "done": False}

        def worker():
            try:
                def progress_cb(done_bytes, total_bytes):
                    if total_bytes:
                        percent = int((done_bytes / total_bytes) * 100)
                        with download_lock:
                            download_progress[file_id]["percent"] = max(0, min(100, percent))

                client.download_file(
                    file_id,
                    row["msg_ids"],
                    progress_cb=progress_cb,
                    total_size=row["size_bytes"],
                )
                with download_lock:
                    download_progress[file_id]["percent"] = 100
                    download_progress[file_id]["done"] = True
            except Exception as exc:
                with download_lock:
                    download_progress[file_id]["error"] = str(exc)
                    download_progress[file_id]["done"] = True

        threading.Thread(target=worker, daemon=True).start()
        return jsonify(ok=True, status="started")

    @app.get("/api/download/<int:file_id>/status")
    def download_status(file_id):
        with download_lock:
            info = download_progress.get(file_id)
        if not info:
            return jsonify(ok=False, error="Task not found"), 404
        return jsonify(ok=True, **info)

    @app.get("/download/<int:file_id>")
    def download(file_id):
        with store_lock:
            row = store.get_file(file_id)
        if not row:
            return "File not found", 404
        payload = client.download_file(file_id, row["msg_ids"])
        if isinstance(payload, bytearray):
            payload = bytes(payload)
        resp = send_file(
            BytesIO(payload),
            as_attachment=True,
            download_name=row["file_name"],
            mimetype="application/octet-stream",
            max_age=0,
            conditional=False,
        )
        resp.headers["Content-Length"] = str(len(payload))
        resp.headers["Cache-Control"] = "no-store"
        return resp

    @app.post("/delete/<int:file_id>")
    def delete(file_id):
        with store_lock:
            msg_ids = store.delete_file(file_id)
        if msg_ids is None:
            return jsonify(ok=False, error="File not found"), 404
        client.delete_messages(msg_ids)
        return jsonify(ok=True)

    return app


def run_web():
    app = create_app()
    host = os.getenv("WEB_HOST", "0.0.0.0")
    port = int(os.getenv("WEB_PORT", "5000"))
    debug = os.getenv("WEB_DEBUG", "false").lower() == "true"
    app.run(host=host, port=port, debug=debug)
