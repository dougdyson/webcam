# MediaPipe Defaults Migration Guide

This guide helps you migrate from custom gesture names to MediaPipe default gesture names.

## 🎯 Quick Summary

The gesture recognition system now returns **raw MediaPipe gesture names** instead of custom interpretations, giving you full control over how to interpret gestures in your application.

## ⚠️ Breaking Changes

### Gesture Name Changes

| Old Custom Name | New MediaPipe Default | Description |
|-----------------|----------------------|-------------|
| `"stop"` | `"Open_Palm"` | Open palm facing camera |
| `"peace"` | `"Victory"` | Peace sign / Victory sign |
| `"none"` | `"Unknown"` | No gesture detected |
| `"hand_up"` | `"Open_Palm"` | Generic hand up → specific open palm |

### New Gestures Available

You now have access to **all 8 MediaPipe gestures**:
- `"Unknown"` - Unrecognized gesture
- `"Closed_Fist"` - Closed fist
- `"Open_Palm"` - Open palm (was "stop")
- `"Pointing_Up"` - Index finger pointing upward
- `"Thumb_Up"` - Thumbs up
- `"Thumb_Down"` - Thumbs down
- `"Victory"` - Victory/Peace sign (was "peace")
- `"ILoveYou"` - ASL "I Love You" sign

## 🔧 Code Migration Examples

### HTTP API Clients

**Before:**
```python
response = requests.get("http://localhost:8767/presence")
gesture = response.json().get("gesture_type")

if gesture == "stop":
    voice_assistant.stop()
elif gesture == "peace":
    enable_peace_mode()
```

**After:**
```python
response = requests.get("http://localhost:8767/presence")
gesture = response.json().get("gesture_type")

# Custom interpretation based on MediaPipe defaults
if gesture == "Open_Palm":
    voice_assistant.stop()  # Your interpretation: stop
elif gesture == "Victory":
    enable_peace_mode()     # Your interpretation: peace mode
elif gesture == "Thumb_Up":
    voice_assistant.continue_listening()  # New possibility!
```

### SSE Event Handling

**Before:**
```python
def handle_gesture(event):
    if event["gesture_type"] == "stop":
        emergency_stop()
```

**After:**
```python
def handle_gesture(event):
    gesture = event["gesture_type"]
    confidence = event["confidence"]
    
    if confidence < 0.8:  # Add confidence check
        return
        
    # Define your own interpretation mapping
    action_mapping = {
        "Open_Palm": emergency_stop,
        "Victory": enable_peaceful_mode,
        "Thumb_Up": approve_action,
        "Thumb_Down": reject_action,
        "Closed_Fist": mute_system
    }
    
    action = action_mapping.get(gesture)
    if action:
        action()
```

### Voice Assistant Integration

**Before:**
```python
# Limited to one gesture
if gesture_detected and gesture_type == "stop":
    voice_assistant.pause()
```

**After:**
```python
# Rich gesture vocabulary
gesture_commands = {
    "Open_Palm": voice_assistant.pause,
    "Victory": voice_assistant.set_peace_mode,
    "Thumb_Up": voice_assistant.continue_listening,
    "Thumb_Down": voice_assistant.reject_command,
    "Pointing_Up": voice_assistant.attention_mode,
    "Closed_Fist": voice_assistant.mute
}

if gesture_detected:
    command = gesture_commands.get(gesture_type)
    if command:
        command()
```

## 🏠 Smart Home Use Cases

### Kitchen Automation
```python
# Kitchen-specific gesture interpretation
kitchen_gestures = {
    "Open_Palm": "stop_all_appliances",
    "Victory": "cooking_complete_celebration", 
    "Thumb_Up": "approve_recipe_step",
    "Thumb_Down": "skip_recipe_step",
    "Pointing_Up": "set_timer",
    "Closed_Fist": "emergency_stop"
}
```

### Entertainment System
```python
# Entertainment-specific interpretation
entertainment_gestures = {
    "Open_Palm": "pause_media",
    "Victory": "peace_and_quiet_mode",
    "Thumb_Up": "like_content", 
    "Thumb_Down": "dislike_content",
    "Pointing_Up": "volume_up",
    "Closed_Fist": "mute_everything"
}
```

## 🧪 Testing Your Migration

### 1. Update Gesture Names
```python
# Test your gesture handling
test_gestures = [
    {"gesture_type": "Open_Palm", "confidence": 0.9},
    {"gesture_type": "Victory", "confidence": 0.85},
    {"gesture_type": "Thumb_Up", "confidence": 0.8}
]

for gesture_event in test_gestures:
    handle_gesture(gesture_event)
```

### 2. Validate Confidence Thresholds
```python
# Add confidence filtering
def handle_gesture_safely(event):
    if event["confidence"] < 0.7:  # Ignore low confidence
        return
        
    # Your gesture handling logic
    process_gesture(event["gesture_type"])
```

### 3. Test All 8 Gestures
```python
# Comprehensive gesture test
all_gestures = [
    "Unknown", "Closed_Fist", "Open_Palm", "Pointing_Up",
    "Thumb_Down", "Thumb_Up", "Victory", "ILoveYou"
]

for gesture in all_gestures:
    test_gesture_response(gesture)
```

## ✅ Migration Checklist

- [ ] Update gesture name strings in your code
- [ ] Add confidence threshold checking (recommended: 0.7+)
- [ ] Define custom interpretation mapping for your use case
- [ ] Test with multiple gesture types
- [ ] Update documentation/comments in your code
- [ ] Consider using new gestures (Thumb_Up, Thumb_Down, etc.)

## 🚀 Benefits of Migration

### Before (Custom Names)
- Limited to 2-3 custom interpretations
- Hard-coded meaning in the service
- No flexibility for different use cases

### After (MediaPipe Defaults)
- All 8 MediaPipe gestures available
- Full client-side interpretation control
- Same gesture can mean different things in different contexts
- Standard MediaPipe naming for consistency

## 🆘 Getting Help

If you encounter issues during migration:

1. **Check the updated examples**: See `docs/examples/` for comprehensive patterns
2. **Review confidence scores**: Low confidence may indicate detection issues
3. **Test gesture mapping**: Verify your interpretation logic with different gestures
4. **Validate service connectivity**: Ensure gesture events are flowing correctly

The migration gives you much more power and flexibility - enjoy building with all 8 MediaPipe gestures! 🎉 