from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def setup_cors(app: FastAPI) -> None:
    """Configure CORS middleware to match Go cors.go behavior.

    The Go code reflects the request Origin header back and allows
    GET, POST, DELETE methods with Authorization, Content-Type, Origin,
    Accept, and token headers.
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "Origin", "Accept", "token"],
    )
