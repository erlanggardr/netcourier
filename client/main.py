import argparse
import sys
import logging
from client.app import NetCourierApp
from common.constants import DEFAULT_GATEWAY_HOST, DEFAULT_GATEWAY_CLIENT_PORT

def main():
    parser = argparse.ArgumentParser(description="NetCourier Tkinter Client")
    parser.add_argument("--gateway-host", default=DEFAULT_GATEWAY_HOST, help="Gateway host address")
    parser.add_argument("--gateway-port", type=int, default=DEFAULT_GATEWAY_CLIENT_PORT, help="Gateway client port")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    logging_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=logging_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    
    app = NetCourierApp(args.gateway_host, args.gateway_port)
    try:
        app.run()
    except KeyboardInterrupt:
        logging.info("Client shutting down...")
    except Exception as e:
        logging.exception(f"Unexpected error: {e}")
    finally:
        app.cleanup()

if __name__ == "__main__":
    main()
