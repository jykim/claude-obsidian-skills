---
name: remotion-narrated-video-essay
description: Edit narration-led Remotion video essays using talking-head footage, overlays, selective B-roll, comic callouts, and still-frame visual QA. Use for personal reflective essays; not for a generic slide deck or a final render without approval.
---

# Remotion Narrated Video Essay

Build a polished video around the recorded narration while preserving the speaker's pace and point of view.

## Editorial shape

- Keep the talking-head shot as the default visual. Prefer contextual media as an overlay rather than cutting away repeatedly.
- Use full-screen material sparingly: reserve it for a visually rich event or a sustained screen capture that needs attention.
- Match each overlay to the actual speaking beat. When narration is shortened, derive every B-roll cue from the same original-to-edited timeline mapping rather than shifting timings by guesswork.
- If cleaning a recorded talk, remove only clear filler, dead air, or repeated explanation at sentence boundaries. Preserve natural breaths and any cut that would create a visible pose or gaze jump.
- Never alter the camera original. Create a separately named proxy or edited narration track.

## Narration phrasing and timing

- Before generating narration, audit long lists, parallel clauses, comparisons, and closing triads for phrases that the voice may run together. When the user limits the edit by priority, change only the approved priority tier and preserve every word; punctuation-only approval does not authorize rewriting.
- Regenerate only the affected narration IDs, use versioned filenames, and keep unrelated visuals and audio unchanged except for timing adjustments required by the new duration.
- Do not assume commas or periods created an audible pause. Check the selected WAV with word timestamps and `silencedetect`, and record the pause at every edited high-priority boundary.
- Base scene safety on the final spoken-word end rather than the container duration. Leave at least 0.5 seconds before the next narration, music entry, transition overlap, or scene end. For a music cue triggered by a mention, measure from the end of the mentioned phrase.

## Layout and visual hierarchy

- Inspect the speaker frame before placing an overlay. Put cards opposite the face and change side when the speaker's position changes later in the recording.
- Keep overlays clear of the eyes, face, and important gestures. Use a consistent card size, corner treatment, and restrained shadow.
- Remove redundant eyebrow labels and tiny descriptive captions. A card should usually contain one large title and one legible explanatory line or two.
- Match card colors to the camera's actual palette rather than imposing a disconnected theme. Preserve enough contrast for small-screen viewing.
- For a tall analytics or dashboard screenshot, use a full-screen still and animate a slow, continuous vertical scroll across the useful content. Do not add browser chrome, ads, or unrelated page areas.
- Clearly distinguish real footage from reconstructed or AI-generated interface concepts. Do not imply that a concept visual is a real product capture.

## Optional comic callouts

- Use comic bubbles only for short self-aware observations; avoid emotional memories, family scenes, and the closing reflection.
- Make the text large, centered, and comfortably fill the bubble. Use a locally bundled, Korean-capable display font so the final render is deterministic.
- Aim the tail at the speaker's face. The tail should be a naturally joined curved shape, with no visible base seam, and it should share the bubble's shadow direction.
- Treat bubble placement as shot-specific. Render a still for each bubble and adjust its tail, scale, and side until it reads as connected to the speaker rather than floating on the wall.

## Review before final render

- Do not final-render until the user approves it.
- Render stills for the opening, every visual treatment, each overlay side change, every comic bubble, the start/end of any scrolling screen capture, and the ending.
- Check that text is readable, no card or bubble touches the face, screen captures show only relevant content, and all media matches the narration's claim.
- Run the project type check or lint. If it is blocked by unrelated existing code, report that precisely without modifying unrelated files.
- For a multi-part series, render and decode-check every part before assembling the full video. Then verify the merged duration, video and audio streams, the joins between parts, and the final frame. Do not substitute a low-resolution review render when the user asked for direct inspection or final output.
