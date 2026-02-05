# Test Results

Comprehensive test status for the audio engine.

---

## Test Summary

| Category | Status | Tests |
|----------|--------|-------|
| Core Rendering | ✅ Pass | Timeline, tracks, clips |
| Scene System | ✅ Pass | Preprocessing, rule merging |
| DSP Pipeline | ✅ Pass | Full processing chain |
| Ducking | ✅ Pass | Envelope-based, semantic roles |
| EQ System | ✅ Pass | Presets, tonal shaping |
| Fade Curves | ✅ Pass | Linear, logarithmic, exponential |
| SFX Processing | ✅ Pass | Semantic roles, loudness |
| LUFS Loudness | ✅ Pass | Target: -20 LUFS |

---

## LUFS Loudness Test

| Parameter | Target | Measured | Status |
|-----------|--------|----------|--------|
| Integrated LUFS | -20.0 | -20.00 | ✅ PASS |
| True Peak | -1.0 dBFS | < -1.0 dBFS | ✅ PASS |

---

## Crossfade + Looping Test (TEST-13)

**Test Goal:** Validate interaction between scene transitions, looping background music, and fade behavior at scene boundaries.

**Observed Behavior:**
- Scene 1 music fades out smoothly over configured duration
- Scene 2 music starts after Scene 1 ends
- Fade-in of Scene 2 does not overlap with fade-out of Scene 1
- No silence gap perceived
- No clicks, pops, or loop artifacts
- No audible restart sensation
- Overall transition feels natural and acceptable

**Timeline Representation:**
```
Scene 1:  0 ─────────────── 20
                   ↘ fade out (16–20)

Scene 2:                      20 ───────────────
                               ↗ fade in (20–24)
```

**Verdict:** ✅ PASS — Sequential fade accepted for Intermediate phase

---

## Fade Intensity Test (TEST-1)

**Test Goal:** Verify fade intensity and smoothness.

**Results:**
- Fade-in applies correctly at clip start
- Fade-out applies correctly at clip end
- No clicks or pops at fade boundaries
- Pre-attenuation works as expected

**Verdict:** ✅ PASS

---

## EQ System Tests

### Preset Application Test

| Preset | Applied Correctly | Audio Quality |
|--------|-------------------|---------------|
| `dialogue_clean` | ✅ | Clear, no rumble |
| `dialogue_warm` | ✅ | Rich tone |
| `dialogue_broadcast` | ✅ | Broadcast presence |
| `music_bed` | ✅ | Carves dialogue space |
| `background_soft` | ✅ | Non-invasive |
| `sfx_punch` | ✅ | Impactful low end |

**Verdict:** ✅ PASS

### Scene Tonal Shaping Test

| Tilt | Applied Correctly | Perceptual Result |
|------|-------------------|-------------------|
| `warm` | ✅ | Warmer, less bright |
| `neutral` | ✅ | No change |
| `bright` | ✅ | Brighter, clearer |

**Verdict:** ✅ PASS

---

## Fade Curves Tests

### Curve Generation Test

| Curve | Range | Shape |
|-------|-------|-------|
| Linear | 0.0 → 1.0 | Straight line |
| Logarithmic | 0.0 → 1.0 | Slow start, fast end |
| Exponential | 0.0 → 1.0 | Fast start, slow end |

**Verdict:** ✅ PASS

### Audio Application Test

| Test | Result |
|------|--------|
| Linear fade-in | ✅ Sounds constant rate |
| Logarithmic fade-in | ✅ Sounds natural |
| Exponential fade-out | ✅ Sounds dramatic |
| Backward compatibility | ✅ Number format works |
| Mixed format | ✅ Object and number work together |

**Verdict:** ✅ PASS

---

## SFX Semantic Role Tests

### Baseline vs Semantic Comparison

**Test Files:**
- `test/test_sfx_baseline.json` — SFX without semantic roles
- `test/test_sfx_semantic.json` — SFX with semantic roles

**Expected Differences:**

| Aspect | Baseline | Semantic | Result |
|--------|----------|----------|--------|
| Loudness | All -20 LUFS | Role-specific | ✅ Different |
| Fades | None/default | Role-specific | ✅ Different |
| Ducking | Standard | Semantic-aware | ✅ Different |

**Commands:**
```bash
python main.py test/test_sfx_baseline.json output/test_sfx_baseline.wav
python main.py test/test_sfx_semantic.json output/test_sfx_semantic.wav
```

**Verdict:** ✅ PASS

---

## Ducking Tests

### Envelope-Based Ducking

| Scenario | Result |
|----------|--------|
| Voice starts → music ducks | ✅ Smooth fade down |
| Voice ends → music recovers | ✅ Smooth fade up |
| Short pauses ignored | ✅ min_pause_ms works |
| Onset delay applied | ✅ No pre-duck artifacts |

**Verdict:** ✅ PASS

### Semantic Role Ducking

| Rule | Result |
|------|--------|
| `voice` → `sfx:ambience` | ✅ Ambience ducks |
| `sfx:impact` → `music` | ✅ Music ducks |
| Unlisted roles | ✅ Not affected |

**Verdict:** ✅ PASS

---

## Integration Tests

### Full Pipeline Test

| Stage | Status |
|-------|--------|
| JSON parsing | ✅ |
| Scene preprocessing | ✅ |
| Validation | ✅ |
| Auto-fix overlaps | ✅ |
| Clip processing | ✅ |
| Track mixing | ✅ |
| Master processing | ✅ |
| WAV export | ✅ |

**Verdict:** ✅ PASS

### Backward Compatibility Test

| Feature | Old Format | New Format | Both Work |
|---------|------------|------------|-----------|
| Fades | Number | Object | ✅ |
| EQ | (none) | Preset | ✅ |
| Semantic roles | (none) | String | ✅ |

**Verdict:** ✅ PASS

---

## Performance Notes

| Operation | Duration | Notes |
|-----------|----------|-------|
| 30s timeline | ~2-3s | Acceptable |
| 2min timeline | ~8-10s | Acceptable |
| EQ processing | +5-10% | Minimal impact |
| SFX processing | +2-5% | Minimal impact |

---

## Testing Philosophy

> **If debug output matches what you hear, the system is trusted.**

All tests verify:
1. Correct DSP application
2. Expected perceptual result
3. No artifacts (clicks, pops, distortion)
4. Backward compatibility
5. Deterministic output

---

*Last updated: February 2026*
