"""Entry point per python -m src.taskrunner.web"""

import argparse
from .app import create_app


def main():
    parser = argparse.ArgumentParser(description="PTOF Task Runner Web UI")
    parser.add_argument("--port", type=int, default=5000, help="Porta HTTP (default: 5000)")
    parser.add_argument("--host", default="0.0.0.0", help="Host (default: 0.0.0.0)")
    parser.add_argument("--debug", action="store_true", help="Modalità debug")
    args = parser.parse_args()

    app = create_app()
    print(f"Task Runner Web UI: http://localhost:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug, threaded=True)


if __name__ == "__main__":
    main()
