import socket
import threading
import os
import time

cache = {}


def start_origin_server():
    host = 'localhost'
    port = 8000
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(1)
    print(f"Origin server is running on {host}:{port}")
    while True:
        client_socket, addr = server_socket.accept()
        print(f"Origin server received connection from {addr}")
        request = client_socket.recv(1024).decode()
        print(f"Origin server received request: {request}")

        file_path = 'test.html'
        try:
            with open(file_path, 'r') as file:
                response_body = file.read()
                last_modified_timestamp = os.path.getmtime(file_path)
                last_modified = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(last_modified_timestamp))

                response = (
                    "HTTP/1.1 200 OK\r\n"
                    f"Content-Length: {len(response_body)}\r\n"
                    "Content-Type: text/html\r\n"
                    f"Last-Modified: {last_modified}\r\n"
                    "\r\n"
                    f"{response_body}"
                )
        except FileNotFoundError:
            response = (
                "HTTP/1.1 404 Not Found\r\n"
                "Content-Length: 0\r\n"
                "\r\n"
            )
            print(f"Origin server: File {file_path} not found")

        client_socket.send(response.encode())
        print(f"Origin server sent response to client {addr}")
        client_socket.close()


def handle_client(client_socket):
    try:
        request = client_socket.recv(1024).decode()
        request_lines = request.split('\n')
        request_line = request_lines[0].strip().split()

        if len(request_line) < 2:
            raise ValueError("Bad request")

        method, path = request_line[0], request_line[1]
        print(f"Proxy server received {method} request for {path}")

        if method != 'GET':
            response = "HTTP/1.1 501 Not Implemented\r\n\r\nOnly GET method is supported"
            client_socket.send(response.encode())
        else:
            cached_entry = get_cached_response(path)

            if cached_entry:
                print(f"Proxy server: Serving cached response for {path}")
                last_modified = cached_entry['last_modified']
                origin_host = "localhost"
                origin_response = proxy(request, origin_host, cached_timestamp=last_modified)

                if b"304 Not Modified" in origin_response:
                    print(f"Proxy server: Cache is still valid for {path}")
                    client_socket.send(cached_entry['response'])
                else:
                    print(f"Proxy server: Cache is outdated, fetching new content for {path}")
                    last_modified = get_last_modified_header(origin_response)
                    store_in_cache(path, origin_response, last_modified)
                    client_socket.send(origin_response)
            else:
                print(f"Proxy server: No cached response for {path}, forwarding to origin server")
                origin_host = "localhost"
                origin_response = proxy(request, origin_host, cached_timestamp=None)

                if origin_response:
                    print(f"Proxy server: Received new content from origin server for {path}")
                    last_modified = get_last_modified_header(origin_response)
                    store_in_cache(path, origin_response, last_modified)
                    client_socket.send(origin_response)
                else:
                    response = "HTTP/1.1 502 Bad Gateway\r\n\r\nCould not fetch from the origin server"
                    print(f"Proxy server: Error fetching from origin server for {path}")
                    client_socket.send(response.encode())
    except ValueError:
        response = "HTTP/1.1 400 Bad Request\r\n\r\nBad request"
        print(f"Proxy server: Bad request received")
        client_socket.send(response.encode())
    except Exception as e:
        print(f"Proxy server: Error {e}")
        response = "HTTP/1.1 500 Internal Server Error\r\n\r\nAn error occurred"
        client_socket.send(response.encode())
    finally:
        client_socket.close()


def start_proxy_server():
    serverPort = 12000
    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serverSocket.bind(('', serverPort))
    serverSocket.listen(5)
    print(f"Proxy server is running on {serverPort}")
    while True:
        connectionSocket, addr = serverSocket.accept()
        print(f"Proxy server received connection from {addr}")
        client_thread = threading.Thread(target=handle_client, args=(connectionSocket,))
        client_thread.start()


def proxy(request, origin_host, cached_timestamp=None, origin_port=8000):
    try:
        origin_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        origin_socket.connect((origin_host, origin_port))
        print(f"Proxy server forwarding request to origin server at {origin_host}:{origin_port}")

        if cached_timestamp:
            request_lines = request.split('\r\n')
            modified_request = "\r\n".join(request_lines[:-1]) + f"\r\nIf-Modified-Since: {cached_timestamp}\r\n\r\n"
            origin_socket.send(modified_request.encode())
            print(f"Proxy server: Sent Conditional GET to origin server with If-Modified-Since: {cached_timestamp}")
        else:
            origin_socket.send(request.encode())
            print(f"Proxy server: Forwarded GET request to origin server")

        response = b""
        while True:
            data = origin_socket.recv(1024)
            if not data:
                break
            response += data

        origin_socket.close()
        return response
    except Exception as e:
        print(f"Proxy server: Error forwarding request: {e}")
        return None


def get_cached_response(url):
    if url in cache:
        cached_entry = cache[url]
        current_time = time.time()

        if current_time - cached_entry['timestamp'] < 60:
            print(f"Proxy server: Found valid cached response for {url}")
            return cached_entry
        else:
            print(f"Proxy server: Cache expired for {url}")
            del cache[url]

    return None


def store_in_cache(url, response, last_modified):
    cache[url] = {
        'response': response,
        'last_modified': last_modified,
        'timestamp': time.time()
    }
    print(f"Proxy server: Stored response for {url} in cache")


def get_last_modified_header(response):
    try:
        headers = response.decode().split('\r\n')
        for header in headers:
            if header.startswith("Last-Modified:"):
                return header.split("Last-Modified: ")[1]
    except Exception:
        return None


if __name__ == "__main__":
    threading.Thread(target=start_origin_server).start()
    threading.Thread(target=start_proxy_server).start()
