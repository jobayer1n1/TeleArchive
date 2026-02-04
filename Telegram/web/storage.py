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
        self.conn.commit()

    def list_files(self, limit, sort_key, sort_dir):
        if sort_key == "size":
            order_by = "size_bytes"
        elif sort_key == "name":
            order_by = "file_name COLLATE NOCASE"
        else:
            order_by = "uploaded_at"

        direction = "ASC" if sort_dir == "asc" else "DESC"
        sql = f"SELECT id, file_name, size_bytes, uploaded_at FROM web_files ORDER BY {order_by} {direction} LIMIT ?"
        rows = self.cursor.execute(sql, (limit,)).fetchall()
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
