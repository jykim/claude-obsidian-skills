---
name: remotion-vlog
description: Import and edit Pocket, phone, action-camera, or similar footage into a concise Remotion vlog with selective cuts, researched location context, titles, maps, transition captions, optional face-adjacent comic bubbles, licensed background music, beat-aware timing, preview approval, verified camera eject, and final render verification. Use for personal trip, family-day, garden, outing, and location-based vlog requests; do not use for generic presentation videos or pause-only cleanup.
---

# Remotion Vlog

Turn raw outing footage into a short story that remains easy to inspect and revise as a Remotion project. Preserve the original media and treat the user's editorial exclusions as hard requirements.

## Interpret the request

- Resolve the requested camera or mounted volume, date scope, output folder, title, people, place, and render gate from the user's messages. Treat “today” using the user's local timezone.
- Inspect files and metadata before choosing clips. Do not mix in footage outside the requested event merely because it is adjacent on disk.
- If the destination or event can be inferred confidently from the footage and request, proceed. Ask only when two materially different events remain plausible.
- Prefer an existing Remotion project in the requested output folder. Create a new one only when none exists.
- When available, load `remotion-best-practices` before editing Remotion code. Use a speech-cleaning workflow only when spoken content determines the cuts.

## Protect the footage

- Never modify, rename, move, or delete camera originals.
- Put selected, trimmed, consistently encoded proxies under the Remotion project's `public/` tree. Keep temporary transcripts and contact sheets outside the project unless the user asks to retain them.
- Preserve unrelated user changes in an existing project.
- If the user wants to eject a camera or card, copy only the selected source originals when capacity allows, then verify every destination against its source with a byte comparison or checksum before saying it is safe to eject. If capacity only permits proxies, say explicitly that full originals were not preserved locally.

### Verified import and automatic eject

When the user asks to import footage and automatically eject the camera or card:

1. Resolve the exact date or event scope and choose a dedicated `media-source/<event-date>/originals` destination outside `public/`.
2. Check destination capacity before copying and leave enough free space for the edit. Prefer selected full-resolution originals plus relevant camera stills. Camera-generated LRF proxies are optional when verified local edit proxies already exist. If the full date set does not fit, state what will and will not be imported before proceeding.
3. Copy without changing the source files. Verify the destination file count and total bytes, then perform a byte comparison or SHA-256 comparison for every copied file.
4. Eject only after all requested copies pass verification. Target the resolved mounted volume explicitly, confirm the eject command succeeds, and confirm that the mount path is gone.
5. On a copy, capacity, or verification failure, keep the device mounted and report the exact blocker. Never describe proxy-only storage as a full original import.

## Select scenes editorially

Keep scenes that contribute at least one of these:

- establish the destination, route, or atmosphere;
- reveal a visually distinct area or meaningful transition;
- contain a concise, authentic interaction;
- explain a place-specific fact;
- provide a satisfying opening or ending.

Remove or shorten scenes that are repetitive, unstable, accidental, private, or unrelated to the outing. Default to removing clothing changes or personal-preparation footage, random logistics, office/library/café planning, stray ethnicity references, and other conversation that interrupts the location story. Do not promote a throwaway complaint such as “too hot” into a comic bubble unless the user explicitly wants it.

For a talking-head opening, compare repeated greetings or takes and start from the take the user selected. Screen the visible lead-in for grooming, ear or nose touching, clothing or microphone adjustments, and other setup gestures; remove them when requested, but use a coherent phrase boundary or a cutaway when the gesture overlaps useful speech.

When dialogue drives the decision:

1. Transcribe candidate clips in the likely spoken language, with word timestamps when practical.
2. Search for the user's target phrases and inspect the neighboring sentence or visual beat.
3. Prefer removing one coherent shot or beat over cutting a single word and leaving an audible fragment.
4. Cross-check ambiguous transcription against representative frames or a stronger model before deleting valuable footage.
5. Treat detected pauses and filler words as cut candidates, not automatic deletions. Inspect both the spoken phrase boundary and the moving image at every internal join, preserve a natural pace around the final sentence, and keep enough audio handle or silence to avoid clipped consonants and clicks.

If the plan changes late in the day, keep the original story coherent and treat the alternate activity as a clearly titled epilogue or appendix when that creates a satisfying turn. A small opening bubble may tease an end twist without revealing it; the ending must still make sense to a viewer who ignores the hint.

For a short practical demonstration inside a vlog, derive the steps from visible actions rather than writing a generic tutorial. Align each step overlay to the action, retain only useful narration, and remove isolated trailing words or recognition artifacts with word-level timing or a brief audio fade while leaving the visual intact. Add a concise safety qualifier when the footage does not show every precaution.

## Research the location

- Browse current official or primary sources for the address, scale, notable areas, history, hours, or admission when these facts improve the story.
- Use only a few facts that correspond to scenes actually present in the footage. Avoid turning a personal vlog into an information deck.
- Keep source URLs for the handoff and avoid unsupported claims.

For an opening location map, use an accurate map source such as OpenStreetMap. Show a visible location pin, place name, and concise address. Crop browser chrome and retain the required map attribution. Never substitute an AI-generated map for a real one.

## Build the Remotion composition

Use 1920×1080 at 24 fps by default unless the footage or user specifies otherwise. Keep one ordered scene list as the timing source of truth.

Include only the elements the story needs:

- an opening title with the vlog title, location, and featured person when supplied;
- an early location map, usually overlaid for roughly four to six seconds without needlessly lengthening the edit;
- chapter or garden-area title cards at meaningful transitions;
- a short bottom caption at the start of every retained scene or transition;
- occasional comic dialogue bubbles for memorable lines;
- restrained crossfades or other transitions that match the footage.

When the user supplies a handwritten note or reference image as an insert, honor the requested corner and size, preserve its aspect ratio, and verify readability in a rendered still at normal viewing scale. Re-check that it does not cover the speaker's face and that chapter titles, captions, and other cards do not collide with it. Treat requested title and card positions as layout constraints rather than universal defaults.

When the user wants section titles distinguished without boxes, remove pills, panels, borders, and card shadows; use scale, weight, position, and a restrained text shadow instead. Match the opening title's type family and hierarchy, then verify the larger text remains inside the safe area on representative section stills.

Track each B-roll image and video by asset and timeline range. When the user asks to use footage only once, do not repeat the same visual at a later beat or chapter; one simultaneous foreground-plus-background treatment of a vertical clip counts as one editorial use. Prefer returning to the talking head or choosing a genuinely different source over recycling the same shot without intent.

If the user asks for a spoken farewell, retain the complete final sign-off and end on that shot. Do not append a silent title or end card after it unless the user requests one.

All animation must be frame-driven with Remotion timing APIs. Premount media and overlays when useful. Keep source audio unless a scene is intentionally muted.

### Licensed background music

- Add music only when the user requests it. If no track is supplied, search current royalty-free catalogs, verify the license on the provider's primary page, and offer a small auditionable shortlist before committing to a track. “Royalty-free” does not imply public domain.
- Download the selected track under the project's `public/music/` tree. Keep its title, artist, source URL, and license URL for the handoff. Reuse one local asset across sibling compositions only when the user asks for the same music; mix each composition independently.
- Inspect track duration, mean/peak level, and tempo before editing. Preserve useful camera audio and apply frame-driven fades plus dialogue ducking rather than replacing all source sound. For a normalized music track, roughly 10–15% base volume and 25–35% of that level during dialogue are useful starting points, not fixed targets.
- When the track is only slightly shorter than the composition, prefer a delayed musical entrance and an intentional ending fade over an audible restart. Use looping, time-stretching, or an additional track only when the mismatch is substantial and the result is musically deliberate.
- For a music-only revision, keep the existing visual edit unless the user also requests rhythmic cutting. Verify the change with a short H.264/AAC smoke render and Remotion Studio; do not treat that smoke test as approval for the final render.

When rhythmic cutting is requested or clearly part of the chosen style:

1. Detect a reliable beat grid or tempo from the selected track; do not infer timing from the filename or genre alone.
2. Prefer placing the visual center of a crossfade or the hard-cut frame on a beat, using downbeats or phrase boundaries for major chapters when they are close enough.
3. Make the smallest useful frame changes. Do not remove valuable dialogue, a key action, or a satisfying ending merely to hit a beat, and never extend a sequence beyond its media duration because that can create a frozen or empty frame.
4. Keep beat indices or derived transition centers in code when practical. After any duration change, regenerate scene starts, captions, dialogue bubbles, music-ducking ranges, and total duration from the same timeline source of truth.
5. Render and inspect the changed cut boundaries, then confirm that the audio stream decodes and that the ending lands cleanly.

### Transition captions

- Write concise scene labels rather than verbatim subtitles.
- Place them in the lower safe area with a readable pill or shadow.
- Fade or slide them in briefly, then clear the image.
- Store timing as derived scene starts when practical. If JSON is used, validate every start after scene removal.
- Treat the user's factual correction about who spoke or performed an action as authoritative for the edit. Update every caption and bubble that expresses the corrected fact so the overlays do not contradict one another.

### Comic dialogue bubbles

- Use bubbles sparingly and only for lines that add character or humor.
- Place each bubble beside the visible speaker's face, not at a fixed lower-third position.
- Point the tail toward the speaker and keep the face, eyes, hands, and important scenery unobstructed.
- Choose left or right placement per shot and verify it from rendered stills. Manual coordinates are acceptable because face position changes by scene.
- Do not add a bubble when the speaker's face is not visible or the line is sensitive, incidental, or unrelated.

## Recalculate after cuts

Removing a scene changes transition overlap as well as scene duration. Recompute:

- total composition duration;
- every downstream scene start;
- transition-caption intervals;
- dialogue-bubble intervals;
- map or global overlay timing if it occurs after the cut.

Do not shift downstream timestamps by visual guesswork. Derive them from scene durations and transition overlap, then render stills at the updated points.

When a whole chapter, example, or newly-started activity is removed, also update every dependent promise: opening counts and singular/plural wording, chapter labels, captions, scene arrays, total duration, and unused imports or references. Search the source for the removed concept so the edit does not continue to promise material that no longer appears.

## Preview approval gate

If the user wants to review before rendering, or has stated that they always review before the final render:

1. Start or preserve Remotion Studio and provide its local URL.
2. Render stills only for the opening, map, each title style, every bubble placement, new cut boundaries, and ending.
3. Inspect the stills for faces, captions, title legibility, map accuracy, and transition continuity.
4. Update the Remotion source and wait for explicit render approval.

For audio-only changes, a short rendered smoke segment should confirm music entrance, ducking, and ending behavior. Render new stills only when music synchronization also changes visual cut or overlay timing.

Do not start a full render before that approval. Requests to edit, make, finish, or perform a final check are not render approval. A later instruction such as “final check and render” or an explicit “render now” satisfies the gate. If a render has already started when the user says to stop, interrupt it immediately and verify that no final output is being presented as complete.

## Final verification and handoff

Before rendering, run lint/type checking and list the composition to confirm resolution, fps, and duration. After approval:

- render an H.264 MP4 with AAC audio unless another delivery format is requested;
- for an end-to-end visual audit, inspect a representative middle frame and a near-end frame from every scene; check for black or frozen media, awkward face crops, stale captions, missing map attribution, and overlays that outlive their action;
- spot-check transcribed dialogue edits and every deliberate music restart or ducking boundary so stray words and abrupt level changes do not survive the final render;
- inspect the output with `ffprobe` for dimensions, frame rate, duration, and audio;
- decode the complete file to a null sink to catch corruption;
- provide clickable links to the final MP4 and Remotion project;
- summarize the consequential removals and retained creative elements;
- cite the official sources used for location facts.

For the originating Bellevue Botanical Garden example, the preferred result used an OpenStreetMap intro, official garden facts, bottom transition captions, face-adjacent Leona bubbles, and removed clothing-change footage plus unrelated ethnicity, office, library, café, and heat-complaint material. Treat those as examples of the editorial principles above, not mandatory content for every vlog.
