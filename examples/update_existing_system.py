#!/usr/bin/env python3
"""
Update Existing System with Enhanced Room Descriptions

This script shows how to update your existing webcam description system
to use the new room-specific prompts with minimal changes.

Works with any room type: kitchen, office, living room, bedroom, etc.
"""

import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ollama.description_service import DescriptionServiceConfig


def load_room_layout_from_file(file_path: str = "config/room_layout.txt") -> str:
    """Load your room layout description from a file."""
    try:
        with open(file_path, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        print(f"Room layout file not found: {file_path}")
        return ""


def create_room_layout_inline() -> str:
    """
    Create a room layout description inline.
    Customize this to match your actual room layout and type.
    """
    return """
ROOM LAYOUT REFERENCE:
======================

ROOM TYPE: Kitchen

MAIN AREAS:
- Island with wooden countertop (warm brown) in center
- Sink area on right wall with white counters
- Stove/range on back wall (stainless steel)
- Refrigerator in far right corner (stainless steel)
- Dining table on left side (dark wood)

COMMON OBJECTS & THEIR TYPICAL LOCATIONS:
- Coffee maker: Usually near sink (black or silver)
- Fruit bowl: Typically on island center (white or blue ceramic)
- Cutting boards: On island or main counter (wood or white plastic)

COLOR REFERENCE FOR IDENTIFICATION:
- Island surface: Warm brown wood
- Counters: White/cream
- Appliances: Stainless steel
- Table: Dark walnut wood
"""


def update_your_existing_config():
    """
    Example of how to update your existing DescriptionServiceConfig
    to use enhanced room-specific prompts.
    """
    
    # Load room layout (choose one approach):
    
    # Option 1: Load from file
    room_layout = load_room_layout_from_file()
    
    # Option 2: Use inline description if no file
    if not room_layout:
        room_layout = create_room_layout_inline()
    
    # Create enhanced configuration
    # If you already have a config, just add these parameters:
    enhanced_config = DescriptionServiceConfig(
        # Your existing settings (if any)
        cache_ttl_seconds=300,
        timeout_seconds=30.0,
        enable_caching=True,
        
        # NEW: Enhanced room-specific settings
        use_room_context=True,
        room_layout_context=room_layout,
    )
    
    return enhanced_config


def preview_enhanced_prompt():
    """Preview what the enhanced prompt looks like."""
    config = update_your_existing_config()
    
    print("Enhanced Prompt Preview:")
    print("=" * 50)
    print(config.get_enhanced_prompt())
    print("=" * 50)
    
    # Show comparison with default
    print("\nVs. Default Prompt:")
    print("-" * 30)
    default_config = DescriptionServiceConfig(use_room_context=False)
    print(default_config.get_enhanced_prompt())


def integration_checklist():
    """Show a simple checklist for integrating enhanced descriptions."""
    print("\n✅ Integration Checklist:")
    print("1. Create/update your room layout description (any room type)")
    print("2. Include color information in the layout for reliable color context")
    print("3. Update your DescriptionServiceConfig with room context")
    print("4. Test the enhanced prompts")
    print("5. Update your conversational AI to use structured descriptions")
    print("6. Monitor the consistency improvements")
    
    print("\n📝 Quick Integration Code:")
    print("""
# Replace your existing config creation with:
config = DescriptionServiceConfig(
    use_room_context=True,
    room_layout_context=your_room_layout_text,
    # ... your other existing settings
)

# Your existing service creation stays the same:
description_service = DescriptionService(
    ollama_client=ollama_client,
    image_processor=image_processor,
    config=config  # Now uses enhanced prompts
)
""")


def show_room_type_examples():
    """Show examples for different room types."""
    print("\n🏠 Room Type Examples:")
    print("=" * 25)
    
    examples = {
        "Kitchen": "Islands, counters, appliances, cooking areas",
        "Office": "Desk, monitor, chair, bookshelves, filing cabinets", 
        "Living Room": "Sofa, coffee table, TV, lamps, side tables",
        "Bedroom": "Bed, dresser, nightstands, closet, reading chair",
        "Workshop": "Workbench, tools, storage, project areas",
    }
    
    for room_type, description in examples.items():
        print(f"• {room_type}: {description}")
    
    print("\nJust replace 'ROOM TYPE: Kitchen' with your room type and")
    print("update the areas, objects, and colors accordingly!")


if __name__ == "__main__":
    print("Enhanced Room Description Integration")
    print("=" * 42)
    
    # Show the enhanced prompt
    preview_enhanced_prompt()
    
    # Show room type examples
    show_room_type_examples()
    
    # Show integration steps
    integration_checklist()
    
    print("\n🎯 Expected Benefits:")
    print("- More consistent description format for any room type")
    print("- Better spatial awareness and context")
    print("- Reliable color information from layout reference")
    print("- Reduced reliance on unreliable image-based color detection")
    print("- Structured output perfect for AI conversation context")
    print("- Improved relevance for room-specific interactions") 