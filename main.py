import os
import shutil
from typing import Optional

from src.audio_splitter import chunk_audio
from src.audio_transcriber import transcribe_chunked_audio
from src.audio_translator import translate_chunked_audio
from src.meeting_audio_processor import record_system_audio
from src.meeting_summarizer import summarize_transcript
from src.rag_pipeline import rag_engine


def prompt_yes_no(question: str, default: str = "y") -> bool:
    choice = input(
        f"{question} [{'Y/n' if default == 'y' else 'y/N'}]: ").strip().lower()
    if not choice:
        choice = default
    return choice in {"y", "yes"}


def prompt_int(question: str, default: int) -> int:
    raw = input(f"{question} [{default}]: ").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        print("Invalid number, using default.")
        return default
    return value


def get_audio_path() -> Optional[str]:
    if prompt_yes_no("Record system audio now?", default="y"):
        raw = input(
            "Press Enter to Proceed: "
        ).strip()
        duration = None
        if raw:
            try:
                duration = int(raw)
            except ValueError:
                print("Invalid number, switching to manual stop.")
                duration = None
        return record_system_audio(duration=duration)

    path = input("Enter path to an existing audio file: ").strip().strip('"')
    if not path:
        return None
    return path


def select_transcript_mode() -> str:
    choice = input(
        "Choose mode: (t)ranscribe or (e)nglish-translate [t]: ").strip().lower()
    if not choice:
        return "transcribe"
    if choice in {"e", "translate", "translation"}:
        return "translate"
    return "transcribe"


def run_rag_qa(transcript: str) -> None:
    print("\nRAG Q&A. Enter a question or press Enter to exit.")
    chain = rag_engine(transcript)

    while True:
        question = input("Q: ").strip()
        if not question:
            break
        result = chain.invoke({"input": question})
        if isinstance(result, str):
            answer = result
        else:
            answer = (
                result.get("answer")
                or result.get("result")
                or result.get("output")
                or str(result)
            )
        print(f"A: {answer}\n")


def main() -> None:
    try:
        audio_path = get_audio_path()
        if not audio_path:
            print("No audio file provided. Exiting.")
            return

        if not os.path.exists(audio_path):
            print(f"Audio file not found: {audio_path}")
            return

        chunk_minutes = prompt_int("Chunk size in minutes", 10)
        chunk_paths = chunk_audio(audio_path, chunk_minutes=chunk_minutes)

        if not chunk_paths:
            print("No chunks created. Exiting.")
            return

        mode = select_transcript_mode()
        if mode == "translate":
            transcript = translate_chunked_audio(chunk_paths)
        else:
            transcript = transcribe_chunked_audio(chunk_paths)

        if not transcript or not transcript.strip():
            print("No transcript produced. Exiting.")
            return

        if prompt_yes_no("Run summarization?", default="y"):
            result = summarize_transcript(transcript)
            print("\nSummary:\n")
            print(result.get("summary", ""))
            print("\nAction Items:\n")
            print(result.get("action_items", ""))
            print("\nKey Decisions:\n")
            print(result.get("key_decisions", ""))
            print("\nOpen Questions:\n")
            print(result.get("open_questions", ""))

        if prompt_yes_no("Run RAG Q&A?", default="n"):
            run_rag_qa(transcript)
    finally:
        recordings_dir = "recordings"
        if os.path.isdir(recordings_dir):
            shutil.rmtree(recordings_dir)
            print(f"Deleted recordings folder: {recordings_dir}")


if __name__ == "__main__":
    main()
