from pydub import AudioSegment
from dsp.loudness import measure_integrated_lufs, apply_lufs_target

audio = AudioSegment.from_file("audio/voice/Scene - 1.wav")

before = measure_integrated_lufs(audio)
print(f"Before: {before:.2f} LUFS")

corrected = apply_lufs_target(audio, target_lufs=-18.0)

after = measure_integrated_lufs(corrected)
print(f"After: {after:.2f} LUFS")

corrected.export("output/scene1_lufs_corrected.wav", format="wav")