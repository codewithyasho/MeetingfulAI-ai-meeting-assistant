import os
import warnings

from pydub import AudioSegment
import soundfile as sf
import soundcard as sc

warnings.filterwarnings("ignore")

DEFAULT_SAMPLERATE = 16000
DEFAULT_CHANNELS = 1
DEFAULT_DURATION = 20
DEFAULT_BITRATE = "64k"


def record_system_audio(
    output_dir: str = "recordings",
    duration: int = DEFAULT_DURATION,
    samplerate: int = DEFAULT_SAMPLERATE,
    channels: int = DEFAULT_CHANNELS,
    bitrate: str = DEFAULT_BITRATE,
) -> str:
    os.makedirs(output_dir, exist_ok=True)

    temp_wav = os.path.join(output_dir, "temp_audio.wav")
    final_mp3 = os.path.join(output_dir, "converted_audio.mp3")

    speaker = sc.default_speaker()
    print(f"\nUsing Speaker: {speaker.name}")
    print("\nRecording system audio...")

    try:
        with sc.get_microphone(
            id=str(speaker.name),
            include_loopback=True,
        ).recorder(
            samplerate=samplerate,
            channels=channels,
        ) as mic:
            data = mic.record(numframes=samplerate * duration)
            sf.write(temp_wav, data, samplerate)

        print("\nWAV recording saved!")
    except Exception as exc:
        raise RuntimeError("Recording failed") from exc

    try:
        print("\nConverting to MP3...")
        audio = AudioSegment.from_wav(temp_wav)
        audio.export(final_mp3, format="mp3", bitrate=bitrate)
        print("\nMP3 saved successfully!")
    except Exception as exc:
        raise RuntimeError("MP3 conversion failed") from exc
    finally:
        try:
            os.remove(temp_wav)
            print("\nTemporary WAV deleted!")
        except Exception:
            print("\nCould not delete temp WAV")

    file_size = os.path.getsize(final_mp3) / (1024 * 1024)
    print("\n========== RECORDING COMPLETE ==========")
    print(f"Saved File : {final_mp3}")
    print(f"File Size  : {file_size:.2f} MB")
    print("========================================")

    return final_mp3


if __name__ == "__main__":
    record_system_audio()
