from http.server import (
    BaseHTTPRequestHandler,
    ThreadingHTTPServer,
)


HOST = "0.0.0.0"
PORT = 8080


class HealthHandler(BaseHTTPRequestHandler):
    """Обработчик проверки состояния контейнера."""

    def do_GET(self):
        if self.path != "/health":
            self.send_response(404)
            self.end_headers()
            return

        response = b"Secure File Manager: OK\n"

        self.send_response(200)
        self.send_header(
            "Content-Type",
            "text/plain; charset=utf-8",
        )
        self.send_header(
            "Content-Length",
            str(len(response)),
        )
        self.end_headers()

        self.wfile.write(response)

    def log_message(self, format, *args):
        return


def main():
    server = ThreadingHTTPServer(
        (HOST, PORT),
        HealthHandler,
    )

    print(
        f"Health endpoint started "
        f"on {HOST}:{PORT}"
    )

    server.serve_forever()


if __name__ == "__main__":
    main()
