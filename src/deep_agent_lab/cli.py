import argparse
import json
import sys
from pathlib import Path

from pydantic import BaseModel, TypeAdapter, ValidationError

from deep_agent_lab.health import doctor
from deep_agent_lab.rag.models import SearchRequest
from deep_agent_lab.rag.pipeline import RagService
from deep_agent_lab.service import (
    AgentService,
    Decision,
    ReviewRequest,
    RunRequest,
    ThreadConflict,
    ThreadId,
    open_checkpointer,
)
from deep_agent_lab.settings import Settings


def main() -> int:
    parser = argparse.ArgumentParser(prog="deep-lab", description="Run the Deep Agent Lab.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--live", action="store_true", help="Use RAG Lab and Ollama.")
    mode.add_argument("--demo", action="store_true", help="Use offline fixtures.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="Check dependencies for the selected mode.")
    sub.add_parser("init", help="Initialize the course schema and search index.")
    ingest = sub.add_parser("ingest", help="Index text, Markdown, or PDF files.")
    ingest.add_argument("path", type=Path)
    ingest.add_argument("--force", action="store_true")
    sub.add_parser("documents", help="List documents in the course corpus.")
    sub.add_parser("reindex", help="Rebuild search chunks from the canonical text.")
    search = sub.add_parser("search", help="Retrieve passages without using the chat model.")
    search.add_argument("query")
    search.add_argument("--mode", choices=["keyword", "semantic", "hybrid"], default="hybrid")
    search.add_argument("--top-k", type=int, default=5)
    ask = sub.add_parser("ask", help="Start or continue a checkpointed thread.")
    ask.add_argument("prompt")
    ask.add_argument("--thread")
    inspect = sub.add_parser("thread", help="Inspect evidence, steps and pending approvals.")
    inspect.add_argument("thread")
    review = sub.add_parser("review", help="Resolve one interrupt.")
    review.add_argument("thread")
    review.add_argument("interrupt")
    review.add_argument("decision", choices=["approve", "reject", "edit"])
    review.add_argument("--title")
    review.add_argument("--markdown-file", type=Path)
    show = sub.add_parser("brief", help="Retrieve a saved brief by ID.")
    show.add_argument("id")
    args = parser.parse_args()

    try:
        selected_mode = "demo" if args.demo else "live" if args.live else None
        overrides = {"deep_lab_mode": selected_mode} if selected_mode else {}
        settings = Settings(**overrides)
        if args.command == "doctor":
            status = doctor(settings, check_tracing=True)
            print(json.dumps(status, indent=2))
            return int(status["status"] != "ok")

        if args.command in {"init", "ingest", "documents", "reindex", "search"}:
            if settings.deep_lab_mode != "live":
                raise ValueError("Corpus commands require live configuration")
            print(json.dumps(corpus_command(args, settings), default=str, indent=2))
            return 0

        if getattr(args, "thread", None) is not None:
            TypeAdapter(ThreadId).validate_python(args.thread)
        with open_checkpointer(settings) as checkpointer:
            service = AgentService(settings, checkpointer)
            try:
                if args.command == "ask":
                    thread = {"thread_id": args.thread} if args.thread is not None else {}
                    result = service.run(RunRequest(prompt=args.prompt, **thread))
                elif args.command == "review":
                    decision = Decision(
                        type=args.decision,
                        title=args.title,
                        markdown=args.markdown_file.read_text(encoding="utf-8")
                        if args.markdown_file
                        else None,
                    )
                    result = service.resume(
                        args.thread,
                        ReviewRequest(
                            interrupt_id=args.interrupt,
                            decisions=[decision],
                        ),
                    )
                elif args.command == "thread":
                    result = service.inspect(args.thread)
                else:
                    result = service.store.get(args.id)
            finally:
                service.close()
        if result is None:
            print("Record not found.", file=sys.stderr)
            return 1
        if isinstance(result, BaseModel):
            print(result.model_dump_json(indent=2))
        return 0
    except ValidationError as error:
        problems = [
            item["msg"] for item in error.errors(include_input=False, include_context=False)
        ]
        print("Invalid settings or input. " + " ".join(problems), file=sys.stderr)
        return 1
    except (ThreadConflict, ValueError) as error:
        print(error, file=sys.stderr)
        return 1
    except Exception as error:
        print(f"Agent run failed ({type(error).__name__}). Run deep-lab doctor.", file=sys.stderr)
        return 1


def corpus_command(args, settings: Settings):
    with RagService(settings) as rag:
        match args.command:
            case "init":
                rag.initialize()
                return {"status": "initialized", "index": settings.opensearch_index}
            case "documents":
                return rag.db.documents()
            case "reindex":
                return [rag.reindex(document_id) for document_id in rag.db.document_ids()]
            case "search":
                request = SearchRequest(query=args.query, mode=args.mode, top_k=args.top_k)
                return [hit.model_dump() for hit in rag.search(request)]
            case "ingest":
                supported = {".txt", ".md", ".pdf"}
                if args.path.is_dir():
                    files = sorted(
                        file
                        for file in args.path.rglob("*")
                        if file.is_file() and file.suffix.lower() in supported
                    )
                elif args.path.is_file() and args.path.suffix.lower() in supported:
                    files = [args.path]
                else:
                    files = []
                if not files:
                    raise ValueError(
                        "Supply a Markdown, text, or PDF file or a folder containing them"
                    )
                return [rag.ingest_file(file, force=args.force) for file in files]


if __name__ == "__main__":
    raise SystemExit(main())
