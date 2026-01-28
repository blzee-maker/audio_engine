import os
from pydub import AudioSegment

def save_audio_from_start(
    input_audio_path,
    duration_seconds,
    output_folder="trim_audio"
):
    # Create output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    # Load audio file
    audio = AudioSegment.from_file(input_audio_path)

    # Convert seconds to milliseconds
    duration_ms = duration_seconds * 1000

    # Trim audio from start
    trimmed_audio = audio[:duration_ms]

    # Output file name
    base_name = os.path.basename(input_audio_path)
    name, ext = os.path.splitext(base_name)
    output_path = os.path.join(
        output_folder,
        f"{name}_{duration_seconds}s{ext}"
    )

    # Export trimmed audio
    trimmed_audio.export(output_path, format=ext.replace(".", ""))

    print(f"Saved trimmed audio to: {output_path}")

# -------------------------
# Example usage
# -------------------------
if __name__ == "__main__":
    save_audio_from_start(
        input_audio_path="audio/sfx/shadowless/cloth_rustling.mp3",
        duration_seconds=3,
        output_folder="trimmed_audio"
    )
