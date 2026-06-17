from netcourier.web.api.http_server import HttpServer
from netcourier.web.api.routes import APIHandler

if __name__ == "__main__":
    api_handler = APIHandler()
    server = HttpServer(port=8080, api_handler=api_handler.handle_request)
    server.start()
