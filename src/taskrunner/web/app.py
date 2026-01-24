"""
Flask Application per PTOF Task Runner Web UI.
"""

import sys
from pathlib import Path
from flask import Flask, render_template, send_from_directory

# Aggiungi path progetto
PROJECT_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(PROJECT_ROOT))


def create_app():
    """Application factory Flask."""
    app = Flask(
        __name__,
        template_folder=str(Path(__file__).parent / "templates"),
        static_folder=str(Path(__file__).parent / "static")
    )

    app.config['SECRET_KEY'] = 'ptof-taskrunner-secret'

    # Registra blueprints
    from .routes.api import api_bp
    from .routes.sse import sse_bp

    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(sse_bp, url_prefix='/sse')

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/health')
    def health():
        return {'status': 'ok'}

    return app


def main():
    """Entry point per il server web."""
    import argparse
    parser = argparse.ArgumentParser(description="PTOF Task Runner Web UI")
    parser.add_argument('--host', default='0.0.0.0', help='Host (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=5000, help='Porta (default: 5000)')
    parser.add_argument('--debug', action='store_true', help='Modalità debug')
    args = parser.parse_args()

    app = create_app()
    print(f"Task Runner Web UI avviato su http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug, threaded=True)


if __name__ == "__main__":
    main()
