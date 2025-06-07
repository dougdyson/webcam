# Enhanced Room Description Prompts

## Overview

The enhanced room description system provides context-aware, structured descriptions of your webcam feed that are specifically designed for conversational AI integration. Works with any room type: kitchen, office, living room, bedroom, workshop, etc.

Instead of generic, variable descriptions, you get consistent, spatially-aware descriptions that focus on activities, objects, and locations. Colors are provided through the room layout reference rather than unreliable image-based color detection.

## Key Benefits

- **Any Room Type**: Works with kitchen, office, living room, bedroom, etc.
- **Consistent Format**: Structured output with predictable sections
- **Spatial Awareness**: Uses your room layout for better context
- **Activity-Focused**: Emphasizes what people are doing, not just what's visible
- **Reliable Colors**: Colors from layout reference, not unreliable image detection
- **AI-Ready**: Perfect for injection into conversational AI system prompts

## Quick Start

### 1. Create Your Room Layout Description

Create a file `config/room_layout.txt` with your room's layout and colors:

```
ROOM LAYOUT REFERENCE:
======================

ROOM TYPE: Kitchen

MAIN AREAS:
- Island/Center: Large wooden butcher block island (warm brown wood) with white bar stools
- Main Counter: Right wall with sink, white/cream countertops, light gray cabinets
- Stove Area: Back wall with stainless steel range and black hood
- Refrigerator: Far right corner, stainless steel finish
- Table Area: Left side with dark wood dining table and black chairs

COMMON OBJECTS & THEIR TYPICAL LOCATIONS:
- Coffee maker: Usually on main counter near sink (black or silver)
- Fruit bowl: Often on island center (ceramic, white or blue)
- Cutting boards: Either on island or main counter (wood or white plastic)

COLOR REFERENCE FOR IDENTIFICATION:
- Island surface: Warm brown butcher block wood
- Main counters: White/cream solid surface
- Cabinets: Light gray painted finish
- Bar stools: White leather/fabric seats
- Appliances: Stainless steel (refrigerator, range)
- Table: Dark walnut wood
- Chairs: Black painted wood
```

### 2. Update Your Configuration

```python
from ollama.description_service import DescriptionServiceConfig

# Load your room layout
with open('config/room_layout.txt', 'r') as f:
    room_layout = f.read()

# Create enhanced config
config = DescriptionServiceConfig(
    use_room_context=True,
    room_layout_context=room_layout,
    cache_ttl_seconds=300,  # 5 minutes
    enable_caching=True
)

# Your existing service setup works the same
description_service = DescriptionService(
    ollama_client=ollama_client,
    image_processor=image_processor,
    config=config  # Now uses enhanced prompts!
)
```

### 3. Get Structured Descriptions

The service now returns descriptions in this format:

```
Currently: Person preparing food at island counter. 
Present: One person, cutting board, knife, vegetables, coffee mug. 
Location details: Activity centered on island, ingredients spread across warm brown butcher block surface, white coffee mug near left edge toward bar stools.
```

## Enhanced Prompt Structure

The system sends this structured prompt to your vision model:

```
This is a webcam view of an indoor space. Provide a concise, structured description focusing on:

PEOPLE & ACTIVITIES: Who is present and what they are doing (working, cooking, relaxing, etc.)
OBJECTS & ITEMS: What furniture, equipment, or items are visible and their general location
SPATIAL CONTEXT: Where things are located (which area, surface, or zone) using the layout reference below

ROOM LAYOUT REFERENCE:
[Your room layout with color information goes here]

Format your response as: "Currently: [brief activity description]. Present: [people/objects]. Location details: [spatial info]."

IMPORTANT: Do NOT attempt to identify colors from the image as they are unreliable. Instead, use the room layout reference above for any color information needed for object identification. Focus on what would be useful context for a conversation.
```

## Room Type Examples

### Kitchen
```
ROOM TYPE: Kitchen
MAIN AREAS: Island, counters, stove area, refrigerator corner
COLORS: Warm brown wood island, white counters, stainless appliances
```

### Office
```
ROOM TYPE: Office
MAIN AREAS: Desk area, bookshelf wall, meeting corner, storage zone
COLORS: Dark wood desk, black monitor, blue ergonomic chair, white walls
```

### Living Room
```
ROOM TYPE: Living Room
MAIN AREAS: Seating area, entertainment center, coffee table zone
COLORS: Gray sectional sofa, black TV stand, light wood coffee table
```

### Bedroom
```
ROOM TYPE: Bedroom
MAIN AREAS: Bed area, dresser wall, reading corner, closet
COLORS: White bedding, dark wood furniture, beige carpet
```

## Integration with Conversational AI

### Basic Integration

```python
# Get latest description
latest_desc = description_service.get_latest_description()

if latest_desc and latest_desc.success:
    # Add to your AI conversation context
    system_context = f"Room status: {latest_desc.description}"
    # Use in your voice assistant or chatbot
```

### Advanced Integration with Color Context

```python
def update_ai_context():
    """Update AI context with current room status including color references."""
    desc = description_service.get_latest_description()
    
    if desc and desc.success and not desc.cached:
        # Only update on fresh descriptions
        context_parts = desc.description.split('. ')
        
        current_activity = context_parts[0].replace('Currently: ', '')
        present_items = context_parts[1].replace('Present: ', '')
        location_info = context_parts[2].replace('Location details: ', '')
        
        return {
            'activity': current_activity,
            'items': present_items,
            'spatial': location_info,
            'timestamp': desc.timestamp,
            'confidence': desc.confidence,
            'has_color_context': True  # Colors from layout, not detection
        }
    
    return None

# In your voice assistant loop
room_context = update_ai_context()
if room_context:
    system_prompt = f"""
    You are a helpful assistant. Current room status:
    Activity: {room_context['activity']}
    Items present: {room_context['items']}
    Spatial context: {room_context['spatial']}
    
    Note: Color information is reliable as it comes from the room layout reference.
    Use this context to provide relevant assistance.
    """
```

## Configuration Options

### DescriptionServiceConfig Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `use_room_context` | `True` | Enable room-specific prompting |
| `room_layout_context` | `""` | Your room layout description with colors |
| `cache_ttl_seconds` | `300` | Cache descriptions for 5 minutes |
| `enable_caching` | `True` | Use caching for performance |
| `timeout_seconds` | `30.0` | Vision processing timeout |

### Disabling Enhanced Prompts

If you want to go back to basic prompts:

```python
config = DescriptionServiceConfig(
    use_room_context=False,
    # Your other settings...
)
```

This will use the simple default prompt: "Describe what you see in this image. Be concise and specific."

## Color Handling Strategy

### Why This Approach Works Better

1. **Vision Model Limitations**: Color detection from images is notoriously unreliable
2. **Consistent Reference**: Your layout provides stable color information
3. **Context-Aware**: Colors are tied to specific objects and locations
4. **Conversation Ready**: Color descriptions make sense in conversational context

### Example Color Benefits

**Before (unreliable image detection):**
```
"Person at some kind of surface with items" (missed brown wood island)
```

**After (layout color reference):**
```
"Person preparing food at warm brown butcher block island"
```

## Performance Considerations

- **Caching**: Enhanced prompts are cached just like regular descriptions
- **Prompt Length**: Longer prompts but much better context quality
- **Processing Time**: No significant increase in processing time
- **Memory**: Room layout is loaded once and reused
- **Color Accuracy**: 100% reliable vs. unreliable image-based detection

## Example Output Comparison

### Before (Generic Prompt)
```
"A person standing in a room with some furniture. There appears to be a table and some objects."
```

### After (Enhanced Room Prompt with Colors)
```
"Currently: Person working at computer in office area. Present: One person, laptop, documents, coffee mug. Location details: Activity at dark wood desk, papers spread across surface, white coffee mug positioned near black monitor on right side."
```

## Example Files

- `examples/enhanced_room_description.py` - Complete working example for any room
- `examples/update_existing_system.py` - Simple upgrade guide
- `config/room_layout.txt` - Sample room layout with colors

## Testing

Run the example to test your setup:

```bash
python examples/enhanced_room_description.py
```

This will:
1. Load your room layout (any room type)
2. Show the enhanced prompt with color handling
3. Test description generation
4. Demonstrate caching
5. Show integration examples

## Migration Guide

### From Basic to Enhanced Prompts

1. **Determine your room type** (kitchen, office, living room, etc.)
2. **Create room layout file** in `config/room_layout.txt` with color information
3. **Update config creation**:
   ```python
   # Old
   config = DescriptionServiceConfig()
   
   # New
   config = DescriptionServiceConfig(
       use_room_context=True,
       room_layout_context=load_room_layout()
   )
   ```
4. **Test with examples** to ensure quality improvements
5. **Update your AI integration** to use structured format with color context

The change is backward compatible - existing code will work with enhanced descriptions providing better quality output and reliable color information. 