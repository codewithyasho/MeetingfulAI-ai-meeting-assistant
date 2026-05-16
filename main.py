import argparse
from pathlib import Path

from src.audio_splitter import chunk_audio
from src.audio_transcriber import transcribe_chunked_audio
from src.audio_translator import translate_chunked_audio
from src.meeting_audio_processor import record_system_audio
from src.meeting_summarizer import summarize_transcript
from src.rag_pipeline import rag_engine

DEFAULT_OUTPUT_DIR = "recordings"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Process meeting audio: record, transcribe/translate, summarize, and query."
    )
    parser.add_argument(
        "--input",
        "-i",
        help="Path to an audio file to process (mp3, wav, etc.).",
    )
    parser.add_argument(
        "--record",
        action="store_true",
        help="Record system audio instead of using --input.",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=20,
        help="Recording duration in seconds (used with --record).",
    )
    parser.add_argument(
        "--chunk-minutes",
        type=int,
        default=10,
        help="Chunk size in minutes for transcription/translation.",
    )
    parser.add_argument(
        "--translate",
        action="store_true",
        help="Translate audio to English instead of transcribing.",
    )
    parser.add_argument(
        "--summarize",
        action="store_true",
        help="Summarize the transcript and extract actions/decisions/questions.",
    )
    parser.add_argument(
        "--rag",
        action="store_true",
        help="Start an interactive Q&A session over the transcript.",
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for recordings and chunks.",
    )
    return parser.parse_args()


def resolve_audio_path(args: argparse.Namespace) -> str:
    if args.duration <= 0:
        raise ValueError("--duration must be a positive number of seconds")
    if args.chunk_minutes <= 0:
        raise ValueError("--chunk-minutes must be a positive number")

    if args.record:
        return record_system_audio(
            output_dir=args.output_dir,
            duration=args.duration,
        )

    if not args.input:
        raise ValueError("Provide --input or use --record")

    audio_path = Path(args.input)
    if not audio_path.exists():
        raise FileNotFoundError(f"Input audio file not found: {audio_path}")

    return str(audio_path)


def run_rag_loop(transcript: str) -> None:
    rag_chain = rag_engine(transcript)
    print("\nRAG is ready. Ask a question, or type 'exit' to quit.")

    while True:
        try:
            question = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if not question or question.lower() in {"exit", "quit"}:
            break

        result = rag_chain.invoke({"input": question})
        if isinstance(result, dict):
            answer = result.get("answer", "")
        else:
            answer = str(result)

        print(answer)


def main() -> int:
    args = parse_args()

    try:
        audio_path = resolve_audio_path(args)
    except Exception as exc:
        print(f"[ERROR] {exc}")
        return 1

    try:
        chunk_paths = chunk_audio(
            audio_path,
            chunk_minutes=args.chunk_minutes,
            output_dir=args.output_dir,
        )
    except Exception as exc:
        print(f"[ERROR] Failed to chunk audio: {exc}")
        return 1

    if not chunk_paths:
        print("[ERROR] No audio chunks were created.")
        return 1

    if args.translate:
        transcript = translate_chunked_audio(chunk_paths)
    else:
        transcript = transcribe_chunked_audio(chunk_paths)

    if args.summarize:
        summary_bundle = summarize_transcript(transcript)
        print("\nSummary:\n")
        print(summary_bundle["summary"])
        print("\nAction Items:\n")
        print(summary_bundle["action_items"])
        print("\nKey Decisions:\n")
        print(summary_bundle["key_decisions"])
        print("\nOpen Questions:\n")
        print(summary_bundle["open_questions"])

    if args.rag:
        run_rag_loop(transcript)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
