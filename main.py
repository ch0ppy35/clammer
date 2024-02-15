from cvdupdate.cvdupdate import CVDUpdate
import logging as l
import time
import threading
import http.server
import socketserver as s
import os

UPDATE_FREQUENCY_HOURS = 12
WEB_PORT = 8080
HEALTHZ_PORT = 8081
CLAM_DIR = os.getenv("CLAM_DIR", "./clamav")

first_update_completed = False
update_lock = threading.Lock()


class HTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        l.info({"message": format % args})

    def do_GET(self):
        if self.path == "/healthz":
            if first_update_completed:
                self.send_response(200)
                self.send_header("Content-type", "text/plain")
                self.end_headers()
                self.wfile.write(bytes("OK", "utf-8"))
            else:
                self.send_response(503)
            self.end_headers()
        else:
            super().do_GET()


class ThreadedHTTPServer(s.ThreadingMixIn, s.TCPServer):
    pass


def init_logger() -> None:
    l.basicConfig(level=l.INFO)
    json_handler = l.StreamHandler()
    json_formatter = l.Formatter(
        '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": %(message)s}'
    )
    json_handler.setFormatter(json_formatter)
    l.getLogger().handlers = [json_handler]


def update_databases() -> None:
    global first_update_completed
    c = CVDUpdate(db_dir=CLAM_DIR)
    err = c.db_update()
    if err > 0:
        l.warning(
            {"error_count": err, "message": "Something went wrong while updating"}
        )
    else:
        with update_lock:
            first_update_completed = True


def keep_updating() -> None:
    while True:
        l.info({"message": "Running update"})
        update_databases()
        time.sleep(60 * 60 * UPDATE_FREQUENCY_HOURS)


def start_updating_thread() -> None:
    l.info({"message": "Running initial update"})
    t = threading.Thread(target=keep_updating)
    t.start()


if __name__ == "__main__":
    init_logger()
    l.info({"message": f"CLAM_DIR is set to {CLAM_DIR}"})
    try:
        start_updating_thread()
        l.info({"message": "Starting web server"})
        try:
            os.chdir(CLAM_DIR)

            with ThreadedHTTPServer(("0.0.0.0", WEB_PORT), HTTPRequestHandler) as httpd:
                l.info(
                    {
                        "message": f"Now serving on port {WEB_PORT}",
                        "web": f"http://0.0.0.0:{WEB_PORT}/",
                    }
                )

                with ThreadedHTTPServer(
                    ("0.0.0.0", HEALTHZ_PORT), HTTPRequestHandler
                ) as probe_httpd:
                    l.info(
                        {
                            "message": f"Now serving on port {HEALTHZ_PORT}",
                            "probe": f"http://0.0.0.0:{HEALTHZ_PORT}/healthz",
                        }
                    )

                    threading.Thread(target=httpd.serve_forever).start()
                    threading.Thread(target=probe_httpd.serve_forever).start()

                    threading.Event().wait()

        except Exception as e:
            l.error({"message": f"Failed bringing up the web server - {e}"})
    except KeyboardInterrupt:
        l.info({"message": "Exiting"})
