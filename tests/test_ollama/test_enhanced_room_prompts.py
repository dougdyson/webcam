"""
Tests for enhanced room prompting system.

This module tests the enhanced prompting capabilities we added for room-aware
conversational AI integration, including:
- General-purpose room context (not kitchen-specific)
- Room layout integration with color references
- Enhanced prompt generation for any room type
- Backward compatibility with existing system
"""
import pytest
import numpy as np
from datetime import datetime
from unittest.mock import Mock, patch

try:
    from src.ollama.description_service import (
        DescriptionService,
        DescriptionServiceConfig,
        DescriptionResult
    )
    from src.ollama.client import OllamaClient
    from src.ollama.snapshot_buffer import Snapshot, SnapshotMetadata
    from src.ollama.image_processing import OllamaImageProcessor
except ImportError:
    # Skip tests if modules not available
    DescriptionService = None
    DescriptionServiceConfig = None
    DescriptionResult = None


class TestEnhancedRoomPrompts:
    """Test enhanced room prompting system."""
    
    def test_config_has_room_context_parameters(self):
        """Should have room context parameters in configuration."""
        if DescriptionServiceConfig is None:
            pytest.skip("DescriptionServiceConfig not available")
        
        config = DescriptionServiceConfig()
        
        # Should have room context fields
        assert hasattr(config, 'room_layout_context')
        assert hasattr(config, 'use_room_context')
        assert hasattr(config, 'default_prompt')
        
        # Should have reasonable defaults
        assert config.room_layout_context == ""
        assert config.use_room_context is True
        assert len(config.default_prompt) > 0
    
    def test_config_room_context_customization(self):
        """Should allow customization of room context."""
        if DescriptionServiceConfig is None:
            pytest.skip("DescriptionServiceConfig not available")
        
        room_layout = """Living Room Layout:
- Couch: Large gray sectional sofa against west wall
- Coffee Table: Dark wood rectangular table in center
- TV: 65" mounted on east wall
- Windows: Two large windows on north wall with white curtains"""
        
        config = DescriptionServiceConfig(
            room_layout_context=room_layout,
            use_room_context=True
        )
        
        assert config.room_layout_context == room_layout
        assert config.use_room_context is True
    
    def test_get_enhanced_prompt_without_room_context(self):
        """Should return default prompt when room context disabled."""
        if DescriptionServiceConfig is None:
            pytest.skip("DescriptionServiceConfig not available")
        
        config = DescriptionServiceConfig(
            use_room_context=False,
            default_prompt="Simple description please."
        )
        
        prompt = config.get_enhanced_prompt()
        assert prompt == "Simple description please."
    
    def test_get_enhanced_prompt_with_basic_room_context(self):
        """Should generate enhanced prompt with room context."""
        if DescriptionServiceConfig is None:
            pytest.skip("DescriptionServiceConfig not available")
        
        config = DescriptionServiceConfig(
            use_room_context=True,
            room_layout_context=""
        )
        
        prompt = config.get_enhanced_prompt()
        
        # Should contain key prompting elements
        assert "PEOPLE & ACTIVITIES" in prompt
        assert "OBJECTS & ITEMS" in prompt  
        assert "SPATIAL CONTEXT" in prompt
        assert "Currently:" in prompt
        assert "Present:" in prompt
        assert "Location details:" in prompt
        
        # Should warn against color detection
        assert "Do NOT attempt to identify colors" in prompt
        assert "colors are unreliable" in prompt
    
    def test_get_enhanced_prompt_with_room_layout_context(self):
        """Should include room layout reference in prompt."""
        if DescriptionServiceConfig is None:
            pytest.skip("DescriptionServiceConfig not available")
        
        room_layout = """Office Layout:
FURNITURE:
- Desk: Large white standing desk against north wall
- Chair: Black ergonomic office chair  
- Bookshelf: Tall wooden bookshelf on east wall with technical books

COLOR REFERENCE FOR IDENTIFICATION:
- Desk surface: White/cream color
- Chair: Black leather/fabric
- Bookshelf: Natural wood brown color
- Walls: Light gray paint"""
        
        config = DescriptionServiceConfig(
            use_room_context=True,
            room_layout_context=room_layout
        )
        
        prompt = config.get_enhanced_prompt()
        
        # Should include the room layout
        assert "ROOM LAYOUT REFERENCE:" in prompt
        assert "Office Layout:" in prompt
        assert "COLOR REFERENCE FOR IDENTIFICATION:" in prompt
        assert "White/cream color" in prompt
        assert "Black leather/fabric" in prompt
        
        # Should still have prompting instructions
        assert "PEOPLE & ACTIVITIES" in prompt
        assert "use the room layout reference above" in prompt
    
    def test_enhanced_prompt_focuses_on_conversation_context(self):
        """Should focus on conversational AI context rather than generic description."""
        if DescriptionServiceConfig is None:
            pytest.skip("DescriptionServiceConfig not available")
        
        config = DescriptionServiceConfig(use_room_context=True)
        prompt = config.get_enhanced_prompt()
        
        # Should focus on conversational elements
        assert "how they might be feeling" in prompt
        assert "happy, sad, angry, concerned, peaceful" in prompt
        assert "clothes, hair, eyes, shave" in prompt
        assert "useful context for a conversation" in prompt
        
        # Should be structured for AI parsing
        assert "Format your response as:" in prompt
        assert "[brief activity description]" in prompt
        assert "[people/objects]" in prompt
        assert "[spatial info]" in prompt


class TestRoomLayoutIntegration:
    """Test room layout integration in description results."""
    
    def test_description_result_includes_room_layout(self):
        """Should include room layout in description results."""
        if DescriptionResult is None:
            pytest.skip("DescriptionResult not available")
        
        room_layout = "Living room with couch and TV"
        
        result = DescriptionResult(
            description="Person sitting on couch watching TV",
            confidence=0.85,
            timestamp=datetime.now(),
            processing_time_ms=150,
            room_layout=room_layout
        )
        
        assert result.room_layout == room_layout
    
    def test_description_result_to_dict_includes_room_layout(self):
        """Should include room layout in dictionary serialization."""
        if DescriptionResult is None:
            pytest.skip("DescriptionResult not available")
        
        room_layout = "Kitchen with island and appliances"
        
        result = DescriptionResult(
            description="Person cooking at stove",
            confidence=0.92,
            timestamp=datetime.now(),
            processing_time_ms=200,
            cached=False,
            room_layout=room_layout
        )
        
        data = result.to_dict()
        
        assert 'room_layout' in data
        assert data['room_layout'] == room_layout
        assert data['description'] == "Person cooking at stove"
        assert data['confidence'] == 0.92
    
    @pytest.mark.asyncio
    async def test_description_service_includes_room_layout_in_results(self):
        """Should include room layout in all description service results."""
        if DescriptionService is None:
            pytest.skip("DescriptionService not available")
        
        room_layout = """Home Office:
- Desk with computer setup
- Ergonomic chair  
- Bookshelves with reference materials"""
        
        config = DescriptionServiceConfig(
            room_layout_context=room_layout,
            use_room_context=True
        )
        
        # Mock dependencies
        mock_ollama_client = Mock(spec=OllamaClient)
        mock_ollama_client.describe_image.return_value = "Person working at computer"
        
        mock_image_processor = Mock(spec=OllamaImageProcessor)
        mock_image_processor.process_webcam_frame.return_value = "base64_image"
        
        service = DescriptionService(
            ollama_client=mock_ollama_client,
            image_processor=mock_image_processor,
            config=config
        )
        
        # Create test snapshot
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        metadata = SnapshotMetadata(
            timestamp=datetime.now(),
            confidence=0.9,
            human_present=True,
            detection_source="test"
        )
        snapshot = Snapshot(frame=frame, metadata=metadata)
        
        # Process snapshot
        result = await service.describe_snapshot(snapshot)
        
        # Should include room layout
        assert result.room_layout == room_layout
        assert result.description == "Person working at computer"
        
        # Should also be in serialized form
        data = result.to_dict()
        assert data['room_layout'] == room_layout
    
    @pytest.mark.asyncio 
    async def test_description_service_room_layout_in_error_cases(self):
        """Should include room layout even in error cases."""
        if DescriptionService is None:
            pytest.skip("DescriptionService not available")
        
        room_layout = "Test room layout"
        
        config = DescriptionServiceConfig(
            room_layout_context=room_layout,
            enable_fallback_descriptions=True
        )
        
        # Mock dependencies to simulate error
        mock_ollama_client = Mock(spec=OllamaClient)
        mock_ollama_client.describe_image.side_effect = Exception("Service error")
        
        mock_image_processor = Mock(spec=OllamaImageProcessor)
        mock_image_processor.process_webcam_frame.return_value = "base64_image"
        
        service = DescriptionService(
            ollama_client=mock_ollama_client,
            image_processor=mock_image_processor,
            config=config
        )
        
        # Create test snapshot
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        metadata = SnapshotMetadata(
            timestamp=datetime.now(),
            confidence=0.9,
            human_present=True,
            detection_source="test"
        )
        snapshot = Snapshot(frame=frame, metadata=metadata)
        
        # Process snapshot (should handle error gracefully)
        result = await service.describe_snapshot(snapshot)
        
        # Should still include room layout even in error case
        assert result.room_layout == room_layout
        assert result.error is not None
        assert "Error:" in result.description or "description temporarily unavailable" in result.description.lower()


class TestBackwardCompatibility:
    """Test backward compatibility with existing system."""
    
    def test_config_defaults_maintain_compatibility(self):
        """Should maintain backward compatibility with existing configurations."""
        if DescriptionServiceConfig is None:
            pytest.skip("DescriptionServiceConfig not available")
        
        # Default config should work like before
        config = DescriptionServiceConfig()
        
        # Original config fields should still exist
        assert hasattr(config, 'cache_ttl_seconds')
        assert hasattr(config, 'max_concurrent_requests')  
        assert hasattr(config, 'timeout_seconds')
        assert hasattr(config, 'enable_caching')
        
        # Should have reasonable defaults
        assert config.cache_ttl_seconds == 300
        assert config.max_concurrent_requests == 3
        assert config.timeout_seconds == 30.0
        assert config.enable_caching is True
    
    def test_service_works_without_room_context(self):
        """Should work normally when room context is disabled."""
        if DescriptionServiceConfig is None:
            pytest.skip("DescriptionServiceConfig not available")
        
        config = DescriptionServiceConfig(
            use_room_context=False,
            default_prompt="Describe this image briefly."
        )
        
        prompt = config.get_enhanced_prompt()
        assert prompt == "Describe this image briefly."
        
        # Should not contain room-specific content
        assert "ROOM LAYOUT REFERENCE" not in prompt
        assert "PEOPLE & ACTIVITIES" not in prompt
    
    @pytest.mark.asyncio
    async def test_service_processes_snapshots_normally_without_room_context(self):
        """Should process snapshots normally when room features disabled."""
        if DescriptionService is None:
            pytest.skip("DescriptionService not available")
        
        config = DescriptionServiceConfig(
            use_room_context=False,
            room_layout_context="",
            default_prompt="Simple description"
        )
        
        # Mock dependencies
        mock_ollama_client = Mock(spec=OllamaClient)
        mock_ollama_client.describe_image.return_value = "Simple scene description"
        
        mock_image_processor = Mock(spec=OllamaImageProcessor)
        mock_image_processor.process_webcam_frame.return_value = "base64_image"
        
        service = DescriptionService(
            ollama_client=mock_ollama_client,
            image_processor=mock_image_processor,
            config=config
        )
        
        # Create test snapshot
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        metadata = SnapshotMetadata(
            timestamp=datetime.now(),
            confidence=0.9,
            human_present=True,
            detection_source="test"
        )
        snapshot = Snapshot(frame=frame, metadata=metadata)
        
        # Process snapshot
        result = await service.describe_snapshot(snapshot)
        
        # Should work normally
        assert result.description == "Simple scene description"
        assert result.error is None
        
        # Room layout should be empty but present
        assert result.room_layout == ""


class TestGeneralPurposeRoomSupport:
    """Test that the system works for any room type, not just kitchens."""
    
    def test_living_room_context(self):
        """Should work well with living room layout."""
        if DescriptionServiceConfig is None:
            pytest.skip("DescriptionServiceConfig not available")
        
        living_room_layout = """Living Room Layout:
FURNITURE:
- Sectional Sofa: Large gray L-shaped couch against west and south walls
- Coffee Table: Glass rectangular table in center of seating area
- TV Stand: Black wooden entertainment center against east wall
- Side Tables: Two matching wooden end tables beside couch

COLOR REFERENCE FOR IDENTIFICATION:
- Sofa: Gray fabric upholstery  
- Coffee table: Clear glass surface with silver metal legs
- TV stand: Dark brown/black wood finish
- Walls: Cream/beige paint color"""
        
        config = DescriptionServiceConfig(
            room_layout_context=living_room_layout,
            use_room_context=True
        )
        
        prompt = config.get_enhanced_prompt()
        
        assert "Living Room Layout:" in prompt
        assert "Sectional Sofa" in prompt
        assert "Gray fabric upholstery" in prompt
        assert "COLOR REFERENCE FOR IDENTIFICATION:" in prompt
    
    def test_bedroom_context(self):
        """Should work well with bedroom layout."""
        if DescriptionServiceConfig is None:
            pytest.skip("DescriptionServiceConfig not available")
        
        bedroom_layout = """Bedroom Layout:
FURNITURE:
- Bed: Queen size bed with white metal frame against north wall
- Dresser: Six-drawer wooden dresser against east wall  
- Nightstands: Two matching wooden tables beside bed
- Wardrobe: Large wooden closet against west wall

COLOR REFERENCE FOR IDENTIFICATION:
- Bed frame: White painted metal
- Dresser: Natural wood finish (oak/pine color)
- Nightstands: Matching natural wood  
- Walls: Light blue paint"""
        
        config = DescriptionServiceConfig(
            room_layout_context=bedroom_layout,
            use_room_context=True
        )
        
        prompt = config.get_enhanced_prompt()
        
        assert "Bedroom Layout:" in prompt
        assert "Queen size bed" in prompt
        assert "Light blue paint" in prompt
        assert "Natural wood finish" in prompt
    
    def test_office_context(self):
        """Should work well with office layout.""" 
        if DescriptionServiceConfig is None:
            pytest.skip("DescriptionServiceConfig not available")
        
        office_layout = """Home Office Layout:
FURNITURE:
- Desk: Large white standing desk against north wall
- Office Chair: Black ergonomic chair with mesh back
- Bookshelf: Tall wooden bookshelf on east wall
- Filing Cabinet: Small gray metal cabinet under window

COLOR REFERENCE FOR IDENTIFICATION:
- Desk surface: White/cream laminate finish
- Chair: Black mesh and fabric
- Bookshelf: Dark wood stain (walnut color)
- Filing cabinet: Gray metal finish"""
        
        config = DescriptionServiceConfig(
            room_layout_context=office_layout,
            use_room_context=True  
        )
        
        prompt = config.get_enhanced_prompt()
        
        assert "Home Office Layout:" in prompt
        assert "standing desk" in prompt
        assert "ergonomic chair" in prompt
        assert "Dark wood stain" in prompt


class TestPromptStructureAndQuality:
    """Test the structure and quality of generated prompts."""
    
    def test_prompt_has_clear_sections(self):
        """Should have clearly organized sections for different aspects."""
        if DescriptionServiceConfig is None:
            pytest.skip("DescriptionServiceConfig not available")
        
        config = DescriptionServiceConfig(use_room_context=True)
        prompt = config.get_enhanced_prompt()
        
        # Should have clear section headers
        sections = [
            "PEOPLE & ACTIVITIES:",
            "OBJECTS & ITEMS:",
            "SPATIAL CONTEXT:",
            "Format your response as:"
        ]
        
        for section in sections:
            assert section in prompt
            
        # Sections should be in logical order
        people_pos = prompt.find("PEOPLE & ACTIVITIES:")
        objects_pos = prompt.find("OBJECTS & ITEMS:")
        spatial_pos = prompt.find("SPATIAL CONTEXT:")
        format_pos = prompt.find("Format your response as:")
        
        assert people_pos < objects_pos < spatial_pos < format_pos
    
    def test_prompt_emphasizes_conversational_context(self):
        """Should emphasize elements useful for conversational AI."""
        if DescriptionServiceConfig is None:
            pytest.skip("DescriptionServiceConfig not available")
        
        config = DescriptionServiceConfig(use_room_context=True)
        prompt = config.get_enhanced_prompt()
        
        # Should focus on conversational elements
        conversational_terms = [
            "feeling",
            "conversation", 
            "activities",
            "how they look",
            "appear physically"
        ]
        
        for term in conversational_terms:
            assert term in prompt.lower()
    
    def test_prompt_provides_clear_output_format(self):
        """Should provide clear formatting instructions for AI responses."""
        if DescriptionServiceConfig is None:
            pytest.skip("DescriptionServiceConfig not available")
        
        config = DescriptionServiceConfig(use_room_context=True)
        prompt = config.get_enhanced_prompt()
        
        # Should specify output format clearly
        assert "Format your response as:" in prompt
        assert "Currently:" in prompt
        assert "Present:" in prompt  
        assert "Location details:" in prompt
        
        # Should provide example format
        assert "[brief activity description]" in prompt
        assert "[people/objects]" in prompt
        assert "[spatial info]" in prompt 