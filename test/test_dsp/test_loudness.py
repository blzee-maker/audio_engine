from pydub import AudioSegment
from dsp.loudness import measure_integrated_lufs

audio = AudioSegment.from_file("audio/voice/Scene - 1.wav")

lufs = measure_integrated_lufs(audio)

print(f"Intergrated LUFS: {lufs:.2f}")