import json
import sqlite3
import time


class WebStore:
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS web_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT NOT NULL,
                msg_ids TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                uploaded_at INTEGER NOT NULL
            )
            """
        )
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS share_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id INTEGER NOT NULL REFERENCES web_files(id),
                token TEXT NOT NULL UNIQUE,
                created_at INTEGER NOT NULL
            )
            """
        )
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS auth_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        self.conn.commit()

    def list_files(self, limit, sort_key, sort_dir, query=None):
        if sort_key == "size":
            order_by = "w.size_bytes"
        elif sort_key == "name":
            order_by = "w.file_name COLLATE NOCASE"
        else:
            order_by = "w.uploaded_at"

        direction = "ASC" if sort_dir == "asc" else "DESC"

        where = ""
        params = []
        if query:
            where = "WHERE w.file_name LIKE ? ESCAPE '\\'"
            params.append(f"%{query}%")

        sql = f"""
            SELECT w.id, w.file_name, w.size_bytes, w.uploaded_at, s.token
            FROM web_files w
            LEFT JOIN share_tokens s ON s.file_id = w.id
            {where}
            ORDER BY {order_by} {direction}
            LIMIT ?
        """
        params.append(limit)
        rows = self.cursor.execute(sql, tuple(params)).fetchall()
        return rows

    def add_file(self, file_name, msg_ids, size_bytes):
        self.cursor.execute(
            "INSERT INTO web_files (file_name, msg_ids, size_bytes, uploaded_at) VALUES (?, ?, ?, ?)",
            (file_name, json.dumps(msg_ids), size_bytes, int(time.time())),
        )
        self.conn.commit()

    def get_file(self, file_id):
        row = self.cursor.execute(
            "SELECT file_name, msg_ids, size_bytes, uploaded_at FROM web_files WHERE id=?",
            (file_id,),
        ).fetchone()
        if not row:
            return None
        return {
            "file_name": row[0],
            "msg_ids": json.loads(row[1]),
            "size_bytes": row[2],
            "uploaded_at": row[3],
        }

    def delete_file(self, file_id):
        row = self.cursor.execute(
            "SELECT msg_ids FROM web_files WHERE id=?",
            (file_id,),
        ).fetchone()
        if not row:
            return None
        msg_ids = json.loads(row[0])
        self.cursor.execute("DELETE FROM web_files WHERE id=?", (file_id,))
        self.conn.commit()
        return msg_ids

    def revoke_share_token(self, file_id):
        self.cursor.execute("DELETE FROM share_tokens WHERE file_id=?", (file_id,))
        self.conn.commit()

    def create_share_token(self, file_id, token, created_at):
        self.cursor.execute(
            "INSERT INTO share_tokens (file_id, token, created_at) VALUES (?, ?, ?)",
            (file_id, token, created_at),
        )
        self.conn.commit()

    def get_file_by_token(self, token):
        row = self.cursor.execute(
            """
            SELECT w.id, w.file_name, w.msg_ids, w.size_bytes, w.uploaded_at
            FROM share_tokens s
            JOIN web_files w ON w.id = s.file_id
            WHERE s.token = ?
            """,
            (token,),
        ).fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "file_name": row[1],
            "msg_ids": json.loads(row[2]),
            "size_bytes": row[3],
            "uploaded_at": row[4],
        }

    def get_config(self, key):
        row = self.cursor.execute(
            "SELECT value FROM auth_config WHERE key=?",
            (key,),
        ).fetchone()
        if not row:
            return None
        return row[0]

    def set_config(self, key, value):
        self.cursor.execute(
            "INSERT OR REPLACE INTO auth_config (key, value) VALUES (?, ?)",
            (key, value),
        )
        self.conn.commit()
