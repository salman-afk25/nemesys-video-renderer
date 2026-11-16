







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

- **LLM (text)** - `POST /a/llm` on the Konten Bot Cloudflare Worker, which proxies the model (no provider name appears in this repo). Used by the clip step to pick the best 30-60 second segment from a timestamped transcript as JSON.
- **Gemini TTS (Google)** - `POST /render/tts`, one call per narration line, with the voice id and style taken from the job payload.
- **edge-tts (Microsoft Edge neural voices)** - narration fallback used once Gemini fails: `id-ID-GadisNeural` by default and `id-ID-ArdiNeural` for Konten videos.
- **Cloudflare Workers AI (image generation)** - `POST /render/img` for scene key visuals; Cloudflare quota error `4006` switches to the local generator.
- **Stability AI SD-Turbo (`stabilityai/sd-turbo`)** - `diffusers` `AutoPipelineForText2Image` on PyTorch CPU, 2 inference steps, guidance scale 0.0, weights cached with `actions/cache`.
- Fallback order: Gemini TTS, then edge-tts; Cloudflare Workers AI images, then SD-Turbo on the runner.
- **Pexels video search** and **yt-dlp** (both through the Konten Bot worker API / runner) for source footage in the clip and stock-video paths.
- **Remotion 4.0.300 with React 18.3.1** in TypeScript for the animated compositions, rendered with `npx remotion render` on Node 20.
- **ffmpeg / ffprobe** - zoompan camera moves and shake, xfade joins, eq, colorbalance, vignette and noise grading, `aevalsrc` chord-pad music, sidechaincompress ducking, loudnorm, ASS subtitles, libx264.
- **Python 3**: requests, asyncio, subprocess, edge-tts, num2words, torch, diffusers, transformers, accelerate, safetensors.
- **GitHub Actions** (`workflow_dispatch`, ubuntu-latest, `actions/cache`) as the render farm, driven by the Discord bot behind the Cloudflare Worker.
## How it works

1. A command in Discord reaches the Cloudflare Worker, which stores the story and dispatches the workflow with a job ID; the renderer fetches that job JSON back from the worker.
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


























