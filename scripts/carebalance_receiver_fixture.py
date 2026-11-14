"""Test-only loopback LabClear connector process with isolated encrypted state.

Run only from the disposable PostgreSQL cross-application test. No repository
.env, application account, OCR route or AI route is loaded by this fixture.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import socket
import sys
import tempfile
import threading


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labclear-root", required=True)
    parser.add_argument("--state-root", required=True)
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()
    if os.environ.get("HIS_CAREBALANCE_TEST_RECEIVER") != "isolated-synthetic-only":
        raise SystemExit("The explicit isolated synthetic test guard is required")
    if not 1024 <= args.port <= 65535:
        raise SystemExit("A nonprivileged loopback port is required")
    root = Path(args.labclear_root).resolve()
    state = Path(args.state_root).resolve()
    if (not (root / "routers/carebalance_bridge.py").is_file()
            or not state.is_relative_to(Path(tempfile.gettempdir()).resolve())
            or not state.is_dir() or any(state.iterdir())):
        raise SystemExit("An existing source tree and empty owned temporary directory are required")
    key = os.environ.get("HIS_CAREBALANCE_TEST_CONNECTOR_KEY", "")
    if len(key.encode("utf-8")) < 32:
        raise SystemExit("A test-only connector key is required")
    keep = {"systemroot", "windir", "path", "pathext", "temp", "tmp", "userprofile",
            "localappdata", "appdata", "comspec", "home"}
    for name in list(os.environ):
        if name.lower() not in keep:
            del os.environ[name]
    os.chdir(state)  # config import cannot discover the owner's repository .env
    sys.path.insert(0, str(root))
    from cryptography.fernet import Fernet
    os.environ.update(APP_ENV="test", DATABASE_URL="", PROVIDER_NETWORK_ENABLED="false",
                      BUSINESS_EXTERNAL_ENABLED="false", DEMO_ACCOUNTS="false",
                      BUSINESS_DB_PATH=str(state / "receiver.sqlite3"),
                      BUSINESS_DATA_KEY=Fernet.generate_key().decode(),
                      CAREBALANCE_CONNECTOR_ENABLED="true", CAREBALANCE_CONNECTOR_KEY=key)

    original_connect, original_pair, original_lookup = socket.socket.connect, socket.socketpair, socket.getaddrinfo
    internal = threading.local()
    def denied(*_args, **_kwargs):
        raise RuntimeError("Test receiver outbound network is disabled")
    def pair(*values, **options):
        internal.socketpair = True
        try:
            return original_pair(*values, **options)
        finally:
            internal.socketpair = False
    def connect(sock, address):
        return original_connect(sock, address) if getattr(internal, "socketpair", False) else denied()
    def lookup(host, *values, **options):
        return original_lookup(host, *values, **options) if host in {"127.0.0.1", "::1"} else denied()
    socket.socketpair = pair
    socket.socket.connect = connect
    socket.socket.connect_ex = denied
    socket.create_connection = denied
    socket.getaddrinfo = lookup

    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse
    from routers.carebalance_bridge import router
    from services.conversation_transport import ConversationError
    import uvicorn

    app = FastAPI(docs_url=None, openapi_url=None, redoc_url=None)
    app.include_router(router)
    @app.exception_handler(ConversationError)
    async def business_error(request: Request, exc: ConversationError):
        headers = {"Cache-Control": "no-store"}
        if exc.retry_after:
            headers["Retry-After"] = str(exc.retry_after)
        return JSONResponse({"code": exc.code, "message": str(exc), "origin": exc.origin,
                             "request_id": None}, status_code=exc.status, headers=headers)
    @app.get("/__test/ready")
    def ready():
        return {"fixture": "isolated-carebalance-connector", "synthetic_only": True,
                "storage": "fresh-encrypted-sqlite", "outbound_network": "blocked"}
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning", access_log=False)


if __name__ == "__main__":
    main()
