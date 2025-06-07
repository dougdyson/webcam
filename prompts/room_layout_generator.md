# Room Layout Generator Prompt

Use this prompt with premium cloud vision models (GPT-4 Vision, Claude Vision, etc.) to generate your room layout description.

## Prompt for Cloud Vision Model

```
Please analyze this image of my room and create a detailed layout description that will be used for consistent webcam descriptions. I need you to format the output exactly as shown below, filling in the specific details from what you see in the image.

Format your response as:

ROOM LAYOUT REFERENCE:
======================

ROOM TYPE: [Identify the primary room type: Kitchen, Office, Living Room, Bedroom, Dining Room, Workshop, etc.]

MAIN AREAS:
[For each distinct area/zone in the room, describe:]
- [Area Name]: [Detailed description including furniture, appliances, or fixtures with colors in parentheses]

COMMON OBJECTS & THEIR TYPICAL LOCATIONS:
[List items you can see and where they're typically located:]
- [Object name]: [Typical location with color details in parentheses]

COLOR REFERENCE FOR IDENTIFICATION:
[List the specific colors of major surfaces, furniture, and objects:]
- [Surface/Object]: [Specific color and material description]

SPATIAL REFERENCES:
[Define directional references based on the room layout:]
- "Left" = [toward what area/feature]
- "Right" = [toward what area/feature]
- "Front/Forward" = [toward what area/feature]
- "Back/Rear" = [toward what area/feature]
- "Center" = [what area constitutes the center]

TYPICAL ACTIVITIES BY LOCATION:
[Based on the room type and setup, list likely activities:]
- [Activity type]: [Where this activity typically happens]

Instructions for analysis:
1. Look carefully at the room layout and identify all distinct areas/zones
2. Note the colors of major surfaces - countertops, cabinets, furniture, appliances
3. Identify where common objects are located or would typically be placed
4. Establish clear spatial references based on the camera's perspective
5. Consider what activities would naturally happen in each area
6. Be specific with colors - use descriptive terms like "warm brown wood", "stainless steel", "cream white", etc.
7. Include both permanent fixtures and moveable items you can see

The goal is to create a reference that will help an AI understand this space consistently, even when colors in webcam images are unclear or lighting changes.
```

## Example Output Format

Here's what the model should generate for a kitchen:

```
ROOM LAYOUT REFERENCE:
======================

ROOM TYPE: Kitchen

MAIN AREAS:
- Island/Center: Large rectangular wooden island (warm honey-colored wood) with white marble-like countertop
- Main Counter: L-shaped counter along right and back walls with white quartz countertops and dark gray cabinets below
- Stove Area: Professional-style range (stainless steel) set into back wall with gray subway tile backsplash
- Refrigerator Zone: Large stainless steel refrigerator in far right corner
- Sink Area: Undermount sink in right wall counter with chrome faucet

COMMON OBJECTS & THEIR TYPICAL LOCATIONS:
- Coffee maker: Right counter near refrigerator (black with chrome accents)
- Microwave: Built into upper cabinets above counter (stainless steel)
- Knife block: Island countertop right side (dark wood with silver knives)
- Fruit bowl: Island center (white ceramic)
- Dish towels: Hanging from oven handle (blue and white striped)

COLOR REFERENCE FOR IDENTIFICATION:
- Island base: Warm honey/golden wood stain
- Island countertop: White marble with gray veining
- Main cabinets: Dark charcoal gray painted finish
- Main countertops: Pure white quartz
- Backsplash: Light gray subway tiles
- Appliances: Stainless steel finish
- Flooring: Light oak hardwood

SPATIAL REFERENCES:
- "Left" = toward dining area and windows
- "Right" = toward refrigerator and main counters
- "Back" = toward stove and backsplash wall
- "Center" = the island area
- "Front" = toward camera/entrance

TYPICAL ACTIVITIES BY LOCATION:
- Food prep: Island countertop and main counter areas
- Cooking: Stove area and island (if it has cooktop)
- Cleaning: Sink area and adjacent counter space
- Storage access: Refrigerator area and cabinet zones
- Coffee/beverages: Right counter near coffee maker
```

## Tips for Best Results

1. **Take a good photo**: 
   - Well-lit room
   - Wide angle showing most of the space
   - Multiple angles if the room is large

2. **Use a premium model**:
   - GPT-4 Vision (via ChatGPT Plus or API)
   - Claude 3 Opus/Sonnet with vision
   - Google Gemini Pro Vision

3. **Review and edit**: The AI might miss some details or colors, so review and adjust as needed

4. **Test with your space**: After generating, see if the spatial references make sense from your webcam's perspective

## Integration

Once you have the generated layout:

1. Save it as `config/room_layout.txt`
2. Test with: `python examples/enhanced_room_description.py`  
3. Adjust any spatial references if needed based on your webcam's actual position

This approach gives you the best of both worlds - premium vision model accuracy for the one-time layout analysis, and consistent reliable descriptions for ongoing use! 