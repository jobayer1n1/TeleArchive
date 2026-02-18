import os
import time
import uuid
import threading
import secrets
import base64
import hashlib
from io import BytesIO

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_file, Response, session, redirect
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


def _escape_like(value):
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _b64e(data):
    return base64.urlsafe_b64encode(data).decode("utf-8")


def _b64d(data):
    return base64.urlsafe_b64decode(data.encode("utf-8"))


def _hash_passkey(passkey, salt):
    return hashlib.pbkdf2_hmac("sha256", passkey.encode("utf-8"), salt, 200_000)


def _login_page(error=None):
    err_html = f"<div class='error'>{error}</div>" if error else ""
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Login</title>
    <style>
      body {{ margin:0; font-family: 'Segoe UI', Arial, sans-serif; background:#0e1014; color:#e9edf5; }}
      .wrap {{ min-height:100vh; display:flex; align-items:center; justify-content:center; padding:24px; }}
      .card {{ background:#151922; padding:28px; border-radius:16px; width:100%; max-width:420px; box-shadow:0 16px 36px rgba(0,0,0,0.35); }}
      h1 {{ margin:0 0 12px; }}
      p {{ color:#96a2b8; margin:0 0 16px; }}
      input {{ width:100%; padding:10px 12px; border-radius:10px; border:1px solid rgba(255,255,255,0.12); background:rgba(255,255,255,0.04); color:#e9edf5; }}
      button {{ margin-top:14px; width:100%; padding:10px 12px; border-radius:10px; border:none; background:#4fe3c1; color:#081014; font-weight:600; cursor:pointer; }}
      .error {{ background:rgba(255,107,107,0.2); color:#e9edf5; padding:10px; border-radius:10px; margin-bottom:12px; }}
    </style>
  </head>
  <body>
    <div class="wrap">
      <form class="card" method="post" action="/login">
        <h1>TeleArchive Login</h1>
        <p>Enter the passkey to access your files.</p>
        {err_html}
        <input name="passkey" type="password" placeholder="Passkey" required />
        <button type="submit">Enter</button>
      </form>
    </div>
  </body>
</html>"""


def create_app():
    load_dotenv()

    api_id_raw = os.getenv("APP_ID")
    api_id = int(api_id_raw) if api_id_raw else None
    api_hash = os.getenv("APP_HASH")
    channel_link = os.getenv("CHANNEL_LINK")
    session_string = os.getenv("SESSION_STRING")

    if not all([api_id, api_hash, channel_link, session_string]):
        raise RuntimeError("Missing Telegram credentials. Check .env values.")

    client = TelegramFileClient(session_string, api_id, api_hash, channel_link)
    store = WebStore(os.getenv("WEB_DB_PATH", "telegram_web.db"))

    env_passkey = os.getenv("PASSKEY")
    if not env_passkey:
        raise RuntimeError("PASSKEY is not set. Add PASSKEY to your .env and restart.")
    salt = secrets.token_bytes(16)
    h = _hash_passkey(env_passkey, salt)
    store.set_config("passkey_salt", _b64e(salt))
    store.set_config("passkey_hash", _b64e(h))
    salt_b64 = _b64e(salt)
    hash_b64 = _b64e(h)

    app = Flask(__name__)
    app.secret_key = os.getenv("WEB_SECRET") or hash_b64

    max_upload = os.getenv("WEB_MAX_UPLOAD_BYTES")
    if max_upload:
        app.config["MAX_CONTENT_LENGTH"] = int(max_upload)

    upload_progress = {}
    download_progress = {}
    store_lock = threading.Lock()
    download_lock = threading.Lock()

    def is_authed():
        return session.get("authed") is True

    @app.before_request
    def _guard():
        path = request.path
        if path.startswith("/share/"):
            return None
        if path.startswith("/login") or path.startswith("/logout"):
            return None
        if path.startswith("/static/"):
            return None
        if path.startswith("/api/"):
            if not is_authed():
                return jsonify(ok=False, error="Unauthorized"), 401
            return None
        if not is_authed():
            return redirect("/login")
        return None

    @app.get("/login")
    def login_form():
        return _login_page()

    @app.post("/login")
    def login_submit():
        passkey = (request.form.get("passkey") or "").strip()
        salt = _b64d(salt_b64)
        expected = _b64d(hash_b64)
        if passkey and _hash_passkey(passkey, salt) == expected:
            session.clear()
            session["authed"] = True
            return redirect("/")
        return _login_page("Invalid passkey.")

    @app.get("/logout")
    def logout():
        session.clear()
        return redirect("/login")

    @app.get("/")
    def index():
        return HTML_PAGE

    @app.get("/api/files")
    def list_files():
        limit = int(request.args.get("limit", "50"))
        sort = request.args.get("sort", "date")
        direction = request.args.get("dir", "desc")
        query = request.args.get("q")
        if sort not in ("date", "size", "name"):
            sort = "date"
        if direction not in ("asc", "desc"):
            direction = "desc"
        if query:
            query = _escape_like(query.strip())
        with store_lock:
            rows = store.list_files(limit, sort, direction, query=query)
        files = [
            {
                "id": row[0],
                "name": row[1],
                "size_bytes": row[2],
                "size_human": _format_bytes(row[2]),
                "uploaded_at": _format_time(row[3]),
                "share_token": row[4],
            }
            for row in rows
        ]
        return jsonify(ok=True, files=files)

    @app.post("/api/share/<int:file_id>")
    def create_share(file_id):
        with store_lock:
            row = store.get_file(file_id)
        if not row:
            return jsonify(ok=False, error="File not found"), 404
        token = secrets.token_urlsafe(32)
        with store_lock:
            store.revoke_share_token(file_id)
            store.create_share_token(file_id, token, int(time.time()))
        link = request.host_url.rstrip("/") + "/share/" + token
        return jsonify(ok=True, link=link, token=token)

    @app.post("/api/share/<int:file_id>/revoke")
    def revoke_share(file_id):
        with store_lock:
            row = store.get_file(file_id)
        if not row:
            return jsonify(ok=False, error="File not found"), 404
        with store_lock:
            store.revoke_share_token(file_id)
        return jsonify(ok=True)

    @app.get("/share/<token>")
    def download_shared(token):
        row = store.get_file_by_token(token)
        if not row:
            return "Invalid or expired link", 404
        payload = client.download_file(row["id"], row["msg_ids"])
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
