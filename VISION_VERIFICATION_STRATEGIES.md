# Vision Verification Strategies

**Date**: 2025-11-15
**Branch**: `feature/vision-verification-exploration`
**Status**: Data collection phase (logging only, no behavioral changes)

---

## Executive Summary

This document explores strategies for using vision-language models (qwen3-vl) to improve human presence detection by complementing MediaPipe's real-time detection with periodic semantic verification.

**Current Implementation**: Vision verification runs every 30 seconds, comparing results with MediaPipe and logging agreement/disagreement for analysis.

**Key Insight**: The system already has robust short-term stability (PresenceGate with hysteresis, cooldown, and image similarity). Vision verification should focus on **long-term semantic validation** to catch persistent false positives that pass image similarity checks.

---

## Current System Architecture

### Existing Stability Mechanisms

#### 1. PresenceFilter (Currently Disabled)
- **Smoothing Window**: 5-frame majority voting
- **Debounce Frames**: Requires 3 consecutive frames to change state
- **Confidence Filtering**: Rejects detections below 0.7 confidence
- **Statistics**: Tracks min/max/average confidence
- **Status**: Not currently instantiated in webcam_service.py

#### 2. PresenceGate (Active & Robust)
Located in: `src/processing/presence_gate.py`

**Hysteresis Mechanism**:
```yaml
enter_k: 4    # Need 4 consecutive "different" frames to enter PRESENT state
exit_l: 5     # Need 5 consecutive "same" frames to exit PRESENT state
```

**Cooldown Logic**:
- 1-second minimum between state changes
- Prevents rapid flickering
- Tracked via timestamp comparison

**Image Similarity Gating**:
- **pHash** (perceptual hash): Distance > 14 = "different"
- **Edge-SSIM**: Structural similarity < 0.94 = "different"
- Gaussian blur preprocessing to reduce noise
- Two-stage pipeline: fast pHash, then slower SSIM if needed

**Reference Management**:
- Maintains up to 3 reference images of "empty room"
- Auto-captures after 5 seconds of stable no-human state
- Downscaled to 320x240 grayscale for efficiency

**Configuration** (`config/detection_config.yaml`):
```yaml
gating:
  enabled: true
  phash_threshold_same: 14
  ssim_threshold_same: 0.94
  hysteresis:
    enter_k: 4
    exit_l: 5
  cooldown_ms: 1000
```

#### 3. MultiModal Detection
Located in: `src/detection/multimodal_detector.py`

**Combined Confidence**:
```python
if pose_detected and face_detected:
    combined = pose_confidence * 0.6 + face_confidence * 0.4
elif pose_detected:
    combined = pose_confidence
elif face_detected:
    combined = face_confidence
```

**Pose Confidence Calculation**:
- Uses 5 key landmarks: nose, shoulders, hips
- Averages visibility scores across visible landmarks
- Range: 0.0 to 1.0

#### 4. Event System
- **PRESENCE_CHANGED** event fires on state transitions
- Implicitly rate-limited by PresenceGate cooldown (1s minimum)
- No additional event debouncing

---

## Current Gaps & Opportunities

### What's Missing

1. **No Semantic Understanding**
   - PresenceGate knows "image changed" but not "is this actually a human?"
   - Can't distinguish chair/plant/poster from actual person
   - Persistent false positives that look different enough pass through

2. **No Confidence Trend Analysis**
   - No historical confidence tracking beyond 5-frame window
   - Can't detect "hovering" confidence (stuck at 0.52 for minutes)
   - No detection of suspicious patterns (stable low, fluctuating)

3. **No Long-Term Validation**
   - Once state is stable, no periodic verification
   - False positives can persist indefinitely if they're visually consistent
   - No "sanity check" mechanism

4. **No Reference Quality Assessment**
   - References captured blindly after 5s of no-detection
   - Could capture person-like objects (chairs, plants) as "empty"
   - No verification that references are actually empty

### Where Vision Adds Value

- ✅ **Semantic validation**: "Is this actually a human?"
- ✅ **Long-term monitoring**: Periodic checks of stable states
- ✅ **Persistent false positive detection**: Catch geometry fooling MediaPipe
- ✅ **Reference quality verification**: Ensure baseline is truly empty
- ✅ **Confidence pattern analysis**: Detect suspicious MediaPipe behavior

---

## Proposed Verification Strategies

### Option 1: Confidence-Based Adaptive Interval

**Concept**: Adjust vision check frequency based on MediaPipe confidence.

```
MediaPipe Confidence → Vision Check Frequency
─────────────────────────────────────────────
0.0 - 0.3 (clear absent) → 60s (infrequent)
0.3 - 0.5 (uncertain low) → 15s (check often)
0.5 - 0.7 (uncertain high) → 15s (check often)
0.7 - 1.0 (clear present) → 60s (infrequent)
```

**Logic**:
- When MediaPipe is confident (very high or very low) → Trust it, check infrequently
- When MediaPipe is uncertain (near threshold) → Verify often
- Focuses Ollama resources where needed most

**Pros**:
- Efficient resource usage
- Smart targeting of verification
- Adaptive to situation

**Cons**:
- More complex implementation
- Needs confidence history tracking
- May miss persistent mid-confidence false positives

**Implementation Complexity**: Medium

---

### Option 2: Persistent Disagreement Override

**Concept**: Override MediaPipe when vision consistently disagrees over time.

```python
if mediapipe_state == PRESENT for duration > 3 minutes:
    if vision_says_no on last 3 consecutive checks (90s):
        if mediapipe_confidence < 0.75:
            # High confidence override action
            force_state_to_absent()
            trigger_reference_recapture()
            reset_presence_gate()
            log_override_event()
```

**Override Conditions** (all must be true):
1. MediaPipe has said "present" for 3+ minutes (persistent)
2. Vision model said "no human" on last 3 checks in a row (consistent disagreement)
3. MediaPipe confidence is below 0.75 (not super confident)

**Actions on Override**:
- Force presence state to ABSENT
- Recapture reference images (old ones may be bad)
- Reset PresenceGate streak counters
- Publish PRESENCE_CHANGED event
- Log override for analysis

**Pros**:
- Self-healing system
- Catches stuck false positives
- Conservative (requires sustained disagreement)
- Fixes bad reference images

**Cons**:
- Could override incorrectly if vision model is wrong
- Adds complexity to state machine
- May cause unexpected state changes

**Implementation Complexity**: Medium-High

---

### Option 3: State Transition Validation

**Concept**: Use vision only at critical moments (state changes).

```python
when presence_gate_is_about_to_flip_state():
    # Don't wait for 30s interval
    immediate_vision_check = verify_human_presence(current_frame)

    if vision_agrees_with_new_state:
        allow_state_transition()
    else:
        block_transition()
        increment_block_counter()

        if block_counter >= 3:
            # Vision has blocked 3 times, trust it
            force_vision_answer()
```

**When It Runs**:
- NOT on regular 30s intervals
- ONLY when PresenceGate is about to flip state
- Triggered by hysteresis threshold being met

**Logic**:
1. State about to change FALSE→TRUE or TRUE→FALSE
2. Trigger immediate vision verification
3. If vision agrees → Allow transition
4. If vision disagrees → Block transition, track blocks
5. After 3 blocks → Force vision's answer (semantic overrides visual)

**Pros**:
- Minimal Ollama usage (only at transitions)
- High impact (prevents bad state changes)
- Clean separation: MediaPipe for speed, Vision for validation

**Cons**:
- Adds latency to state transitions (~2-5 seconds for Ollama)
- Could delay legitimate presence detection
- Doesn't validate stable states

**Implementation Complexity**: Medium

---

### Option 4: Confidence Dampening

**Concept**: Use vision to modulate MediaPipe's effective confidence.

```python
every_30s_vision_check():
    if vision_agrees_with_mediapipe:
        confidence_multiplier = 1.2  # Boost
    else:
        confidence_multiplier = 0.7  # Dampen

    # Apply to next 30s of detections
    for each_frame_for_next_30s:
        effective_confidence = mediapipe_confidence * multiplier

    # This indirectly affects hysteresis:
    # - Agreement → Faster entry (higher conf), slower exit
    # - Disagreement → Slower entry (lower conf), faster exit
```

**Effect on System**:
- Agreement: Effective confidence boosted → Easier to enter PRESENT, harder to exit
- Disagreement: Effective confidence dampened → Harder to enter PRESENT, easier to exit
- Gradual influence rather than hard override

**Multiplier Decay**:
```python
# Fade multiplier back to 1.0 over 30 seconds
multiplier = 1.0 + (initial_multiplier - 1.0) * (time_remaining / 30.0)
```

**Pros**:
- Subtle, gradual influence
- No binary override (safer)
- Preserves MediaPipe responsiveness

**Cons**:
- Complex to reason about behavior
- Multiplier interactions with hysteresis unclear
- May not fix persistent false positives

**Implementation Complexity**: High

---

### Option 5: Dual-Confirmation Mode

**Concept**: Separate "MediaPipe detection" from "Vision confirmation" in API.

**State Machine**:
```
States:
├─ ABSENT              (both agree: no human)
├─ UNCONFIRMED_PRESENT (MediaPipe: yes, vision: not checked yet)
├─ CONFIRMED_PRESENT   (MediaPipe: yes, vision: yes)
└─ DISPUTED            (MediaPipe: yes, vision: no)
```

**API Response** (`/presence`):
```json
{
  "mediapipe_present": true,
  "vision_confirmed": true,
  "confidence_level": "confirmed",
  "states": {
    "mediapipe": "present",
    "vision_last_check": "yes",
    "vision_check_age_seconds": 12
  },
  "metadata": {
    "last_vision_check": "2025-11-15T10:30:45Z",
    "agreement_rate": 0.85
  }
}
```

**Client Decision Tree**:
```python
# Conservative client (low false positives)
if response["vision_confirmed"]:
    activate_voice_assistant()

# Responsive client (low latency)
if response["mediapipe_present"]:
    activate_voice_assistant()

# Balanced client
if response["confidence_level"] in ["confirmed", "unconfirmed"]:
    activate_voice_assistant()
```

**Pros**:
- No false negatives (MediaPipe still responsive)
- Clients choose their own tradeoff
- Full transparency in API
- No breaking changes to existing clients

**Cons**:
- API complexity increases
- All clients need updates to use effectively
- Ambiguous state ("unconfirmed") may confuse clients

**Implementation Complexity**: Medium

---

### Option 6: Flicker Pattern Detection

**Concept**: Detect unstable environments and adapt behavior.

**Tracking System**:
```python
# Track last 5 minutes of state changes
state_history = deque(maxlen=300)  # 5 min @ 1 check/sec

# Calculate stability metrics
flicker_count = count_state_changes(state_history)
stability_score = 1.0 - (flicker_count / 300)

if stability_score < 0.85:  # >45 flips in 5 minutes
    environment_mode = UNSTABLE
```

**Adaptive Response**:
```python
if environment_mode == UNSTABLE:
    # Increase verification frequency
    vision_check_interval = 10  # Instead of 30s

    # Add extra hysteresis
    presence_gate.enter_k = 6  # Instead of 4
    presence_gate.exit_l = 8   # Instead of 5

    # Log environment issue
    log_warning("Unstable detection environment detected")
```

**Vision Analysis**:
```python
# Use vision to diagnose flicker cause
if flickering:
    if vision_alternates_yes_no_matching_reality:
        diagnosis = "Real activity (person moving in/out)"
    elif vision_consistently_says_no:
        diagnosis = "False positive flicker (geometry issue)"
    elif vision_consistently_says_yes:
        diagnosis = "False negative flicker (MediaPipe threshold issue)"
```

**Pros**:
- Self-tuning system
- Adaptive to environment challenges
- Diagnoses root cause of instability
- Can alert user to camera/lighting issues

**Cons**:
- Requires long-term state tracking
- More memory usage
- Complex stability calculations
- May be overkill for stable environments

**Implementation Complexity**: High

---

## Recommendations

### Phase 1: Current State (DONE)
✅ **Pure Logging Mode**
- Vision checks every 30s
- Logs agreement/disagreement
- Zero behavioral impact
- Collect data for 1-2 weeks

**Goal**: Understand real-world agreement patterns

### Phase 2: Low-Risk Enhancement
🎯 **Recommended Next Step**

**Option 2 (Persistent Disagreement Override)** with conservative thresholds:
- Requires 5+ minutes of MediaPipe "present" (not 3)
- Requires 4+ consecutive vision "no" checks (not 3)
- Only override if MediaPipe confidence < 0.70 (not 0.75)
- Add "override disable" config flag for safety

**Why This First**:
- Addresses core issue (persistent false positives)
- Conservative triggers minimize risk
- Self-healing via reference recapture
- Easy to disable if problems occur
- Clear logging for debugging

### Phase 3: Advanced Features
After Option 2 proves stable, consider:

1. **Option 1 (Adaptive Interval)** - Optimize Ollama usage
2. **Option 6 (Flicker Detection)** - Handle unstable environments
3. **Option 5 (Dual-Confirmation API)** - Give clients control

**Avoid** (for now):
- Option 3 (State Transition Validation) - Adds latency
- Option 4 (Confidence Dampening) - Too complex

---

## Configuration Design

### Proposed Config Structure

```yaml
# config/vision_verification_config.yaml

vision_verification:
  enabled: true
  model: "qwen3-vl:2b-instruct-q4_K_M"

  # Base interval (Option 1 can override)
  check_interval_seconds: 30

  # Adaptive interval (Option 1)
  adaptive_interval:
    enabled: false
    confident_interval_seconds: 60    # When MediaPipe is sure
    uncertain_interval_seconds: 15    # When MediaPipe is borderline
    confidence_threshold_low: 0.3
    confidence_threshold_high: 0.7

  # Persistent disagreement override (Option 2)
  override:
    enabled: false
    require_mediapipe_present_duration_seconds: 300  # 5 minutes
    require_consecutive_vision_no_count: 4           # 4 checks = 120s
    max_mediapipe_confidence_for_override: 0.70      # Only if not super confident
    action_on_override: "force_absent_and_recapture" # or "log_only"

  # State transition validation (Option 3)
  transition_validation:
    enabled: false
    max_blocks_before_force: 3
    timeout_seconds: 10  # Max wait for Ollama response

  # Confidence dampening (Option 4)
  confidence_modulation:
    enabled: false
    agreement_boost: 1.2
    disagreement_dampen: 0.7
    decay_over_seconds: 30

  # Flicker detection (Option 6)
  flicker_detection:
    enabled: false
    tracking_window_seconds: 300  # 5 minutes
    stability_threshold: 0.85     # <85% = unstable
    unstable_check_interval_seconds: 10
    unstable_enter_k: 6
    unstable_exit_l: 8

  # Caching (already implemented)
  cache_ttl_seconds: 30

  # Logging
  log_level: "INFO"  # DEBUG shows all comparisons
  log_disagreements_only: false
```

---

## Key Questions to Answer

Before implementing any strategy, clarify:

### 1. What should happen when vision disagrees?
- [ ] Just log it (current - safe for learning)
- [ ] Force state change (aggressive)
- [ ] Influence confidence (subtle)
- [ ] Block state transitions (preventive)

### 2. How aggressive should vision be?
- [ ] Advisory only (safe, learn first)
- [ ] Override on persistent disagreement (medium risk)
- [ ] Hard veto power (risky but effective)

### 3. What's the primary goal?
- [ ] Reduce false positives (kitchen geometry issue)
- [ ] Catch false negatives (MediaPipe missing real people)
- [ ] Both equally
- [ ] Validate system health long-term

### 4. Acceptable latency?
- [ ] 30s delay to correct false positives is fine
- [ ] Need faster intervention (<10s)
- [ ] Real-time critical (use Option 3)

### 5. Ollama resource constraints?
- [ ] Shared with other services (minimize usage)
- [ ] Dedicated to webcam service (can check more often)
- [ ] Cost/performance sensitive (adaptive interval needed)

---

## Testing Strategy

### Metrics to Track

**Agreement Metrics**:
- Overall agreement rate (%)
- Agreement when MediaPipe confident (>0.8)
- Agreement when MediaPipe uncertain (0.4-0.6)
- False positive detection rate (vision=no, MediaPipe=yes)
- False negative detection rate (vision=yes, MediaPipe=no)

**Performance Metrics**:
- Vision check latency (p50, p95, p99)
- Ollama queue depth
- Cache hit rate
- State transition latency (if Option 3)

**Stability Metrics**:
- State changes per hour
- Average time in each state
- Override events per day (if Option 2)
- Blocked transitions per day (if Option 3)

### Test Scenarios

1. **Empty Room Baseline**
   - Let system run for 1 hour with no people
   - Expected: Both agree "no human" consistently
   - Measures: False positive rate

2. **Persistent Presence**
   - Sit in view for 30 minutes
   - Expected: Both agree "human present" consistently
   - Measures: False negative rate, agreement on true positives

3. **Kitchen Geometry Challenge**
   - Stand where geometry causes MediaPipe issues
   - Expected: Vision correctly identifies false positives
   - Measures: Vision's semantic accuracy advantage

4. **Rapid Movement**
   - Walk in/out of frame repeatedly
   - Expected: MediaPipe fast, vision validates on interval
   - Measures: Responsiveness vs. accuracy tradeoff

5. **Edge Cases**
   - Partial occlusion (half in frame)
   - Low lighting
   - Person-like objects (chair, poster)
   - Measures: Robustness to edge conditions

---

## Implementation Checklist

### Phase 1: Data Collection (DONE ✓)
- [x] VisionPresenceVerifier module created
- [x] 30s periodic verification integrated
- [x] Logging of agreement/disagreement
- [x] Agreement rate tracking
- [x] Unit tests (29 passing)

### Phase 2: Option 2 Implementation
- [ ] Add vision_verification_config.yaml
- [ ] Implement persistent disagreement tracking
- [ ] Add override logic with safety checks
- [ ] Integrate reference recapture on override
- [ ] Add override event publishing
- [ ] Create override metrics/logging
- [ ] Write integration tests
- [ ] Add configuration flags for safe rollout
- [ ] Document override behavior in API

### Phase 3: Advanced Features
- [ ] Implement chosen additional options
- [ ] Performance optimization
- [ ] Dashboard for monitoring
- [ ] Alert system for anomalies

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2025-11-15 | Use qwen3-vl:2b-instruct-q4_K_M | Fast, direct responses for binary yes/no |
| 2025-11-15 | 30-second verification interval | Balance between Ollama load and validation frequency |
| 2025-11-15 | Start with pure logging | Gather data before behavioral changes |
| TBD | Choose implementation strategy | After analyzing real-world agreement data |

---

## Next Steps

1. **Let current implementation run for 1-2 weeks**
   - Collect agreement rate data
   - Identify patterns of disagreement
   - Analyze false positive scenarios

2. **Analyze collected data**
   - What's the baseline agreement rate?
   - When does disagreement happen most?
   - Is it catching false positives as expected?

3. **Choose implementation strategy**
   - Based on data, select Option 2, 1, 3, or combination
   - Configure conservative thresholds
   - Plan rollout

4. **Implement chosen strategy**
   - Add configuration structure
   - Implement logic with safety flags
   - Test thoroughly
   - Deploy with monitoring

5. **Iterate based on results**
   - Tune thresholds
   - Add additional strategies if needed
   - Optimize performance

---

## References

- **Code**: `src/ollama/vision_verifier.py`
- **Integration**: `webcam_service.py` lines 321-358
- **Config**: `config/ollama_config.yaml`
- **Tests**: `tests/test_ollama/test_vision_verifier.py` (29 tests)
- **Branch**: `feature/vision-verification-exploration`

---

## Appendix: Vision Model Comparison

### qwen3-vl:2b-instruct vs qwen3-vl:2b-thinking

**Instruct Model** (currently using):
- Optimized for direct instruction following
- Faster (fewer tokens generated)
- Predictable yes/no format
- Best for binary decisions

**Thinking Model** (alternative):
- Shows chain-of-thought reasoning
- Explains WHY it decided yes/no
- Better for debugging false positives
- Slower (more tokens)
- Example output: "I see a vertical shape near the counter, but examining the context and lack of human features like a face, this appears to be a kitchen cabinet. Answer: no, certain"

**Recommendation**:
- Use **instruct** for production (current choice)
- Consider **thinking** for debugging specific false positive scenarios
- Thinking model output could inform prompt engineering for instruct model
