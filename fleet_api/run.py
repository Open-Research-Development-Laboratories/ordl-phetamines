from __future__ import annotations

from fleet_api import create_app


app = create_app()


if __name__ == "__main__":
    bind = app.config["FLEET_API_BIND"]
    port = app.config["FLEET_API_PORT"]
    app.run(host=bind, port=port, debug=False)

