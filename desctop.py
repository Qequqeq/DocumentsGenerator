import webview
import threading
import uvicorn
import socket
import time
import sys
import os
import logging
import urllib.request
import tempfile
from pathlib import Path

os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"
os.environ["QT_LOGGING_RULES"] = "qt.webenginecontext.info=false"

from src.logger import logger, log_error, log_info, log_warning

PORT = 8000
HOST = "127.0.0.1"


class Api:
    def download_file(self, url: str, filename: str):
        try:
            log_info("DOWNLOAD", f"Запрос на скачивание: {filename}", {"url": url})

            if url.startswith("blob:"):
                return {"success": False, "error": "blob URL не поддерживается напрямую, используется fetch-обход"}

            full_url = url if url.startswith("http") else f"http://{HOST}:{PORT}{url}"

            import ssl
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            req = urllib.request.Request(full_url)
            with urllib.request.urlopen(req, context=ctx) as response:
                content = response.read()

            downloads_dir = Path.home() / "Загрузки"
            downloads_dir.mkdir(parents=True, exist_ok=True)
            target_path = downloads_dir / filename

            counter = 1
            stem = target_path.stem
            suffix = target_path.suffix
            while target_path.exists():
                target_path = downloads_dir / f"{stem}_{counter}{suffix}"
                counter += 1

            with open(target_path, "wb") as f:
                f.write(content)

            log_info("DOWNLOAD", f"Файл сохранён: {target_path}")
            return {"success": True, "path": str(target_path), "filename": target_path.name}
        except Exception as e:
            log_error("DOWNLOAD", e, {"url": url, "filename": filename})
            return {"success": False, "error": str(e)}

    def save_blob(self, data_base64: str, filename: str):
        try:
            import base64
            log_info("DOWNLOAD", f"Сохранение blob данных как: {filename}")

            content = base64.b64decode(data_base64)

            downloads_dir = Path.home() / "Загрузки"
            downloads_dir.mkdir(parents=True, exist_ok=True)
            target_path = downloads_dir / filename

            counter = 1
            stem = target_path.stem
            suffix = target_path.suffix
            while target_path.exists():
                target_path = downloads_dir / f"{stem}_{counter}{suffix}"
                counter += 1

            with open(target_path, "wb") as f:
                f.write(content)

            log_info("DOWNLOAD", f"Blob файл сохранён: {target_path}")
            return {"success": True, "path": str(target_path), "filename": target_path.name}
        except Exception as e:
            log_error("DOWNLOAD", e, {"filename": filename})
            return {"success": False, "error": str(e)}

    def open_external(self, url: str):
        import webbrowser
        try:
            log_info("BROWSER", f"Открытие во внешнем браузере: {url}")
            full_url = url if url.startswith("http") else f"http://{HOST}:{PORT}{url}"
            webbrowser.open(full_url)
            return {"success": True}
        except Exception as e:
            log_error("BROWSER", e, {"url": url})
            return {"success": False, "error": str(e)}


def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((HOST, port)) == 0


def start_server():
    log_info("DESKTOP", f"Запуск встроенного сервера на {HOST}:{PORT}")
    from api_entry import app
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")


def wait_for_server(timeout=10):
    start_time = time.time()
    while time.time() - start_time < timeout:
        if is_port_in_use(PORT):
            log_info("DESKTOP", f"Сервер успешно запущен и отвечает на порту {PORT}")
            return True
        time.sleep(0.1)
    return False


def main():
    log_info("DESKTOP", "Запуск десктоп-приложения")

    if is_port_in_use(PORT):
        log_error("DESKTOP", Exception(f"Порт {PORT} уже занят"), {
            "hint": "Возможно, приложение уже запущено в другом окне"
        })
        sys.exit(1)

    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    if not wait_for_server():
        log_error("DESKTOP", Exception("Таймаут ожидания сервера"), {
            "timeout": 10,
            "host": HOST,
            "port": PORT
        })
        sys.exit(1)

    log_info("DESKTOP", "Создание окна приложения", {
        "title": "Оценка профессиональных рисков",
        "width": 1200,
        "height": 800
    })

    api = Api()
    window = webview.create_window(
        'Оценка профессиональных рисков',
        f'http://{HOST}:{PORT}',
        width=1200,
        height=800,
        min_size=(800, 600),
        text_select=True,
        js_api=api
    )

    log_info("DESKTOP", "Окно приложения открыто")
    webview.start(debug=False)

    log_info("DESKTOP", "Окно приложения закрыто пользователем, завершение работы")

    logging.shutdown()
    os._exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log_error("DESKTOP", e, {"context": "Необработанное исключение в main()"})
        logging.shutdown()
        sys.exit(1)