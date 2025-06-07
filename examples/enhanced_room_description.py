#!/usr/bin/env python3
"""
Enhanced Room Description Example

This example demonstrates how to use the improved description service
with room-specific context and layout information for better, more
consistent descriptions suitable for conversational AI integration.

Works with any room type: kitchen, office, living room, bedroom, etc.

Features demonstrated:
- Room layout context loading (any room type)
- Enhanced prompt configuration with color references
- Structured description output
- Integration with conversational AI systems
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the src directory to the path so we can import the modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ollama.client import OllamaClient, OllamaConfig
from ollama.description_service import DescriptionService, DescriptionServiceConfig
from ollama.image_processing import OllamaImageProcessor
from ollama.snapshot_buffer import Snapshot, SnapshotMetadata
from datetime import datetime
import numpy as np


def load_room_layout(layout_file: str = "config/room_layout.txt") -> str:
    """
    Load room layout configuration from file.
    
    Args:
        layout_file: Path to room layout configuration file
        
    Returns:
        Room layout context string, or empty string if file not found
    """
    try:
        # Get the project root directory
        project_root = Path(__file__).parent.parent
        layout_path = project_root / layout_file
        
        if layout_path.exists():
            with open(layout_path, 'r') as f:
                return f.read().strip()
        else:
            print(f"Warning: Room layout file not found at {layout_path}")
            return ""
    except Exception as e:
        print(f"Error loading room layout: {e}")
        return ""


def create_enhanced_config(room_layout: str) -> DescriptionServiceConfig:
    """
    Create enhanced description service configuration with room context.
    
    Args:
        room_layout: Room layout description text with color references
        
    Returns:
        Configured DescriptionServiceConfig with room context
    """
    config = DescriptionServiceConfig(
        # Enable room-specific context (works for any room type)
        use_room_context=True,
        room_layout_context=room_layout,
        
        # Cache settings for better performance
        cache_ttl_seconds=300,  # 5 minutes
        enable_caching=True,
        
        # Reasonable timeout for vision processing
        timeout_seconds=30.0,
        
        # Error handling for robustness
        enable_fallback_descriptions=True,
        retry_attempts=2
    )
    
    return config


def create_mock_room_snapshot() -> Snapshot:
    """
    Create a mock snapshot for testing purposes.
    In real usage, this would come from your webcam system.
    """
    # Create a simple mock frame (in reality this would be from webcam)
    mock_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    # Add some simple patterns to make it non-empty
    mock_frame[100:200, 200:400] = [128, 128, 128]  # Gray rectangle
    mock_frame[300:350, 100:500] = [64, 64, 64]     # Darker strip
    
    metadata = SnapshotMetadata(
        timestamp=datetime.now(),
        confidence=0.95,
        human_present=True,
        detection_source="mock_camera"
    )
    
    return Snapshot(frame=mock_frame, metadata=metadata)


async def main():
    """
    Main example demonstrating enhanced room description service.
    """
    print("Enhanced Room Description Service Example")
    print("=" * 48)
    
    # Step 1: Load room layout context
    print("1. Loading room layout context...")
    room_layout = load_room_layout()
    if room_layout:
        print("   ✓ Room layout loaded successfully")
        # Extract room type from layout
        room_type = "Unknown"
        for line in room_layout.split('\n'):
            if line.startswith('ROOM TYPE:'):
                room_type = line.split(':', 1)[1].strip()
                break
        print(f"   Room type: {room_type}")
        print(f"   Layout preview: {room_layout[:100]}...")
    else:
        print("   ⚠ No room layout found, using basic configuration")
    
    # Step 2: Create enhanced configuration
    print("\n2. Creating enhanced configuration...")
    config = create_enhanced_config(room_layout)
    
    # Display the enhanced prompt that will be used
    enhanced_prompt = config.get_enhanced_prompt()
    print("   ✓ Enhanced prompt created:")
    print("   " + enhanced_prompt.replace('\n', '\n   ')[:200] + "...")
    
    # Step 3: Set up the description service
    print("\n3. Setting up description service...")
    
    # Create Ollama client
    ollama_config = OllamaConfig(
        model="gemma3:latest",  # or whatever model you prefer
        base_url="http://localhost:11434",
        timeout=30.0
    )
    ollama_client = OllamaClient(ollama_config)
    
    # Check if Ollama is available
    if not ollama_client.is_available():
        print("   ✗ Ollama service is not available")
        print("   Please ensure Ollama is running on localhost:11434")
        return
    
    print("   ✓ Ollama service is available")
    
    # Create image processor and description service
    image_processor = OllamaImageProcessor()
    description_service = DescriptionService(
        ollama_client=ollama_client,
        image_processor=image_processor,
        config=config
    )
    
    print("   ✓ Description service initialized")
    
    # Step 4: Process a sample snapshot
    print("\n4. Processing sample snapshot...")
    
    # Create mock snapshot (in real usage, this comes from your webcam)
    snapshot = create_mock_room_snapshot()
    
    try:
        # Get description with enhanced context
        result = await description_service.describe_snapshot(snapshot)
        
        print("   ✓ Description generated successfully")
        print(f"\n   Description: {result.description}")
        print(f"   Confidence: {result.confidence}")
        print(f"   Processing time: {result.processing_time_ms}ms")
        print(f"   Cached: {result.cached}")
        print(f"   Error: {result.error}")
        print(f"   Room layout available: {'Yes' if result.room_layout else 'No'}")
        
    except Exception as e:
        print(f"   ✗ Error processing snapshot: {e}")
        return
    
    # Step 5: Demonstrate cache performance
    print("\n5. Testing cache performance...")
    
    # Process the same snapshot again to test caching
    try:
        start_time = asyncio.get_event_loop().time()
        cached_result = await description_service.describe_snapshot(snapshot)
        end_time = asyncio.get_event_loop().time()
        
        print(f"   ✓ Cached result retrieved in {(end_time - start_time)*1000:.1f}ms")
        print(f"   Cached: {cached_result.cached}")
        
        # Show cache statistics
        cache_stats = description_service.get_cache_statistics()
        print(f"   Cache hit rate: {cache_stats['hit_rate']:.2%}")
        print(f"   Total cache entries: {cache_stats['total_entries']}")
        
    except Exception as e:
        print(f"   ✗ Error testing cache: {e}")
    
    # Step 6: Integration guidance
    print("\n6. Integration with Conversational AI")
    print("=" * 40)
    print("To integrate with your conversational AI system:")
    print()
    print("A. Use the description as system context:")
    print(f'   system_prompt = f"Current scene: {{latest_description.description}}"')
    print()
    print("B. Include room layout for spatial understanding:")
    print("   if latest_description.room_layout:")
    print('       system_prompt += f"\\n\\nRoom layout:\\n{latest_description.room_layout}"')
    print()
    print("C. The structured format helps with parsing:")
    print("   - 'Currently:' section describes ongoing activities")
    print("   - 'Present:' section lists people and objects")  
    print("   - 'Location details:' provides spatial context with color references")
    print()
    print("D. Update the description every 10-20 seconds:")
    print("   - Use the caching for performance")
    print("   - Only update AI context when description changes significantly")
    print()
    print("E. Color handling:")
    print("   - Colors come from room layout, not unreliable image detection")
    print("   - More consistent and accurate color references")
    print()
    print("F. Example integration code:")
    print("""
   # In your voice assistant loop:
   latest_desc = description_service.get_latest_description()
   if latest_desc and latest_desc.success:
       context = f"Room status: {latest_desc.description}"
       if latest_desc.room_layout:
           context += f"\\n\\nRoom layout: {latest_desc.room_layout}"
       # Add context to your AI conversation
   """)
    
    # Cleanup
    description_service.cleanup()
    print("\n✓ Example completed successfully!")


if __name__ == "__main__":
    asyncio.run(main()) 