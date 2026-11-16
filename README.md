







# Nemesys Video Renderer

Python renderers that turn a short-story script into a finished 9:16 vertical video: AI images, narration, camera motion, subtitles and music, rendered free on GitHub Actions.

My role: designed and built end to end.

## Features

- Pulls a render job with story text, per-scene image prompts, narration, voices and mood from a Cloudflare Worker API
- Two shots per scene with varied camera moves such as zoom in, zoom out and pans, plus camera shake on dramatic beats
- Hosted AI image generation with a free local fallback: SD-Turbo on the GitHub CPU runner when the image quota runs out
- Multi-voice Indonesian narration through Gemini TTS, with edge-tts neural voices as backup
- Speech normalization: digits spelled out with num2words, abbreviations expanded, markup and emoji stripped
- Anime color grading, film grain and vignette, crossfade transitions, and synthesized chord-pad music ducked under the voice
- Burned-in ASS subtitles with speaker labels, plus title and studio watermark
- Hard 60 second budget: narration tempo is adjusted, and the render fails early if the dialogue still overruns
- Second pipeline for short form content: Remotion motion renders, Pexels stock footage videos, and LLM based highlight clipping
- Progress, quota pauses and failures are posted back to the API so each job reports its own status

## Tech stack

- Python 3 with requests, asyncio and subprocess
- Gemini TTS through the worker endpoint, and edge-tts with Microsoft Edge neural voices, id-ID-GadisNeural and id-ID-ArdiNeural
- AI image generation through a Cloudflare Worker endpoint, with stabilityai/sd-turbo via diffusers and PyTorch on CPU as fallback
- LLM text endpoint of the same worker, used to pick the best clip from a timestamped transcript
- Remotion 4 with React 18 in TypeScript for animated compositions
- ffmpeg and ffprobe: zoompan, xfade, eq and colorbalance, aevalsrc, loudnorm, sidechaincompress, ASS subtitles, libx264
- yt-dlp and Pexels search for source footage
- GitHub Actions with workflow_dispatch, ubuntu-latest runners and actions/cache for the model weights
- num2words for reading numbers in Indonesian

## How it works

1. A workflow is dispatched with a job ID, and the renderer fetches the story JSON from the worker.
2. Each scene gets a wide shot image and, when the scene is dramatic, a close-up as well.
3. Narration is synthesized line by line, trimmed and time stretched so the episode lands near 60 seconds.
4. ffmpeg animates each still, joins shots with crossfades, mixes voice over music, then burns in subtitles.
5. The finished MP4 is uploaded back to the worker.

## Setup

1. Keep the render key as the repository secret RENDER_SECRET; the worker URL and job ID come from workflow env and inputs.
2. The workflow installs ffmpeg, fonts and the Python dependencies, and caches the SD-Turbo weights.
3. Run the Nemesys Video Cerpen or Konten Bot workflow with a job ID.

## Security

- Secrets stay in GitHub Actions secrets and environment variables only, never in this repository.
- The job key is masked in the Actions log.
- No API keys, tokens or passwords are committed.


























