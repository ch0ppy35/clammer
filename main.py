from cvdupdate.cvdupdate import CVDUpdate
import logging as l
import time
import threading
import http.server
import socketserver
import os

UPDATE_FREQUENCY = 12
WEB_PORT = 8080
CLAM_DIR = os.getenv("CLAM_DIR", "./clamav")

l.basicConfig(level=l.INFO)
json_handler = l.StreamHandler()
json_formatter = l.Formatter(
    '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": %(message)s}'
)
json_handler.setFormatter(json_formatter)
l.getLogger().handlers = [json_handler]


def update_databases() -> None:
    c = CVDUpdate(db_dir=CLAM_DIR)
    err = c.db_update()
    if err > 0:
        l.warning(
            {"error_count": err, "message": "Something went wrong while updating"}
        )


def keep_updating() -> None:
    while True:
        l.info({"message": "Performing update"})
        update_databases()
        time.sleep(60 * 60 * UPDATE_FREQUENCY)


def start_updating_thread() -> None:
    l.info({"message": "Performing initial update"})
    t = threading.Thread(target=keep_updating)
    t.start()


if __name__ == "__main__":
    try:
        start_updating_thread()
        l.info({"message": "Starting web server"})
        try:
            os.chdir(CLAM_DIR)
            with socketserver.TCPServer(
                ("0.0.0.0", WEB_PORT), http.server.SimpleHTTPRequestHandler
            ) as httpd:
                l.info({"message": f"Now serving at port TCP {WEB_PORT}", "web": f"http://0.0.0.0:{WEB_PORT}/" })
                httpd.serve_forever()
        except Exception as e:
            l.error({"message": f"Failed bringing up the web server - {e}"})
    except KeyboardInterrupt:
        l.info({"message": "Program interrupted. Exiting gracefully."})
