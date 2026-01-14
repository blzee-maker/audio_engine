from pydub import AudioSegment
from dsp.compression import apply_dialogue_compression

# Load raw dialogue
audio = AudioSegment.from_file("audio/voice/Scene - 1.wav")

# Compression config
cfg = {
    "enabled": True,
    "threshold": -30,
    "ratio": 8,
    "attack_ms": 5,
    "release_ms": 200,
    "makeup_gain": 6
}

# Apply compression
compressed = apply_dialogue_compression(audio, cfg)

# Export result
compressed.export("output/test_compression.wav", format="wav")

print("Original:")
print("  Avg dBFS:", audio.dBFS)
print("  Peak dBFS:", audio.max_dBFS)

print("Compressed:")
print("  Avg dBFS:", compressed.dBFS)
print("  Peak dBFS:", compressed.max_dBFS)


print("Compression test exported.")
