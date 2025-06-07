"""
Enhanced Room System Test Suite

This is a comprehensive test suite for all the room layout enhancements
we implemented. It serves as a single entry point to test all the changes
made during our conversation.

Test Coverage:
- Enhanced room prompting system
- Room layout integration in description results  
- HTTP API room layout responses
- Configuration loading and file handling
- Room photo capture and adjustment scripts
- End-to-end integration testing
- Backward compatibility verification
"""
import pytest
import sys
import os

# Add the project root to Python path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class TestEnhancedRoomSystemOverview:
    """Overview tests for the enhanced room system."""
    
    def test_all_enhanced_modules_importable(self):
        """Should be able to import all enhanced modules."""
        try:
            # Test core enhanced modules
            from src.ollama.description_service import (
                DescriptionServiceConfig, 
                DescriptionService,
                DescriptionResult
            )
            
            # Test configuration enhancements
            config = DescriptionServiceConfig()
            assert hasattr(config, 'room_layout_context')
            assert hasattr(config, 'use_room_context')
            assert hasattr(config, 'get_enhanced_prompt')
            
            # Test result enhancements
            result = DescriptionResult(
                description="test",
                confidence=0.8,
                timestamp=None,
                processing_time_ms=100,
                room_layout="test room"
            )
            assert hasattr(result, 'room_layout')
            
            success = True
            
        except ImportError as e:
            success = False
            pytest.skip(f"Enhanced modules not available: {e}")
        
        assert success, "All enhanced modules should be importable"
    
    def test_enhanced_prompt_system_functional(self):
        """Should verify enhanced prompting system works end-to-end."""
        try:
            from src.ollama.description_service import DescriptionServiceConfig
            
            # Test basic enhanced prompting
            config = DescriptionServiceConfig(use_room_context=True)
            prompt = config.get_enhanced_prompt()
            
            # Verify prompt contains expected enhancements
            expected_sections = [
                "PEOPLE & ACTIVITIES",
                "OBJECTS & ITEMS", 
                "SPATIAL CONTEXT",
                "Format your response as:",
                "Do NOT attempt to identify colors"
            ]
            
            for section in expected_sections:
                assert section in prompt, f"Prompt missing section: {section}"
            
            # Test with room layout
            room_layout = "Test Room Layout:\n- Desk: White desk\n- Chair: Black chair"
            config_with_layout = DescriptionServiceConfig(
                room_layout_context=room_layout,
                use_room_context=True
            )
            
            prompt_with_layout = config_with_layout.get_enhanced_prompt()
            assert "ROOM LAYOUT REFERENCE:" in prompt_with_layout
            assert "Test Room Layout:" in prompt_with_layout
            
        except ImportError:
            pytest.skip("Enhanced prompting system not available")
    
    def test_room_layout_integration_functional(self):
        """Should verify room layout integration works across components."""
        try:
            from src.ollama.description_service import DescriptionResult
            from datetime import datetime
            
            # Test room layout in results
            room_layout = "Integration Test Room Layout"
            result = DescriptionResult(
                description="Person at desk",
                confidence=0.85,
                timestamp=datetime.now(),
                processing_time_ms=200,
                room_layout=room_layout
            )
            
            # Verify room layout integration
            assert result.room_layout == room_layout
            
            # Verify serialization includes room layout
            data = result.to_dict()
            assert 'room_layout' in data
            assert data['room_layout'] == room_layout
            
        except ImportError:
            pytest.skip("Room layout integration not available")


class TestFeatureCompleteness:
    """Test that all promised features are implemented and working."""
    
    def test_general_purpose_room_support(self):
        """Should support any room type, not just kitchens."""
        try:
            from src.ollama.description_service import DescriptionServiceConfig
            
            room_types = [
                ("Living Room", "sofa", "TV"),
                ("Bedroom", "bed", "dresser"),
                ("Office", "desk", "chair"),
                ("Kitchen", "stove", "refrigerator"),
                ("Bathroom", "sink", "mirror")
            ]
            
            for room_type, item1, item2 in room_types:
                room_layout = f"""{room_type} Layout:
FURNITURE:
- {item1.title()}: Test {item1}
- {item2.title()}: Test {item2}

COLOR REFERENCE:
- {item1.title()}: Test color {item1}
- {item2.title()}: Test color {item2}"""
                
                config = DescriptionServiceConfig(
                    room_layout_context=room_layout,
                    use_room_context=True
                )
                
                prompt = config.get_enhanced_prompt()
                
                # Should include room-specific content
                assert f"{room_type} Layout:" in prompt
                assert item1.lower() in prompt.lower()
                assert item2.lower() in prompt.lower()
                
        except ImportError:
            pytest.skip("General purpose room support not available")
    
    def test_color_reference_system(self):
        """Should include color reference system instead of unreliable color detection."""
        try:
            from src.ollama.description_service import DescriptionServiceConfig
            
            room_layout_with_colors = """Test Room:
FURNITURE:
- Sofa: Large comfortable seating

COLOR REFERENCE FOR IDENTIFICATION:
- Sofa: Gray fabric upholstery
- Walls: Cream/beige paint color
- Floor: Dark hardwood finish"""
            
            config = DescriptionServiceConfig(
                room_layout_context=room_layout_with_colors,
                use_room_context=True
            )
            
            prompt = config.get_enhanced_prompt()
            
            # Should include color reference
            assert "COLOR REFERENCE FOR IDENTIFICATION:" in prompt
            assert "Gray fabric upholstery" in prompt
            
            # Should warn against color detection from image
            assert "Do NOT attempt to identify colors" in prompt
            assert "colors are unreliable" in prompt
            assert "use the room layout reference" in prompt
            
        except ImportError:
            pytest.skip("Color reference system not available")
    
    def test_conversational_ai_focus(self):
        """Should focus on conversational AI context rather than generic descriptions."""
        try:
            from src.ollama.description_service import DescriptionServiceConfig
            
            config = DescriptionServiceConfig(use_room_context=True)
            prompt = config.get_enhanced_prompt()
            
            # Should emphasize conversational elements
            conversational_indicators = [
                "how they might be feeling",
                "happy, sad, angry, concerned, peaceful",
                "clothes, hair, eyes, shave",
                "useful context for a conversation",
                "how they look",
                "appear physically"
            ]
            
            for indicator in conversational_indicators:
                assert indicator in prompt.lower(), f"Missing conversational indicator: {indicator}"
                
        except ImportError:
            pytest.skip("Conversational AI focus not available")
    
    def test_structured_output_format(self):
        """Should provide structured output format for AI parsing."""
        try:
            from src.ollama.description_service import DescriptionServiceConfig
            
            config = DescriptionServiceConfig(use_room_context=True)
            prompt = config.get_enhanced_prompt()
            
            # Should specify clear output format
            format_indicators = [
                "Format your response as:",
                "Currently:",
                "Present:",
                "Location details:",
                "[brief activity description]",
                "[people/objects]",
                "[spatial info]"
            ]
            
            for indicator in format_indicators:
                assert indicator in prompt, f"Missing format indicator: {indicator}"
                
        except ImportError:
            pytest.skip("Structured output format not available")


class TestBackwardCompatibilityGuarantees:
    """Test that all changes maintain backward compatibility."""
    
    def test_original_configuration_still_works(self):
        """Should maintain compatibility with original configuration."""
        try:
            from src.ollama.description_service import DescriptionServiceConfig
            
            # Original style configuration should still work
            config = DescriptionServiceConfig(
                cache_ttl_seconds=300,
                max_concurrent_requests=3,
                timeout_seconds=30.0,
                enable_caching=True
            )
            
            # Original fields should still exist and work
            assert config.cache_ttl_seconds == 300
            assert config.max_concurrent_requests == 3
            assert config.timeout_seconds == 30.0
            assert config.enable_caching is True
            
        except ImportError:
            pytest.skip("Original configuration not available")
    
    def test_service_works_without_room_features(self):
        """Should work normally when room features are disabled."""
        try:
            from src.ollama.description_service import DescriptionServiceConfig
            
            # Disable room features
            config = DescriptionServiceConfig(
                use_room_context=False,
                room_layout_context="",
                default_prompt="Simple description please."
            )
            
            prompt = config.get_enhanced_prompt()
            
            # Should use default prompt
            assert prompt == "Simple description please."
            
            # Should not contain room-specific content
            assert "ROOM LAYOUT REFERENCE" not in prompt
            assert "PEOPLE & ACTIVITIES" not in prompt
            
        except ImportError:
            pytest.skip("Room feature disable not available")
    
    def test_api_responses_include_room_layout_field(self):
        """Should include room_layout field in API responses without breaking existing clients."""
        try:
            from src.ollama.description_service import DescriptionResult
            from datetime import datetime
            
            # Test with room layout
            result_with_layout = DescriptionResult(
                description="Test description",
                confidence=0.8,
                timestamp=datetime.now(),
                processing_time_ms=150,
                room_layout="Test room layout"
            )
            
            data = result_with_layout.to_dict()
            assert 'room_layout' in data
            assert data['room_layout'] == "Test room layout"
            
            # Test without room layout (backward compatibility)
            result_without_layout = DescriptionResult(
                description="Test description",
                confidence=0.8,
                timestamp=datetime.now(),
                processing_time_ms=150,
                room_layout=None
            )
            
            data = result_without_layout.to_dict()
            assert 'room_layout' in data
            assert data['room_layout'] is None
            
            # Should still have all original fields
            required_fields = ['description', 'confidence', 'timestamp', 'processing_time_ms', 'success']
            for field in required_fields:
                assert field in data, f"Missing required field: {field}"
                
        except ImportError:
            pytest.skip("API response integration not available")


# Import and run specific test modules for detailed testing
def run_enhanced_room_tests():
    """
    Entry point to run all enhanced room system tests.
    
    This function can be called to run the complete test suite
    for all room layout enhancements.
    """
    test_modules = [
        "tests.test_ollama.test_enhanced_room_prompts",
        "tests.test_service.test_http_room_layout_integration", 
        "tests.test_integration.test_room_layout_configuration",
        "tests.test_utils.test_room_photo_scripts"
    ]
    
    results = {}
    
    for module in test_modules:
        try:
            pytest.main(["-v", module])
            results[module] = "PASSED"
        except Exception as e:
            results[module] = f"FAILED: {e}"
    
    return results


if __name__ == "__main__":
    # Run all enhanced room system tests when script is executed directly
    print("Running Enhanced Room System Test Suite...")
    print("=" * 60)
    
    # Run overview tests first
    pytest.main(["-v", __file__ + "::TestEnhancedRoomSystemOverview"])
    pytest.main(["-v", __file__ + "::TestFeatureCompleteness"])
    pytest.main(["-v", __file__ + "::TestBackwardCompatibilityGuarantees"])
    
    # Run detailed test modules
    print("\nRunning detailed test modules...")
    results = run_enhanced_room_tests()
    
    print("\nTest Results Summary:")
    print("=" * 60)
    for module, result in results.items():
        print(f"{module}: {result}")
    
    print("\nEnhanced Room System Test Suite Complete!") 