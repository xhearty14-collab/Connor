---
name: video-frame-analysis
description: Analyze videos by extracting ordered frames with ffmpeg and sending frames to a vision model. Use when the user asks for frame-by-frame video analysis, per-frame evidence, timestamped visual timelines, UI/game/sports/monitoring motion review, or when direct Gemini video reading is unstable or too coarse.
---

# Video Frame Analysis

Use this skill for dense visual inspection when reading the whole video directly is not precise enough. The method is: extract sampled frames, preserve frame order and timestamps, send the images to a vision model, then return frame-by-frame or segment-level findings.

## Workflow

1. Confirm the source video path and the requested detail level.
2. Choose FPS:
   - `1` fps for summaries, UI walkthroughs, lectures, and long clips.
   - `2-5` fps for motion, games, sports, demonstrations, or short clips.
   - `10+` fps only for very short clips where fine motion matters.
3. Extract frames into a temporary output directory. Prefer the bundled script because it also creates a timestamp manifest:

```powershell
python .codex/skills/video-frame-analysis/scripts/extract_video_frames.py video.mp4 --fps 1 --out frames
```

4. Inspect `frames/manifest.json` to map file names to timestamps.
5. Send frames to the model in order. For many frames, batch them by segment.
6. Return JSON or a readable timeline with timestamps, visible content, action/change, text on screen, and uncertainty.
7. Delete temporary frame directories after capturing the analysis unless the user asks to keep evidence images.

## Direct ffmpeg Fallback

Use ffmpeg directly when the script is not available:

```powershell
ffmpeg -i video.mp4 -vf fps=1 frames/frame_%05d.jpg
ffmpeg -i video.mp4 -vf fps=5 frames/frame_%05d.jpg
```

With direct extraction, frame `00001` is approximately `00:00` at `fps=1`, frame `00002` is approximately `00:01`, and so on. Prefer the script when exact timestamp mapping matters.

## Gemini Frame Prompt

Use this prompt shape when sending ordered images:

```text
Analyze these video frames in order.

Each image file name maps to a timestamp in the provided manifest.
For each frame or meaningful group of adjacent frames, describe:
- timestamp or frame number
- visible subjects and objects
- action or motion implied by changes between frames
- important text on screen
- uncertainty if unclear

Return valid JSON with summary, timeline_granularity, events, and warnings.
Do not invent details when the frame is blurry, cropped, or visually ambiguous.
```

## Python Gemini Example

```python
from google import genai
from google.genai import types
import json
import os
from pathlib import Path

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

frame_dir = Path("frames")
manifest = json.loads((frame_dir / "manifest.json").read_text(encoding="utf-8"))
frame_paths = [frame_dir / item["file"] for item in manifest["frames"]]

parts = [
    "Analyze these video frames in order. Use this manifest for timestamps:\n"
    + json.dumps(manifest, ensure_ascii=False)
    + "\nReturn valid JSON with summary, timeline_granularity, events, and warnings."
]

for path in frame_paths:
    parts.append(types.Part.from_bytes(data=path.read_bytes(), mime_type="image/jpeg"))

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=parts,
)

print(response.text)
```

## Batching

Batch long videos to avoid oversized requests. A practical default is 30-80 frames per request depending on image size and requested detail. Ask the model to return a segment result, then merge segment timelines by timestamp.

Use lower JPEG quality or lower FPS before resizing away critical details such as UI text. For screen recordings, preserve readability even if fewer frames are sent.

## Output Shape

Prefer this JSON shape for reusable analysis:

```json
{
  "success": true,
  "source": {
    "type": "frame-extraction",
    "video": "video.mp4",
    "fps": 1,
    "model": "gemini-2.5-flash"
  },
  "summary": "Concise summary of the observed video.",
  "timeline_granularity": "per-frame|sampled-frames|segments",
  "events": [
    {
      "frame": "frame_00001.jpg",
      "timestamp": "00:00",
      "end_timestamp": "00:01",
      "visual": "What is visible.",
      "action": "What changes or happens.",
      "text": "Visible text, if any.",
      "confidence": "high|medium|low"
    }
  ],
  "warnings": [
    "Mention sampling gaps, blur, missing audio, or low confidence."
  ]
}
```
