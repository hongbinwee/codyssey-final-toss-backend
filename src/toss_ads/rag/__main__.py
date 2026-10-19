"""CLI entry point for the Product RAG HTTP service."""

from __future__ import annotations

import argparse

def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m toss_ads.rag")
    commands = parser.add_subparsers(dest="command", required=True)
    serve = commands.add_parser("serve", help="serve POST /v1/rag/search")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()
    import uvicorn
    uvicorn.run("toss_ads.rag.api:app", host=args.host, port=args.port)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
