#!/usr/bin/env python3
"""
Generate marble texture images using Gemini API for Treasury brand guidelines.
Creates tileable marble patterns in Treasury, Carrara, and Gold-veined styles.
"""

import os
from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

OUTPUT_DIR = "/Users/CorcosS/code/home.treasury.gov/static/brand-guidelines/textures"

# Texture prompts - each designed for a specific Treasury use case
TEXTURES = [
    {
        "name": "marble-treasury",
        "prompt": """Create a seamless tileable marble texture image. Style: Warm Carrara marble like the floors of the Treasury Building in Washington DC.

Requirements:
- Warm cream/off-white base color (#FAF8F4)
- Subtle brown/taupe veins flowing diagonally across the surface
- Veins should be organic, flowing, and vary in thickness
- Some veins should branch naturally
- Subtle variation in the base stone color (not flat)
- Sophisticated, expensive, government-building feel
- Should tile seamlessly when repeated
- Photorealistic texture, not illustration
- No text, no objects, just the marble surface
- Soft, diffused lighting""",
        "aspect": "4:3",
    },
    {
        "name": "marble-carrara",
        "prompt": """Create a seamless tileable marble texture image. Style: Classic Italian Carrara marble.

Requirements:
- Cool white/light gray base color
- Gray veins with subtle blue undertones flowing across the surface
- Veins should be fine, elegant, and vary in intensity
- Some areas with denser vein clusters, others more open
- Very subtle base color variation
- Elegant, timeless, museum-quality feel
- Should tile seamlessly when repeated
- Photorealistic texture, not illustration
- No text, no objects, just the marble surface
- Clean, even lighting""",
        "aspect": "4:3",
    },
    {
        "name": "marble-gold-veined",
        "prompt": """Create a seamless tileable marble texture image. Style: Luxurious Calacatta marble with gold veining.

Requirements:
- Warm cream/white base color
- Subtle golden/amber veins flowing across the surface (like Calacatta Borghini)
- Veins should be bold but not overwhelming
- Natural branching patterns
- Premium, luxurious, prestigious feel
- Should tile seamlessly when repeated
- Photorealistic texture, not illustration
- No text, no objects, just the marble surface
- Warm, sophisticated lighting
- The gold should be subtle metallic, not yellow""",
        "aspect": "4:3",
    },
    {
        "name": "marble-gray",
        "prompt": """Create a seamless tileable marble texture image. Style: Sophisticated gray Bardiglio marble.

Requirements:
- Medium gray base color with subtle cool undertones
- Darker gray and white veins creating contrast
- Dramatic but refined veining pattern
- Contemporary, modern government feel
- Should tile seamlessly when repeated
- Photorealistic texture, not illustration
- No text, no objects, just the marble surface
- Even, professional lighting""",
        "aspect": "4:3",
    },
]


def generate_texture(texture_config):
    """Generate a single marble texture using Gemini."""
    name = texture_config["name"]
    prompt = texture_config["prompt"]
    aspect = texture_config["aspect"]

    print(f"\nGenerating {name}...")

    response = client.models.generate_content(
        model="gemini-3-pro-image-preview",
        contents=[prompt],
        config=types.GenerateContentConfig(
            response_modalities=['TEXT', 'IMAGE'],
            image_config=types.ImageConfig(
                aspect_ratio=aspect,
            ),
        ),
    )

    # Save the image
    for part in response.parts:
        if part.inline_data:
            img = part.as_image()
            output_path = os.path.join(OUTPUT_DIR, f"{name}.jpg")
            img.save(output_path)
            print(f"  Saved: {output_path}")
            return output_path

    print(f"  ERROR: No image generated for {name}")
    return None


def main():
    print("=" * 60)
    print("Treasury Marble Texture Generator")
    print("=" * 60)

    generated = []
    for texture in TEXTURES:
        path = generate_texture(texture)
        if path:
            generated.append(path)

    print("\n" + "=" * 60)
    print(f"Generated {len(generated)} textures:")
    for path in generated:
        print(f"  - {path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
