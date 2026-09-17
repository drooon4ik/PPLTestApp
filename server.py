#!/usr/bin/env python3
"""
Простой сервер для PPLTestApp.

- Отдаёт статические файлы (index.html, *.json и т.д.) из папки проекта.
- Хранит прогресс в файле progress.json на диске (один общий профиль):
    GET  /api/progress -> вернуть содержимое progress.json (или {} если нет)
    POST /api/progress -> сохранить присланный JSON в progress.json

Запуск:
    python3 server.py            # порт 8000 по умолчанию
    python3 server.py 8080       # другой порт
"""

import json
import os
import sys
import tempfile
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROGRESS_FILE = os.path.join(BASE_DIR, "progress.json")
API_PATH = "/api/progress"
MAX_BODY_BYTES = 50 * 1024 * 1024  # 50 MB — с запасом


def read_progress():
    """Прочитать прогресс с диска. Возвращает dict (пустой, если файла нет/битый)."""
    if not os.path.exists(PROGRESS_FILE):
        return {}
    try:
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def write_progress(data):
    """Атомарно записать прогресс на диск (через временный файл + rename)."""
    fd, tmp_path = tempfile.mkstemp(dir=BASE_DIR, prefix=".progress.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        os.replace(tmp_path, PROGRESS_FILE)
    except BaseException:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def _send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.split("?", 1)[0] == API_PATH:
            self._send_json(200, read_progress())
            return
        super().do_GET()

    def do_POST(self):
        if self.path.split("?", 1)[0] != API_PATH:
            self._send_json(404, {"error": "not found"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_json(400, {"error": "bad content-length"})
            return

        if length <= 0 or length > MAX_BODY_BYTES:
            self._send_json(400, {"error": "invalid body size"})
            return

        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            self._send_json(400, {"error": "invalid json"})
            return

        if not isinstance(data, dict):
            self._send_json(400, {"error": "expected a json object"})
            return

        try:
            write_progress(data)
        except OSError as exc:
            self._send_json(500, {"error": f"cannot save: {exc}"})
            return

        self._send_json(200, {"ok": True, "count": len(data)})

    # Чуть тише в логах для статики, но оставим по умолчанию поведение.
    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


def main():
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Некорректный порт: {sys.argv[1]}", file=sys.stderr)
            sys.exit(1)

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"PPLTestApp запущен: http://localhost:{port}")
    print(f"Прогресс хранится в: {PROGRESS_FILE}")
    print("Остановить: Ctrl+C")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nОстановлено.")
        server.shutdown()


if __name__ == "__main__":
    main()
