"""NEMESYS AI COMPANY - render video cerpen 9:16 (gambar AI + narasi + subtitle), gratis via GitHub Actions."""
import asyncio, json, os, subprocess, sys, textwrap
import requests, edge_tts

W = os.environ["WORKER_URL"].rstrip("/")
H = {"x-nemesys-key": os.environ["RENDER_SECRET"]}
JOB = os.environ["JOB_ID"]
OUT = "out"; os.makedirs(OUT, exist_ok=True)
WIDTH, HEIGHT, FPS = 720, 1280, 25

def log(msg):
    print(msg, flush=True)
    try: requests.post(f"{W}/render/log", headers=H, json={"job": JOB, "msg": msg[:1500]}, timeout=20)
    except Exception: pass

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0: raise RuntimeError(r.stderr[-1500:])
    return r.stdout

def dur(path):
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path]).strip())

def ts(t):
    h, r = divmod(t, 3600); m, s = divmod(r, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"

async def tts(text, path, voice):
    await edge_tts.Communicate(text, voice, rate="+5%").save(path)

def main():
    job = requests.get(f"{W}/render/job/{JOB}", headers=H, timeout=30).json()
    story = job["story"]; scenes = story["scenes"][:10]
    voice = story.get("voice", "id-ID-GadisNeural")
    style = story.get("gaya_visual", "")
    clips, subs, t = [], [], 0.0
    for i, sc in enumerate(scenes):
        img = f"{OUT}/s{i}.jpg"; aud = f"{OUT}/s{i}.mp3"; clip = f"{OUT}/c{i}.mp4"
        prompt = f"{sc['prompt_gambar']}, {style}, vertical composition, cinematic, highly detailed"
        for attempt in range(3):
            r = requests.post(f"{W}/render/img", headers=H, json={"prompt": prompt}, timeout=120)
            if r.ok and len(r.content) > 5000: open(img, "wb").write(r.content); break
        else: raise RuntimeError(f"Gagal membuat gambar adegan {i+1}: {r.status_code} {r.text[:200]}")
        asyncio.run(tts(sc["narasi"], aud, voice))
        d = dur(aud) + 0.6
        frames = int(d * FPS)
        zoom = "min(zoom+0.0009,1.15)" if i % 2 == 0 else "if(eq(on,0),1.15,max(zoom-0.0009,1.0))"
        vf = (f"scale=-2:{int(HEIGHT*1.2)},crop={int(WIDTH*1.2)}:{int(HEIGHT*1.2)},"
              f"zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={WIDTH}x{HEIGHT}:fps={FPS},"
              f"fade=t=in:st=0:d=0.4,fade=t=out:st={d-0.4:.2f}:d=0.4")
        run(["ffmpeg", "-y", "-loop", "1", "-i", img, "-i", aud, "-filter_complex", f"[0:v]{vf}[v];[1:a]apad=pad_dur=0.6[a]",
             "-map", "[v]", "-map", "[a]", "-t", f"{d:.2f}", "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "96k", "-ar", "44100", "-ac", "2", clip])
        # subtitle dipecah per ~8 kata
        words = sc["narasi"].split(); chunks = [" ".join(words[k:k+8]) for k in range(0, len(words), 8)] or [""]
        per = (d - 0.6) / len(chunks)
        for k, c in enumerate(chunks):
            subs.append((t + k*per, t + (k+1)*per, c))
        clips.append(clip); t += d
        log(f"Adegan {i+1}/{len(scenes)} selesai")
    with open(f"{OUT}/list.txt", "w") as f:
        for c in clips: f.write(f"file '{os.path.basename(c)}'\n")
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", f"{OUT}/list.txt", "-c", "copy", f"{OUT}/joined.mp4"])
    ass = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {WIDTH}", f"PlayResY: {HEIGHT}", "",
           "[V4+ Styles]", "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV",
           "Style: Sub,DejaVu Sans,36,&H00FFFFFF,&H00000000,&H80000000,1,1,3,1,2,50,50,170",
           "Style: Judul,DejaVu Sans,52,&H0000D7FF,&H00000000,&H80000000,1,1,4,2,8,40,40,140", "",
           "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
           f"Dialogue: 0,{ts(0)},{ts(3.5)},Judul,,0,0,0,,{{\\fad(300,300)}}{story.get('judul','').replace(',', '，')}"]
    for a, b, c in subs: ass.append(f"Dialogue: 0,{ts(a)},{ts(b)},Sub,,0,0,0,,{c}")
    open(f"{OUT}/sub.ass", "w").write("\n".join(ass))
    final = f"{OUT}/video.mp4"
    total = dur(f"{OUT}/joined.mp4")
    vbit = max(400, min(1500, int((9.0 * 8 * 1024) / total - 100)))  # target < 9,5 MB (batas upload Discord 10 MB)
    run(["ffmpeg", "-y", "-i", f"{OUT}/joined.mp4", "-vf", f"subtitles={OUT}/sub.ass", "-c:v", "libx264", "-preset", "medium",
         "-b:v", f"{vbit}k", "-maxrate", f"{vbit}k", "-bufsize", f"{vbit*2}k", "-c:a", "copy", "-movflags", "+faststart", final])
    size = os.path.getsize(final) / 1e6
    log(f"Render selesai: {total:.0f} detik, {size:.1f} MB")
    with open(final, "rb") as f:
        r = requests.post(f"{W}/render/upload", headers={**H, "x-job": JOB, "content-type": "video/mp4"}, data=f, timeout=300)
    if not r.ok: raise RuntimeError(f"Upload gagal {r.status_code}: {r.text[:300]}")

if __name__ == "__main__":
    try: main()
    except Exception as e:
        log(f"❌ Render gagal: {e}"); sys.exit(1)
