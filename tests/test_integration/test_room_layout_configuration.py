"""
Tests for room layout configuration loading and integration.

This module tests the configuration loading mechanisms for room layout
context, including file loading, service integration, and end-to-end
functionality with the webcam service.
"""
import pytest
import tempfile
import os
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

try:
    from src.ollama.description_service import DescriptionServiceConfig, DescriptionService
    from src.service.http_service import HTTPDetectionService, HTTPServiceConfig
    DEPENDENCIES_AVAILABLE = True
except ImportError:
    DescriptionServiceConfig = None
    DescriptionService = None
    HTTPDetectionService = None
    HTTPServiceConfig = None
    DEPENDENCIES_AVAILABLE = False


@pytest.mark.skip(reason="Room layout feature is currently commented out in implementation")
class TestRoomLayoutFileLoading:
    """Test loading room layout from configuration files."""
    
    def test_load_room_layout_from_file(self):
        """Should load room layout context from file."""
        if not DEPENDENCIES_AVAILABLE:
            pytest.skip("Dependencies not available")
        
        # Create temporary room layout file
        room_layout_content = """Home Office Layout:
FURNITURE:
- Desk: Large white standing desk against north wall
- Chair: Black ergonomic office chair
- Bookshelf: Tall wooden bookshelf on east wall

COLOR REFERENCE FOR IDENTIFICATION:
- Desk: White/cream laminate surface
- Chair: Black mesh and fabric
- Bookshelf: Dark walnut wood stain"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(room_layout_content)
            temp_file_path = f.name
        
        try:
            # Test loading into configuration
            with open(temp_file_path, 'r') as f:
                loaded_content = f.read()
            
            config = DescriptionServiceConfig(
                room_layout_context=loaded_content,
                use_room_context=True
            )
            
            assert config.room_layout_context == room_layout_content
            assert "Home Office Layout:" in config.room_layout_context
            assert "COLOR REFERENCE" in config.room_layout_context
            
        finally:
            os.unlink(temp_file_path)
    
    def test_handle_missing_room_layout_file(self):
        """Should handle missing room layout file gracefully."""
        if not DEPENDENCIES_AVAILABLE:
            pytest.skip("Dependencies not available")
        
        # Test with empty/missing content
        config = DescriptionServiceConfig(
            room_layout_context="",
            use_room_context=True
        )
        
        prompt = config.get_enhanced_prompt()
        
        # Should still work without room layout
        assert "PEOPLE & ACTIVITIES" in prompt
        assert "OBJECTS & ITEMS" in prompt
        # Should not include room layout section
        assert "ROOM LAYOUT REFERENCE:" not in prompt
    
    def test_handle_invalid_room_layout_content(self):
        """Should handle invalid or malformed room layout content."""
        if not DEPENDENCIES_AVAILABLE:
            pytest.skip("Dependencies not available")
        
        # Test with various edge cases
        edge_cases = [
            "",  # Empty
            " \n\t ",  # Whitespace only
            "Room\nWith\nOnly\nBasic\nText",  # Basic text
            None,  # None value (should be handled)
        ]
        
        for test_content in edge_cases:
            if test_content is None:
                config = DescriptionServiceConfig(use_room_context=True)
            else:
                config = DescriptionServiceConfig(
                    room_layout_context=test_content,
                    use_room_context=True
                )
            
            # Should not crash when generating prompt
            prompt = config.get_enhanced_prompt()
            assert isinstance(prompt, str)
            assert len(prompt) > 0


@pytest.mark.skip(reason="Room layout feature is currently commented out in implementation")
class TestWebcamServiceRoomLayoutIntegration:
    """Test integration of room layout with webcam service."""
    
    def test_webcam_service_loads_room_layout_on_startup(self):
        """Should load room layout configuration during service startup."""
        if not DEPENDENCIES_AVAILABLE:
            pytest.skip("Dependencies not available")
        
        # Create mock room layout file content
        room_layout_content = """Living Room Layout:
- Sofa: Gray sectional against west wall
- TV: 65" mounted on east wall
- Coffee table: Glass rectangular table in center"""
        
        # Mock file loading
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = room_layout_content
            
            # Mock the service components
            with patch('src.ollama.description_service.DescriptionService') as mock_desc_service, \
                 patch('src.service.http_service.HTTPDetectionService') as mock_http_service:
                
                # Simulate service initialization that loads room layout
                mock_config = DescriptionServiceConfig(
                    room_layout_context=room_layout_content,
                    use_room_context=True
                )
                
                # Verify configuration contains room layout
                assert mock_config.room_layout_context == room_layout_content
                assert "Living Room Layout:" in mock_config.room_layout_context
    
    @patch('os.path.exists')
    def test_webcam_service_handles_missing_room_layout_file(self, mock_exists):
        """Should handle missing room layout file gracefully."""
        if not DEPENDENCIES_AVAILABLE:
            pytest.skip("Dependencies not available")
        
        # Simulate missing file
        mock_exists.return_value = False
        
        # Should create default configuration
        config = DescriptionServiceConfig(
            room_layout_context="",  # Empty when file missing
            use_room_context=True
        )
        
        # Should still function normally
        prompt = config.get_enhanced_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "PEOPLE & ACTIVITIES" in prompt
    
    def test_service_configuration_validation(self):
        """Should validate room layout configuration parameters."""
        if not DEPENDENCIES_AVAILABLE:
            pytest.skip("Dependencies not available")
        
        # Test valid configurations
        valid_configs = [
            {"room_layout_context": "", "use_room_context": False},
            {"room_layout_context": "Simple room", "use_room_context": True},
            {"room_layout_context": "Multi\nLine\nRoom", "use_room_context": True},
        ]
        
        for config_params in valid_configs:
            config = DescriptionServiceConfig(**config_params)
            # Should not raise any exceptions
            prompt = config.get_enhanced_prompt()
            assert isinstance(prompt, str)


@pytest.mark.skip(reason="Room layout feature is currently commented out in implementation")
class TestEndToEndRoomLayoutIntegration:
    """Test end-to-end room layout integration across all components."""
    
    def test_full_integration_pipeline(self):
        """Should work end-to-end from file loading to API response."""
        if not DEPENDENCIES_AVAILABLE:
            pytest.skip("Dependencies not available")
        
        # Room layout content
        room_layout_content = """Kitchen Layout:
APPLIANCES:
- Refrigerator: Large stainless steel fridge against north wall
- Stove: Gas range with 4 burners against east wall
- Dishwasher: Built-in dishwasher next to sink
- Microwave: Over-range microwave above stove

SURFACES:
- Island: Large granite-topped island in center with bar seating
- Counters: Granite countertops along walls with backsplash
- Sink: Double basin stainless steel sink under window

COLOR REFERENCE FOR IDENTIFICATION:
- Appliances: Stainless steel finish
- Countertops: Dark granite with white veining
- Cabinets: White painted wood with brushed nickel hardware
- Island: Same white cabinets with dark granite top"""
        
        # Create configuration with room layout
        config = DescriptionServiceConfig(
            room_layout_context=room_layout_content,
            use_room_context=True,
            cache_ttl_seconds=300
        )
        
        # Mock dependencies for description service
        mock_ollama_client = Mock()
        mock_ollama_client.describe_image.return_value = "Person cooking at stove, wearing apron"
        mock_ollama_client.is_available.return_value = True
        
        mock_image_processor = Mock()
        mock_image_processor.process_webcam_frame.return_value = "base64_image_data"
        
        # Create description service
        desc_service = DescriptionService(
            ollama_client=mock_ollama_client,
            image_processor=mock_image_processor,
            config=config
        )
        
        # Create HTTP service and integrate description service
        http_config = HTTPServiceConfig(port=8767)
        http_service = HTTPDetectionService(http_config)
        http_service.setup_description_integration(desc_service)
        
        # Simulate processing (normally would come from webcam)
        import numpy as np
        from src.ollama.snapshot_buffer import Snapshot, SnapshotMetadata
        
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        metadata = SnapshotMetadata(
            timestamp=datetime.now(),
            confidence=0.9,
            human_present=True,
            detection_source="test"
        )
        snapshot = Snapshot(frame=frame, metadata=metadata)
        
        # Test full pipeline
        import asyncio
        async def test_pipeline():
            # Process snapshot through description service
            result = await desc_service.describe_snapshot(snapshot)
            
            # Verify room layout is included
            assert result.room_layout == room_layout_content
            assert "Person cooking at stove" in result.description
            assert result.error is None
            
            # Verify latest description includes room layout
            latest = desc_service.get_latest_description()
            assert latest is not None
            assert latest.room_layout == room_layout_content
            
            return result
        
        # Run the test
        result = asyncio.run(test_pipeline())
        
        # Verify configuration was used
        assert config.room_layout_context in result.room_layout
        assert "Kitchen Layout:" in result.room_layout
        assert "COLOR REFERENCE" in result.room_layout
    
    def test_integration_with_multiple_room_types(self):
        """Should work with different room types in configuration."""
        if not DEPENDENCIES_AVAILABLE:
            pytest.skip("Dependencies not available")
        
        room_types = [
            ("Bedroom", "bed", "dresser"),
            ("Office", "desk", "chair"),  
            ("Living Room", "sofa", "television"),
            ("Kitchen", "stove", "refrigerator"),
            ("Bathroom", "sink", "mirror"),
        ]
        
        for room_type, item1, item2 in room_types:
            room_layout = f"""{room_type} Layout:
FURNITURE:
- {item1.title()}: Primary {item1} in the room
- {item2.title()}: Secondary {item2} item

COLOR REFERENCE:
- {item1.title()}: Test color for {item1}
- {item2.title()}: Test color for {item2}"""
            
            config = DescriptionServiceConfig(
                room_layout_context=room_layout,
                use_room_context=True
            )
            
            prompt = config.get_enhanced_prompt()
            
            # Should include room-specific content
            assert f"{room_type} Layout:" in prompt
            assert item1 in prompt.lower()
            assert item2 in prompt.lower()
            assert "COLOR REFERENCE" in prompt
    
    def test_configuration_persistence_across_service_lifecycle(self):
        """Should maintain room layout configuration across service operations."""
        if not DEPENDENCIES_AVAILABLE:
            pytest.skip("Dependencies not available")
        
        original_room_layout = """Test Room Layout:
- Item 1: Test item one
- Item 2: Test item two"""
        
        config = DescriptionServiceConfig(
            room_layout_context=original_room_layout,
            use_room_context=True
        )
        
        # Mock dependencies
        mock_ollama_client = Mock()
        mock_ollama_client.describe_image.return_value = "Test description"
        
        mock_image_processor = Mock()
        mock_image_processor.process_webcam_frame.return_value = "base64_data"
        
        service = DescriptionService(
            ollama_client=mock_ollama_client,
            image_processor=mock_image_processor,
            config=config
        )
        
        # Process multiple snapshots
        import numpy as np
        from src.ollama.snapshot_buffer import Snapshot, SnapshotMetadata
        
        async def test_persistence():
            for i in range(3):
                frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
                metadata = SnapshotMetadata(
                    timestamp=datetime.now(),
                    confidence=0.8 + i * 0.05,
                    human_present=True,
                    detection_source="test"
                )
                snapshot = Snapshot(frame=frame, metadata=metadata)
                
                result = await service.describe_snapshot(snapshot)
                
                # Should maintain room layout across all operations
                assert result.room_layout == original_room_layout
                assert "Test Room Layout:" in result.room_layout
        
        import asyncio
        asyncio.run(test_persistence())


@pytest.mark.skip(reason="Room layout feature is currently commented out in implementation")
class TestRoomLayoutConfigurationErrorHandling:
    """Test error handling in room layout configuration."""
    
    def test_configuration_with_corrupted_room_layout(self):
        """Should handle corrupted or malformed room layout gracefully."""
        if not DEPENDENCIES_AVAILABLE:
            pytest.skip("Dependencies not available")
        
        # Test various corrupted formats
        corrupted_layouts = [
            "Not a proper layout format",
            "Line 1\nLine 2\n\n\nLine 5",  # Extra newlines
            "FURNITURE:\n- Incomplete",
            "💺 Chair with emoji",  # Unicode characters
            "Layout with very very very very very very very very long lines that might cause issues",
        ]
        
        for corrupted_layout in corrupted_layouts:
            config = DescriptionServiceConfig(
                room_layout_context=corrupted_layout,
                use_room_context=True
            )
            
            # Should not crash
            try:
                prompt = config.get_enhanced_prompt()
                assert isinstance(prompt, str)
                assert len(prompt) > 0
            except Exception as e:
                pytest.fail(f"Configuration failed with corrupted layout '{corrupted_layout[:50]}...': {e}")
    
    def test_service_fallback_when_room_layout_unavailable(self):
        """Should fallback gracefully when room layout becomes unavailable."""
        if not DEPENDENCIES_AVAILABLE:
            pytest.skip("Dependencies not available")
        
        # Start with room layout
        config = DescriptionServiceConfig(
            room_layout_context="Original room layout",
            use_room_context=True
        )
        
        # Simulate room layout becoming unavailable
        config.room_layout_context = ""
        config.use_room_context = False
        
        # Should still work
        prompt = config.get_enhanced_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        # Should use default prompt
        assert prompt == config.default_prompt
    
    def test_memory_usage_with_large_room_layouts(self):
        """Should handle large room layout configurations efficiently."""
        if not DEPENDENCIES_AVAILABLE:
            pytest.skip("Dependencies not available")
        
        # Create very large room layout
        large_layout_parts = []
        for i in range(100):
            large_layout_parts.append(f"- Item {i}: Very detailed description of item number {i} in the room")
        
        large_room_layout = f"""Large Room Layout:
FURNITURE:
{chr(10).join(large_layout_parts)}

COLOR REFERENCE:
{chr(10).join([f'- Item {i}: Color description {i}' for i in range(50)])}"""
        
        config = DescriptionServiceConfig(
            room_layout_context=large_room_layout,
            use_room_context=True
        )
        
        # Should handle large layout without issues
        prompt = config.get_enhanced_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 1000  # Should be quite large
        assert "Large Room Layout:" in prompt
        assert "Item 99:" in prompt  # Should include last item 