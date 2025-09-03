#!/usr/bin/env python3
"""
Test Room Layout Integration

Simple test to verify that room layout context is properly included
in DescriptionResult for conversational AI integration.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.ollama.description_service import DescriptionServiceConfig, DescriptionResult
from datetime import datetime

def test_room_layout_integration():
    """Test that room layout is properly included in results."""
    print("🧪 Testing Room Layout Integration")
    print("=" * 35)
    
    # Test 1: Load room layout from file
    try:
        layout_file = project_root / "config" / "room_layout.txt"
        if layout_file.exists():
            room_layout = layout_file.read_text().strip()
            print(f"✅ Room layout loaded ({len(room_layout)} chars)")
            print(f"   Preview: {room_layout[:100]}...")
        else:
            print("❌ Room layout file not found")
            return False
    except Exception as e:
        print(f"❌ Error loading room layout: {e}")
        return False
    
    # Test 2: Create config with room layout
    try:
        config = DescriptionServiceConfig(
            room_layout_context=room_layout,
            use_room_context=True
        )
        print("✅ Config created with room layout context")
        
        # Verify enhanced prompt includes room layout
        enhanced_prompt = config.get_enhanced_prompt()
        if "ROOM LAYOUT REFERENCE:" in enhanced_prompt:
            print("✅ Enhanced prompt includes room layout reference")
        else:
            print("❌ Enhanced prompt missing room layout reference")
            return False
            
    except Exception as e:
        print(f"❌ Error creating config: {e}")
        return False
    
    # Test 3: Create DescriptionResult with room layout
    try:
        result = DescriptionResult(
            description="Currently: Testing room layout integration. Present: Developer at computer. Location details: Working at right counter near sink area.",
            confidence=0.9,
            timestamp=datetime.now(),
            processing_time_ms=100,
            cached=False,
            room_layout=room_layout
        )
        
        print("✅ DescriptionResult created with room layout")
        print(f"   Room layout included: {'Yes' if result.room_layout else 'No'}")
        print(f"   Room layout size: {len(result.room_layout) if result.room_layout else 0} chars")
        
    except Exception as e:
        print(f"❌ Error creating DescriptionResult: {e}")
        return False
    
    # Test 4: Verify serialization includes room layout
    try:
        result_dict = result.to_dict()
        if 'room_layout' in result_dict and result_dict['room_layout']:
            print("✅ Serialization includes room layout")
        else:
            print("❌ Serialization missing room layout")
            return False
            
    except Exception as e:
        print(f"❌ Error in serialization: {e}")
        return False
    
    # Test 5: Show AI integration example
    print("\n🤖 AI Integration Example:")
    print("=" * 25)
    
    # Simulate how a conversational AI would use this
    if result.success:
        context = f"Room status: {result.description}"
        if result.room_layout:
            context += f"\n\nRoom layout:\n{result.room_layout[:200]}..."
            
        print("Context sent to AI:")
        print("-" * 20)
        print(context)
        print("-" * 20)
        print("✅ AI now has both current scene AND room layout context!")
    
    print("\n🎉 All tests passed! Room layout integration working correctly.")
    return True

if __name__ == "__main__":
    success = test_room_layout_integration()
    if not success:
        sys.exit(1) 