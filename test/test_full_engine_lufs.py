from pydub import AudioSegment
from dsp.loudness import measure_integrated_lufs

final_audio = AudioSegment.from_file("output/final.wav")

lufs = measure_integrated_lufs(final_audio)
print(f"Final Integrated LUFS: {lufs:.2f}")
