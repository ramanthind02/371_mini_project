from socket import *
import os

def get_content_type(file_path):
    # Determine content type based on file extension
    _, ext = os.path.splitext(file_path)
    if ext == '.html':
        return 'text/html'
    elif ext == '.txt':
        return 'text/plain'
    else:
        return 'application/octet-stream'

def run_server():
    serverPort = 12000
    serverSocket = socket(AF_INET, SOCK_STREAM)
    serverSocket.bind(('', serverPort))
    serverSocket.listen(1)
    print('The server is ready to receive')

    while True:
        connectionSocket, addr = serverSocket.accept()
        
        try:
            request = connectionSocket.recv(1024).decode()
            request_lines = request.split('\n')
            request_line = request_lines[0].strip().split()
            
            if len(request_line) < 2:
                raise ValueError("Bad request")
            
            method, path = request_line[0], request_line[1]
            
            if method != 'GET':
                response = "HTTP/1.1 501 Not Implemented\r\n\r\nOnly GET method is supported"
            else:
                file_path = '.' + path  # Assuming the server runs in the same directory as the files
                if not os.path.exists(file_path):
                    response = "HTTP/1.1 404 Not Found\r\n\r\nFile not found"
                else:
                    with open(file_path, 'rb') as file:
                        content = file.read()
                    content_type = get_content_type(file_path)
                    response = f"HTTP/1.1 200 OK\r\nContent-Type: {content_type}\r\n\r\n".encode() + content

            connectionSocket.send(response if isinstance(response, bytes) else response.encode())
        except ValueError:
            response = "HTTP/1.1 400 Bad Request\r\n\r\nBad request"
            connectionSocket.send(response.encode())
        except Exception as e:
            print(f"Error: {e}")
            response = "HTTP/1.1 500 Internal Server Error\r\n\r\nAn error occurred"
            connectionSocket.send(response.encode())
        finally:
            connectionSocket.close()

if __name__ == "__main__":
    run_server()