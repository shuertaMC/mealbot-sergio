import os
import sys

from flask import Flask

from mealbot.auth import require_auth
from mealbot.config import get_port
from mealbot.cors import setup_cors
from mealbot.log import setup_logging
from mealbot.members import members_handler
from mealbot.org import (
    create_organization_handler,
    cross_match_trait_handler,
    get_organizations_handler,
)


def create_app():
    """Flask app factory.

    Migrated from Go's main() in server.go. Creates and configures a Flask
    application with route registration, CORS middleware, and static file serving.
    """
    setup_logging()

    app = Flask(
        __name__,
        static_folder=os.path.join(os.path.dirname(__file__), "..", "static"),
        static_url_path="",
    )

    # Apply CORS middleware globally (mirrors Go's GetCorsHandler in middleware chain)
    setup_cors(app)

    # Register organization endpoints (Milestone 1)
    # Go's serveMux.Handle registers for all methods; handlers check method themselves.
    # We register for all common methods so handlers can return 405 for wrong methods.
    all_methods = ["GET", "POST", "DELETE", "PUT", "PATCH", "OPTIONS"]

    app.add_url_rule(
        "/orgs",
        endpoint="get_orgs",
        view_func=require_auth(get_organizations_handler),
        methods=all_methods,
    )
    app.add_url_rule(
        "/org",
        endpoint="create_org",
        view_func=require_auth(create_organization_handler),
        methods=all_methods,
    )
    app.add_url_rule(
        "/crossmatchtrait",
        endpoint="crossmatchtrait",
        view_func=require_auth(cross_match_trait_handler),
        methods=all_methods,
    )

    # Register members endpoint (Milestone 2)
    app.add_url_rule(
        "/members",
        endpoint="members",
        view_func=require_auth(members_handler),
        methods=all_methods,
    )

    return app


def main():
    """Main entry point for running the application.

    Mirrors Go's main() CLI dispatch: handles 'pair' and 'migrate' arguments,
    otherwise starts the HTTP server.
    """
    args = sys.argv
    if len(args) == 2:
        if args[1] == "pair":
            print("pair command not yet implemented")
            return
        elif args[1] == "migrate":
            print("migrate command not yet implemented")
            return
        else:
            print(f"argument '{args[1]}' not recognized")
            return

    app = create_app()
    port = get_port()
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
