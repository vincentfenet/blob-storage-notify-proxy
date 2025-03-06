#!/usr/bin/python

"""Proxy server for notifications."""

import importlib
import os
import re
import select
import socket
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

import requests


def eprint(*args, **kwargs):
    """Print to stderr."""
    print(*args, file=sys.stderr, **kwargs)


CONFIG_PROXY_PORT = int(os.getenv("PROXY_PORT"))
CONFIG_TARGET_SERVER = urlparse(os.getenv("TARGET_SERVER"))
CONFIG_NOTIFICATION_ENDPOINT = os.getenv("NOTIFICATION_ENDPOINT")
CONFIG_TRANSFORMER_MODULE = sys.argv[1] if len(sys.argv) > 1 else None


class Notify:
    """Send notifications to a specified endpoint."""

    def __init__(self, endpoint):
        self.endpoint = endpoint
        self.executor = ThreadPoolExecutor()

    def send_notification(self, message):
        """Schedule a notification sent to the endpoint."""
        future = self.executor.submit(self._send_notification, message)
        return future

    def _send_notification(self, message):
        """Send a notification to the endpoint."""
        try:
            requests.post(self.endpoint, json=message, timeout=1)
        except Exception:  # pragma pylint: disable=broad-exception-caught
            traceback.print_exc()


class Proxy:
    """Proxy server that receives messages and sends them to a target server."""

    input_list = []
    channel = {}
    recv_map = {}

    def __init__(self, host, port):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((host, port))
        self.server.listen(200)
        self.s = None
        self.data = None
        self.notification = Notify(CONFIG_NOTIFICATION_ENDPOINT)

    def main_loop(self):
        """Main loop of the proxy server."""
        self.input_list.append(self.server)
        if CONFIG_TRANSFORMER_MODULE:
            eprint("Loading transform module:", CONFIG_TRANSFORMER_MODULE)
            transform_module = importlib.import_module(CONFIG_TRANSFORMER_MODULE)
            transform = getattr(transform_module, "transform")

        while 1:
            time.sleep(0.001)
            inputready, _, _ = select.select(self.input_list, [], [])
            for self.s in inputready:
                if self.s == self.server:
                    clientsock, clientaddr = self.server.accept()
                    host = CONFIG_TARGET_SERVER.netloc.split(":")[0]
                    port = int(CONFIG_TARGET_SERVER.netloc.split(":")[1])
                    forward = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

                    try:
                        forward.connect((host, port))
                        eprint("Forward", [host, port], "connected")
                    except (
                        Exception  # pragma pylint: disable=broad-exception-caught
                    ) as e:
                        eprint(e)
                        continue

                    if forward:
                        eprint("Client", clientaddr, "connected")
                        self.input_list.append(clientsock)
                        self.input_list.append(forward)
                        self.channel[clientsock] = forward
                        self.channel[forward] = clientsock
                    else:
                        eprint("Can't establish connection with remote server")
                        eprint("Closing connection with client", clientaddr)
                        clientsock.close()
                    break
                try:
                    self.data = self.s.recv(4096)
                    self.data = re.sub(
                        rb"(?i)keep-alive: timeout=\d+\r\n", b"", self.data
                    )
                    if (
                        b"HTTP/1.1" == self.data[:8]
                        and self.channel[self.s] in self.channel
                    ):
                        queries = Proxy.parse_http_requests(
                            self.data, self.recv_map[self.channel[self.s]]
                        )
                        for i in queries:
                            eprint(
                                # pragma: pylint: disable=consider-using-f-string
                                "{method} {path}: {status_code} {reason_phrase}".format(
                                    method=i["request"]["method"],
                                    path=i["request"]["path"],
                                    status_code=i["response"]["status_code"],
                                    reason_phrase=i["response"]["reason_phrase"],
                                )
                            )
                        if CONFIG_TRANSFORMER_MODULE:
                            queries = transform(queries)
                        if queries:
                            self.notification.send_notification(queries)
                        self.recv_map[self.s] = b""
                        self.recv_map[self.channel[self.s]] = b""
                    if self.s not in self.recv_map:
                        self.recv_map[self.s] = b""
                    self.recv_map[self.s] += self.data
                    if len(self.data) == 0:
                        self.on_close()
                        break
                    self.channel[self.s].send(self.data)
                except Exception as e:  # pragma pylint: disable=broad-exception-caught
                    eprint(traceback.format_exc())
                    eprint("exception", e)
                    self.on_close()
                    if self.s in self.recv_map:
                        del self.recv_map[self.s]
                    break

    @staticmethod
    def parse_http_requests(response, request):
        """Parse an HTTP request and return a list of queries."""
        reqs = []
        while request:
            headers_and_body = request.split(b"\r\n\r\n", 1)
            if len(headers_and_body) == 2:
                raw_headers, body = headers_and_body
            else:
                raw_headers = headers_and_body[0]
                body = ""

            status_line, *raw_headers_list = raw_headers.split(b"\r\n")
            method, path, _ = status_line.decode("ascii").split(" ", 2)
            headers = {}
            for header in raw_headers_list:
                key, value = header.decode("ascii").split(": ", 1)
                headers[key.lower()] = value

            reqs.append(
                {
                    "method": method,
                    "path": path,
                    "headers": headers,
                    "body": body.decode("ascii"),
                }
            )

            if len(headers_and_body) == 2:
                content_length = headers.get("content-length")
                if content_length:
                    try:
                        content_length = int(content_length)
                        request = request[len(raw_headers) + 4 + content_length :]
                    except ValueError:
                        break
                else:
                    break
            else:
                break

        responses = []
        while response:
            headers_and_body = response.split(b"\r\n\r\n", 1)
            if len(headers_and_body) == 2:
                raw_headers, body = headers_and_body
            else:
                raw_headers = headers_and_body[0]
                body = ""

            status_line, *raw_headers_list = raw_headers.split(b"\r\n")
            version, status_code, reason_phrase = status_line.decode("ascii").split(
                " ", 2
            )
            headers = {}
            for header in raw_headers_list:
                key, value = header.decode("ascii").split(": ", 1)
                headers[key.lower()] = value

            responses.append(
                {
                    "version": version,
                    "status_code": int(status_code),
                    "reason_phrase": reason_phrase,
                    "headers": headers,
                    "body": body.decode("ascii"),
                }
            )

            if len(headers_and_body) == 2:
                content_length = headers.get("content-length")
                if content_length:
                    try:
                        content_length = int(content_length)
                        response = response[len(raw_headers) + 4 + content_length :]
                    except ValueError:
                        break
                else:
                    break
            else:
                break
        if len(reqs) != len(responses):
            raise ValueError("Number of requests does not match number of responses")
        res = []
        for request, response in zip(reqs, responses):
            res.append({"request": request, "response": response})
        return res

    def on_close(self):
        """Close the connection."""
        try:
            eprint("Client", self.s.getpeername(), "disconnected")
        except Exception as e:  # pragma pylint: disable=broad-exception-caught
            eprint(e)
            eprint("Client closed")

        self.input_list.remove(self.s)
        self.input_list.remove(self.channel[self.s])
        out = self.channel[self.s]
        self.channel[out].close()
        self.channel[self.s].close()
        del self.channel[out]
        del self.channel[self.s]


if __name__ == "__main__":
    proxy = Proxy("0.0.0.0", CONFIG_PROXY_PORT)
    eprint(
        f"Listening on port: {CONFIG_PROXY_PORT}, forwarding to: {CONFIG_TARGET_SERVER.netloc}"
    )
    proxy.main_loop()
