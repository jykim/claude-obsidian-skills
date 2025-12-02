# Image Generation Skill

A comprehensive skill for generating AI images for documents and slide decks with user-defined styles.

## Purpose

Automatically analyze documents or slide decks, identify sections/slides needing images, and generate appropriate images in the user's preferred visual style.

## When to Use This Skill

- User requests to "add images to my presentation/document"
- User wants to "generate visuals for my slides"
- User asks to "illustrate my markdown document"
- User needs consistent visual style across multiple images

## Workflow

### Phase 1: Analysis
1. Read the target document/slide deck
2. Identify all sections (for documents) or slides (for presentations) that:
   - Have text content but NO images
   - Are actual content sections (not just headings/dividers)
   - Would benefit from visual representation
3. For each section/slide, extract:
   - Title/heading
   - Main content theme
   - Key concepts to visualize

### Phase 2: Style Selection

Ask the user to choose from these visual styles:

**1. Vibrant Modern Cartoon** (Default)
- Bright gradient colors (blues, pinks, purples, oranges)
- Flat design with subtle shadows
- Simple, friendly human figures
- Metaphorical visual storytelling
- Best for: Business presentations, educational content

**2. Professional Minimalist**
- Muted color palette (navy, gray, white, accent color)
- Clean geometric shapes
- Abstract representations
- Corporate-friendly aesthetic
- Best for: Business reports, formal presentations

**3. Playful Illustration**
- Hand-drawn style with organic shapes
- Warm, friendly color palette
- Character-focused narratives
- Whimsical details
- Best for: Creative projects, personal blogs

**4. Technical Diagram**
- Clean lines and structured layouts
- Blueprint/schematic style
- Infographic-inspired
- Data visualization elements
- Best for: Technical documentation, tutorials

**5. Artistic Watercolor**
- Soft watercolor textures
- Pastel color schemes
- Flowing, organic compositions
- Artistic and expressive
- Best for: Personal journals, creative writing

**6. Bold Graphic**
- High contrast colors
- Strong geometric shapes
- Pop art influence
- Eye-catching and modern
- Best for: Marketing materials, social media

**7. Custom Style**
- User provides specific style description
- Can combine elements from multiple styles
- Maximum flexibility

### Phase 3: Image Generation

For each identified section/slide:

1. **Create detailed prompt** based on:
   - Section/slide content and theme
   - Selected visual style
   - Key concepts to visualize
   - Standard constraints (no text in images, square format)

2. **Generate image** using:
   ```bash
   python3 "generate_slide_cartoon.py" \
       "[detailed description]" \
       --output-path "[appropriate path]" \
       --style "[style description]" \
       --auto-approve
   ```

3. **Track progress**:
   - Use TodoWrite to track generation progress
   - Show cost estimate upfront (N images × $0.04)
   - Report any generation failures

### Phase 4: Integration

For each generated image:

1. **Insert into document/slides**:
   - Documents: Add after section heading, before content
   - Slides: Add after content, before speaker notes
   - Format: `![right fit](_files_/filename.jpg)` for slides
   - Format: `![](path/to/image.jpg)` for documents

2. **Update speaker notes/captions** (if applicable):
   - Reference the visual naturally
   - Explain what the image represents
   - Connect visual to spoken/written content

3. **Verify insertion**:
   - Check all images are properly placed
   - Ensure paths are correct
   - Confirm formatting is consistent

## Style Descriptions for generate_slide_cartoon.py

Map user's style choice to --style parameter:

1. **Vibrant Modern Cartoon**:
   - `"vibrant modern minimalist cartoon illustration"`

2. **Professional Minimalist**:
   - `"professional minimalist illustration with muted colors and clean geometric shapes"`

3. **Playful Illustration**:
   - `"playful hand-drawn illustration with warm friendly colors and whimsical details"`

4. **Technical Diagram**:
   - `"technical diagram illustration with clean lines and infographic style"`

5. **Artistic Watercolor**:
   - `"artistic watercolor illustration with soft pastel colors and flowing organic composition"`

6. **Bold Graphic**:
   - `"bold graphic illustration with high contrast colors and strong geometric shapes"`

7. **Custom Style**:
   - Use user's exact description

## File Naming Convention

### For Slide Decks:
- Format: `[slide-topic-slug].jpg`
- Example: `ai-changes-game.jpg`, `perils-specialization.jpg`
- Location: Same `_files_/` directory as slide deck

### For Documents:
- Format: `[section-number]-[topic-slug].jpg`
- Example: `01-introduction.jpg`, `03-methodology.jpg`
- Location: `_files_/` subdirectory relative to document

## Cost Estimation

Always show cost estimate before proceeding:
- Each image: $0.04
- Total cost: N images × $0.04
- Example: "Generating 10 images will cost $0.40"

## Error Handling

- If generation fails: Report error, continue with remaining images
- If image path is invalid: Create directory, retry
- If duplicate names: Append number suffix (e.g., `image-1.jpg`, `image-2.jpg`)

## Best Practices

1. **Batch generation**: Generate all images first, then insert all at once
2. **Parallel generation**: When possible, generate multiple images concurrently
3. **Style consistency**: Use same style for all images in a document/deck
4. **Descriptive prompts**: Include specific visual metaphors and concepts
5. **Square format**: Always use 1024x1024 for slides (compatible with `right fit`)

## Example Invocation

### Slide Deck Example

**User Request**: "Add images to my presentation slides"

**Skill Workflow**:

1. **Analysis Phase**:
   - Read slide deck
   - Identify 8 text-only slides
   - Extract themes and concepts

2. **Style Selection Phase**:
   - Present 7 style options to user
   - User selects: "Vibrant Modern Cartoon"
   - Confirm style choice

3. **Generation Phase**:
   - Show cost estimate: "$0.32 (8 images)"
   - Generate all 8 images with consistent style
   - Track progress with TodoWrite
   - Report completion: "8/8 images generated successfully"

4. **Integration Phase**:
   - Insert all images with `![right fit]()` format
   - Update speaker notes to reference visuals
   - Verify all paths and formatting

**Result**: Complete slide deck with consistent visual style across all slides.

### Document Example

**User Request**: "Generate section images for my article"

**Skill Workflow**:

1. **Analysis Phase**:
   - Read markdown document
   - Identify 5 main sections (H2 headings)
   - Extract key concepts from each section

2. **Style Selection Phase**:
   - Present 7 style options
   - User selects: "Professional Minimalist"
   - Confirm style for business article

3. **Generation Phase**:
   - Cost estimate: "$0.20 (5 images)"
   - Generate numbered section images
   - Files: `01-introduction.jpg` through `05-conclusion.jpg`

4. **Integration Phase**:
   - Insert after each section heading
   - Format: `![](\_files_/0X-section-name.jpg)`
   - Add image captions if needed

**Result**: Professional article with minimalist illustrations for each section.

## Advanced Features

### Batch Processing
When processing multiple documents:
- Reuse style choice across all documents
- Generate all images in one batch
- Apply consistent naming convention

### Smart Image Placement
- Slides: After content, before speaker notes (`^` lines)
- Documents: After heading, before first paragraph
- Respect existing images (don't duplicate)

### Style Variations
Allow user to specify variations:
- "Vibrant Modern Cartoon, but with green/blue color scheme"
- "Professional Minimalist + Technical Diagram elements"
- Completely custom: "Studio Ghibli style with nature themes"

## Maintenance

### Updating Style Options
To add new styles:
1. Add to style list in Phase 2
2. Add style mapping in "Style Descriptions" section
3. Test with sample prompts
4. Update examples if needed

### Troubleshooting
- Images not fitting: Check `![right fit]()` vs `![]()` format
- Path errors: Verify `_files_/` directory exists
- Style inconsistency: Ensure same --style parameter for all images
- Cost concerns: Offer to generate subset first for preview