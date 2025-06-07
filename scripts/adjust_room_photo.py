#!/usr/bin/env python3
"""
Adjust Room Photo Brightness and Exposure

This script processes the captured room photo to reduce brightness,
adjust contrast, and improve exposure for better analysis by vision models.

Usage:
    python scripts/adjust_room_photo.py input_image.jpg [output_image.jpg]
"""

import cv2
import numpy as np
import sys
import os
from pathlib import Path

def adjust_brightness_contrast(image, brightness=-50, contrast=1.2):
    """
    Adjust brightness and contrast of an image.
    
    Args:
        image: Input image
        brightness: Brightness adjustment (-100 to 100, negative = darker)
        contrast: Contrast multiplier (0.5 = less contrast, 2.0 = more contrast)
        
    Returns:
        Adjusted image
    """
    # Convert brightness to the range used by OpenCV
    beta = brightness
    alpha = contrast
    
    # Apply the formula: new_image = alpha * old_image + beta
    adjusted = cv2.convertScaleAbs(image, alpha=alpha, beta=beta)
    return adjusted

def reduce_exposure(image, gamma=0.7):
    """
    Reduce exposure using gamma correction.
    
    Args:
        image: Input image
        gamma: Gamma value (< 1.0 = darker, > 1.0 = brighter)
        
    Returns:
        Gamma-corrected image
    """
    # Build a lookup table mapping pixel values [0, 255] to their adjusted gamma values
    inv_gamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
    
    # Apply gamma correction using the lookup table
    return cv2.LUT(image, table)

def enhance_shadows_highlights(image):
    """
    Enhance shadows while reducing highlights.
    
    Args:
        image: Input image
        
    Returns:
        Enhanced image
    """
    # Convert to LAB color space for better luminance control
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    
    # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization) to luminance
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    
    # Merge channels and convert back to BGR
    enhanced = cv2.merge([l, a, b])
    enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
    
    return enhanced

def auto_white_balance(image):
    """
    Apply simple white balance correction.
    
    Args:
        image: Input image
        
    Returns:
        White-balanced image
    """
    # Calculate the mean for each channel
    b_mean = np.mean(image[:, :, 0])
    g_mean = np.mean(image[:, :, 1])
    r_mean = np.mean(image[:, :, 2])
    
    # Calculate the overall mean
    overall_mean = (b_mean + g_mean + r_mean) / 3
    
    # Calculate scaling factors
    b_scale = overall_mean / b_mean if b_mean > 0 else 1
    g_scale = overall_mean / g_mean if g_mean > 0 else 1
    r_scale = overall_mean / r_mean if r_mean > 0 else 1
    
    # Apply scaling (but limit to reasonable range)
    b_scale = np.clip(b_scale, 0.5, 2.0)
    g_scale = np.clip(g_scale, 0.5, 2.0)
    r_scale = np.clip(r_scale, 0.5, 2.0)
    
    # Split channels
    b, g, r = cv2.split(image)
    
    # Apply scaling
    b = cv2.convertScaleAbs(b, alpha=b_scale)
    g = cv2.convertScaleAbs(g, alpha=g_scale)
    r = cv2.convertScaleAbs(r, alpha=r_scale)
    
    # Merge back
    balanced = cv2.merge([b, g, r])
    
    return balanced

def process_image(input_path, output_path, preset="balanced"):
    """
    Process the image with different adjustment presets.
    
    Args:
        input_path: Path to input image
        output_path: Path to save adjusted image
        preset: Adjustment preset ('gentle', 'balanced', 'strong')
        
    Returns:
        bool: Success status
    """
    print(f"🔧 Processing image: {input_path}")
    print(f"📐 Using preset: {preset}")
    
    # Read the image
    image = cv2.imread(input_path)
    if image is None:
        print(f"❌ Error: Could not read image from {input_path}")
        return False
    
    original_height, original_width = image.shape[:2]
    print(f"📏 Original size: {original_width}x{original_height}")
    
    # Apply adjustments based on preset
    if preset == "gentle":
        # Gentle adjustments
        processed = adjust_brightness_contrast(image, brightness=-30, contrast=1.1)
        processed = reduce_exposure(processed, gamma=0.8)
    elif preset == "balanced":
        # Balanced adjustments (good for overexposed images)
        processed = adjust_brightness_contrast(image, brightness=-50, contrast=1.2)
        processed = reduce_exposure(processed, gamma=0.7)
        processed = auto_white_balance(processed)
    elif preset == "strong":
        # Strong adjustments for very overexposed images
        processed = adjust_brightness_contrast(image, brightness=-70, contrast=1.3)
        processed = reduce_exposure(processed, gamma=0.6)
        processed = enhance_shadows_highlights(processed)
        processed = auto_white_balance(processed)
    else:
        print(f"❌ Unknown preset: {preset}")
        return False
    
    # Save the processed image
    success = cv2.imwrite(output_path, processed)
    
    if success:
        file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
        print(f"✅ Processed image saved!")
        print(f"📁 Output: {output_path}")
        print(f"📏 Size: {file_size:.1f} MB")
        
        # Show before/after info
        original_mean = np.mean(image)
        processed_mean = np.mean(processed)
        brightness_reduction = ((original_mean - processed_mean) / original_mean) * 100
        print(f"🔆 Brightness reduced by: {brightness_reduction:.1f}%")
        
    else:
        print(f"❌ Error: Could not save processed image to {output_path}")
    
    return success

def main():
    """Main function to process room photo."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/adjust_room_photo.py input_image.jpg [output_image.jpg] [preset]")
        print("Presets: gentle, balanced (default), strong")
        return
    
    input_path = sys.argv[1]
    
    # Generate output filename if not provided
    if len(sys.argv) > 2:
        output_path = sys.argv[2]
    else:
        # Auto-generate output name
        input_name = Path(input_path).stem
        input_ext = Path(input_path).suffix
        output_path = f"{input_name}_adjusted{input_ext}"
    
    # Get preset
    preset = "balanced"  # default
    if len(sys.argv) > 3:
        preset = sys.argv[3].lower()
        if preset not in ["gentle", "balanced", "strong"]:
            print(f"⚠️  Unknown preset '{preset}', using 'balanced'")
            preset = "balanced"
    
    # Check if input file exists
    if not os.path.exists(input_path):
        print(f"❌ Error: Input file not found: {input_path}")
        return
    
    print("🎨 Room Photo Brightness Adjustment")
    print("=" * 35)
    
    # Process the image
    success = process_image(input_path, output_path, preset)
    
    if success:
        print("\n🚀 Next Steps:")
        print("=" * 15)
        print(f"1. Review the adjusted image: {output_path}")
        print("2. If still too bright, try 'strong' preset:")
        print(f"   python scripts/adjust_room_photo.py {input_path} {output_path} strong")
        print("3. Upload the adjusted image to your vision model")
        print("4. Use the prompt from: prompts/room_layout_generator.md")
    else:
        print("\n🔧 Troubleshooting:")
        print("• Check input file path")
        print("• Ensure write permissions for output directory")
        print("• Try different presets: gentle, balanced, strong")

if __name__ == "__main__":
    main() 