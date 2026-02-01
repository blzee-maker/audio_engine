# 📘 Timeline.json Specification

A complete guide to writing timelines for the Audio Engine

---

1️⃣ Overview

`timeline.json` is the single source of truth for the audio engine.

It defines:

* What audio plays
* When it plays
* How it behaves
* How scenes transition
* How intelligence (ducking, energy, loudness) is applied

The engine does not guess.
Everything is explicit, deterministic, and reproducible.

---

2️⃣ Top-Level Structure

```json
{
  "project": {},
  "settings": {},
  "tracks": [],
  "scenes": []
}
```

| Key        | Purpose                        |
| ---------- | ------------------------------ |
| `project`  | Technical output configuration |
| `settings` | Global audio behavior          |
| `tracks`   | Logical audio lanes            |
| `scenes`   | Story-based time blocks        |

---

3️⃣ `project` — Output Definition

```json
"project": {
  "name": "My Audio Drama",
  "duration": 120.0,
  "sample_rate": 48000,
  "bit_depth": 16
}
```

| Field         | Type         | Meaning             |
| ------------- | ------------ | ------------------- |
| `name`        | string       | Project label       |
| `duration`    | number (sec) | Total output length |
| `sample_rate` | number       | Audio sample rate   |
| `bit_depth`   | number       | Output bit depth    |

📌 `duration` is mandatory — all audio is clipped to this.

---

4️⃣ `settings` — Global Audio Rules

These apply unless overridden by scenes.

Example

```json
"settings": {
  "default_silence": 0.5,
  "normalize": true,
  "master_gain": 0
}
```

Common Settings

| Key               | Meaning                       |
| ----------------- | ----------------------------- |
| `default_silence` | Gap between auto-placed clips |
| `normalize`       | Peak normalization            |
| `master_gain`     | Final output gain             |

---

5️⃣ Ducking Configuration

```json
"ducking": {
  "enabled": true,
  "mode": "audacity",
  "duck_amount": -6,
  "fade_down_ms": 500,
  "fade_up_ms": 500,
  "min_pause_ms": 300,
  "onset_delay_ms": 120,
  "rules": [
    { "when": "voice", "duck": ["background"] }
  ]
}
```

What This Means

Music ducks after dialogue actually begins
Ducking is smooth and natural
Short dialogue gaps don’t cause pumping

| Field            | Meaning                    |
| ---------------- | -------------------------- |
| `mode`           | Ducking style (`audacity`) |
| `duck_amount`    | Gain reduction in dB       |
| `fade_down_ms`   | Fade into duck             |
| `fade_up_ms`     | Recovery fade              |
| `min_pause_ms`   | Ignore micro pauses        |
| `onset_delay_ms` | Delay before ducking       |
| `rules`          | Role-based behavior        |

---

6️⃣ Dialogue Compression

```json
"dialogue_compression": {
  "enabled": true,
  "threshold": -22,
  "ratio": 2.5,
  "attack_ms": 20,
  "release_ms": 180,
  "makeup_gain": 1
}
```

Used only on voice tracks.

Purpose:

Consistent loudness
No ear fatigue
Broadcast-style clarity

---

## 7️⃣ Scene Crossfade

```json
"scene_crossfade": {
  "enabled": true,
  "duration": 1.5
}
```

Automatically:

ades out previous scene
Fades in next scene
Overlaps scenes slightly

No silence gaps.

---

8️⃣ Loudness (LUFS)

```json
"loudness": {
  "enabled": true,
  "target_lufs": -20.0
}
```

Applied after rendering, before normalization.

Ensures:

Streaming-safe loudness
Consistent output level

---

9️⃣ Tracks — Audio Lanes

Tracks define what kind of audio this is, not when it plays.

```json
{
  "id": "music",
  "type": "music",
  "role": "background",
  "gain": -6,
  "clips": []
}
```

Track Fields

| Field   | Meaning                           |
| ------- | --------------------------------- |
| `id`    | Unique identifier                 |
| `type`  | music / voice / sfx / ambience    |
| `role`  | background / voice / foreground   |
| `gain`  | Track-wide gain                   |
| `clips` | (usually empty when using scenes) |

📌 With scenes, clips are usually declared inside scenes, not here.

---

🔟 Scenes — Story Blocks

Scenes define when and why audio plays.

```json
{
  "id": "scene_1",
  "name": "Opening Atmosphere",
  "start": 0,
  "duration": 40,
  "energy": 0.4,
  "tracks": {}
}
```

Scene Fields

| Field      | Meaning                       |
| ---------- | ----------------------------- |
| `id`       | Scene identifier              |
| `name`     | Human-readable name           |
| `start`    | Start time (sec)              |
| `duration` | Scene length                  |
| `energy`   | Narrative intensity (0.0–1.0) |
| `tracks`   | Scene-local clips             |

---

1️⃣1️⃣ Scene Energy (Important)

```json
"energy": 0.0 → very restrained  
"energy": 0.5 → neutral  
"energy": 1.0 → intense
```

Used to:

Adjust music presence
Drive cinematic ramps
Enable story-aware mixing

---

1️⃣2️⃣ Scene Tracks & Clips

```json
"tracks": {
  "music": [
    {
      "file": "audio/music/Days.mp3",
      "loop": true
    }
  ],
  "dialogue": [
    {
      "file": "audio/voice/Scene-1.wav",
      "offset": 2
    }
  ]
}
```

Clip Fields

| Field    | Meaning                   |
| -------- | ------------------------- |
| `file`   | Audio file path           |
| `start`  | Absolute start (optional) |
| `offset` | Scene-relative start      |
| `loop`   | Loop until scene ends     |
| `gain`   | Clip-level gain           |

---

1️⃣3️⃣ Rule Overrides (Scene-Level)

Scenes can override global settings:

```json
"rules": {
  "ducking": {
    "duck_amount": -18
  },
  "dialogue_compression": {
    "threshold": -22
  }
}
```

These overrides:

Apply only inside this scene
Are merged into `_rules` during preprocessing

---

## 1️⃣4️⃣ Internal Fields (Engine-Generated)

These are not written manually:

| Field                  | Purpose            |
| ---------------------- | ------------------ |
| `_rules`               | Merged rule set    |
| `fade_in` / `fade_out` | Scene transitions  |
| `scene_energy`         | Active energy      |
| `prev_scene_energy`    | For ramps          |
| `energy_ramp_duration` | Smooth transitions |

---

1️⃣5️⃣ Philosophy

Timeline.json is declarative
No DSP logic lives here
Story intent > audio tricks
Same file can render:

  Podcast
  Audio drama
  Cinematic narration

---

