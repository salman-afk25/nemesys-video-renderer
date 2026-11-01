"""NEMESYS Animation Studio - render episode anime 60 detik (9:16) gratis di GitHub Actions.
Fitur: 2 shot per adegan, gerak kamera bervariasi, guncangan untuk adegan dramatis, crossfade,
color grading anime, grain + vignette, musik latar sintetis, dialog multi-suara, subtitle berlabel."""
import asyncio, json, os, re, subprocess, sys, math
import requests, edge_tts
from num2words import num2words

W = os.environ["WORKER_URL"].rstrip("/")
H = {"x-nemesys-key": os.environ["RENDER_SECRET"], "user-agent": "nemesys-renderer"}
JOB = os.environ["JOB_ID"]
OUT = "out"; os.makedirs(OUT, exist_ok=True)
WIDTH, HEIGHT, FPS, TARGET, XF = 720, 1280, 25, 60.0, 0.35

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
    h, r = divmod(max(t, 0), 3600); m, s = divmod(r, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"

ABBR = {"dll": "dan lain-lain", "dsb": "dan sebagainya", "yg": "yang", "tdk": "tidak", "km": "kilometer", "kg": "kilogram", "%": " persen"}
def speakable(t):
    """Teks untuk diucapkan: angka jadi huruf, singkatan dibuka, simbol dibersihkan."""
    t = re.sub(r"[\"“”*_#~`]|[\U0001F300-\U0001FAFF\u2600-\u27BF]", "", t)
    t = t.replace("—", ", ").replace("–", ", ").replace("...", ", ").replace("…", ", ")
    t = re.sub(r"(\d+)%", lambda m: m.group(1) + " persen", t)
    t = re.sub(r"\d+", lambda m: num2words(int(m.group()), lang="id"), t)
    for k, v in ABBR.items(): t = re.sub(rf"\b{re.escape(k)}\b", v, t, flags=re.I)
    return re.sub(r"\s+", " ", t).strip()

def readable(t):
    return re.sub(r"\s+", " ", re.sub(r"[\"“”*_#~`]", "", t)).strip()

class QuotaError(Exception): pass
IMG = {"local": False, "pipe": None}
def local_img(prompt, path):
    """Cadangan gratis tanpa kuota: SD-Turbo di CPU runner GitHub."""
    if IMG["pipe"] is None:
        import torch
        from diffusers import AutoPipelineForText2Image
        torch.set_num_threads(os.cpu_count() or 4)
        IMG["pipe"] = AutoPipelineForText2Image.from_pretrained("stabilityai/sd-turbo", torch_dtype=torch.float32)
        IMG["pipe"].set_progress_bar_config(disable=True)
    short = prompt[:300]
    im = IMG["pipe"](prompt=f"anime key visual, cel shading, {short}", num_inference_steps=2, guidance_scale=0.0, width=512, height=896).images[0]
    im = im.resize((768, 1344))
    im.save(path, quality=92)

def get_img(prompt, path):
    if not IMG["local"]:
        for attempt in range(3):
            r = requests.post(f"{W}/render/img", headers=H, json={"prompt": prompt}, timeout=120)
            if r.ok and len(r.content) > 5000:
                open(path, "wb").write(r.content); return
            if "4006" in r.text:
                IMG["local"] = True
                log("ℹ️ Kuota gambar Cloudflare habis, beralih ke pembuat gambar lokal (SD-Turbo)")
                break
        else:
            raise RuntimeError(f"Gagal membuat gambar: {r.status_code} {r.text[:200]}")
    local_img(prompt, path)

MOVES = ["zoomin", "panright", "zoomout", "panup", "panleft", "zoomin_slow"]
def shot(img, d, move, dramatic, out):
    frames = int(math.ceil(d * FPS)) + 2
    S = 1.25  # ruang gerak kamera
    big_w, big_h = int(WIDTH * S), int(HEIGHT * S)
    p = f"(on/{frames})"
    if move == "zoomin": z, x, y = f"1+0.18*{p}", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    elif move == "zoomin_slow": z, x, y = f"1.05+0.10*{p}", "iw/2-(iw/zoom/2)", "ih/3-(ih/zoom/3)"
    elif move == "zoomout": z, x, y = f"1.2-0.18*{p}", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    elif move == "panright": z, x, y = "1.12", f"(iw-iw/zoom)*{p}", "ih/2-(ih/zoom/2)"
    elif move == "panleft": z, x, y = "1.12", f"(iw-iw/zoom)*(1-{p})", "ih/2-(ih/zoom/2)"
    else: z, x, y = "1.12", "iw/2-(iw/zoom/2)", f"(ih-ih/zoom)*(1-{p})"
    if dramatic:  # guncangan kamera
        x = f"({x})+8*sin(on*1.9)"; y = f"({y})+6*cos(on*2.3)"
        z = f"({z})+0.04"
    vf = (f"scale={big_w}:{big_h}:force_original_aspect_ratio=increase,crop={big_w}:{big_h},"
          f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={WIDTH}x{HEIGHT}:fps={FPS},"
          "eq=saturation=1.18:contrast=1.06:brightness=0.01,"
          "colorbalance=rs=0.03:bs=0.04:rh=0.04:bh=-0.03,"
          "vignette=PI/5,noise=alls=5:allf=t,format=yuv420p")
    if dramatic: vf = vf.replace("eq=saturation=1.18", "eq=saturation=1.05:contrast=1.15")
    run(["ffmpeg", "-y", "-loop", "1", "-i", img, "-vf", vf, "-t", f"{d:.3f}", "-r", str(FPS),
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-an", out])

def music(mood, out):
    """Musik latar sintetis lembut: pad akord + reverb."""
    if mood == "dramatis":
        chords = [(110.0, 130.81, 164.81), (87.31, 110.0, 130.81), (98.0, 123.47, 146.83), (82.41, 103.83, 123.47)]
    else:
        chords = [(130.81, 164.81, 196.0), (110.0, 130.81, 164.81), (87.31, 110.0, 130.81), (98.0, 123.47, 146.83)]
    seg = 7.5; parts = []
    for k in range(int(TARGET / seg) + 1):
        a, b, c = chords[k % 4]; t0 = k * seg
        parts.append(f"(between(t,{t0},{t0+seg}))*(sin(2*PI*{a}*t)+0.7*sin(2*PI*{b}*t)+0.6*sin(2*PI*{c}*t)+0.3*sin(2*PI*{a/2}*t))")
    expr = "0.12*(" + "+".join(parts) + ")*(0.75+0.25*sin(2*PI*0.25*t))"
    run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"aevalsrc='{expr}':s=44100:d={TARGET}",
         "-af", "lowpass=f=1400,aecho=0.8:0.85:120|260:0.35|0.25,afade=t=in:d=2,afade=t=out:st=57:d=3,volume=0.55",
         "-ac", "2", out])

def main():
    r = requests.get(f"{W}/render/job/{JOB}", headers=H, timeout=30)
    try: job = r.json()
    except Exception: raise RuntimeError(f"Ambil job gagal {r.status_code}: {r.text[:300]}")
    story = job["story"]; scenes = story["scenes"][:10]; n = len(scenes)
    style = story.get("gaya_visual", "")
    voices = story.get("voices", {})
    mood = story.get("mood", "tenang")

    # 1) gambar: shot lebar + close-up
    for i, sc in enumerate(scenes):
        get_img(f"{sc['prompt_gambar']}, {style}", f"{OUT}/a{i}.jpg")
        if sc.get("prompt_close") and (sc.get("efek") == "dramatis" or i in (0, n - 1)): get_img(f"{sc['prompt_close']}, {style}", f"{OUT}/b{i}.jpg")
    log(f"Gambar selesai untuk {n} adegan")

    # 2) suara: Gemini TTS (gratis) → cadangan edge-tts
    state = {"gemini": True}
    def gemini_tts(text, v, style, path):
        if not state["gemini"] or not v.get("gemini"): return False
        st = ", ".join(x for x in [v.get("gaya", ""), style] if x)
        for attempt in range(3):
            try:
                r = requests.post(f"{W}/render/tts", headers=H, json={"text": text, "voice": v["gemini"], "style": st}, timeout=90)
                if r.ok and len(r.content) > 2000:
                    open(path + ".wav", "wb").write(r.content)
                    run(["ffmpeg", "-y", "-i", path + ".wav", "-af", "silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse", "-ar", "44100", path])
                    return True
                if r.status_code in (429, 503): import time; time.sleep(6 * (attempt + 1)); continue
                break
            except Exception: pass
        state["gemini"] = False
        log("ℹ️ Suara Gemini tidak tersedia, beralih ke suara cadangan")
        return False
    used = {"gemini": 0, "edge": 0}
    raw = []
    for i, sc in enumerate(scenes):
        v = voices.get(sc.get("suara", ""), {"voice": "id-ID-GadisNeural", "pitch": "+0Hz", "rate": 0})
        path = f"{OUT}/r{i}.mp3"; txt = speakable(sc["narasi"])
        if gemini_tts(txt, v, sc.get("gaya_suara", ""), path): used["gemini"] += 1
        else:
            asyncio.run(edge_tts.Communicate(txt, v.get("voice", "id-ID-GadisNeural"), rate=f"{int(v.get('rate', 0)):+d}%", pitch=v.get("pitch", "+0Hz")).save(path)); used["edge"] += 1
        raw.append(dur(path))
    total = sum(raw) + 0.5 * n
    tempo = 1.0
    if total > 57.5: tempo = min(1.2, total / 56.5)
    elif total < 45: tempo = max(0.9, total / 48.0)
    ds = []
    for i in range(n):
        run(["ffmpeg", "-y", "-i", f"{OUT}/r{i}.mp3", "-af", f"atempo={tempo:.3f}", "-ar", "44100", f"{OUT}/v{i}.mp3"])
        ds.append(dur(f"{OUT}/v{i}.mp3"))
    rate = int(round((tempo - 1) * 100))
    if sum(ds) > TARGET - 2:
        raise RuntimeError(f"Dialog terlalu panjang ({sum(ds):.1f} dtk) walau sudah dipercepat")
    log(f"Suara: {used['gemini']} baris Gemini, {used['edge']} baris cadangan")
    gap = (TARGET - sum(ds)) / n
    durs = [d + gap for d in ds]; durs[-1] = TARGET - sum(durs[:-1])
    log(f"Suara {sum(ds):.1f} dtk (penyesuaian kecepatan {rate:+d}%), total {TARGET:.0f} dtk")

    # 3) trek suara utuh 60 detik
    lead = min(0.35, gap / 2); inputs, filt, t = [], [], 0.0
    for i in range(n):
        inputs += ["-i", f"{OUT}/v{i}.mp3"]
        filt.append(f"[{i}:a]aresample=44100,adelay={int((t+lead)*1000)}:all=1[a{i}]"); t += durs[i]
    filt.append("".join(f"[a{i}]" for i in range(n)) + f"amix=inputs={n}:normalize=0,apad,atrim=0:{TARGET},"
                "highpass=f=70,acompressor=threshold=-18dB:ratio=3:attack=5:release=120,loudnorm=I=-15:TP=-1.5[v]")
    run(["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(filt), "-map", "[v]", "-ac", "2", f"{OUT}/voice.wav"])
    music(mood, f"{OUT}/music.wav")
    run(["ffmpeg", "-y", "-i", f"{OUT}/voice.wav", "-i", f"{OUT}/music.wav", "-filter_complex",
         "[1:a]volume=0.22[m];[m][0:a]sidechaincompress=threshold=0.05:ratio=6:attack=20:release=300[md];[0:a][md]amix=inputs=2:normalize=0[out]",
         "-map", "[out]", "-t", str(TARGET), "-c:a", "aac", "-b:a", "128k", f"{OUT}/audio.m4a"])

    # 4) shot video + crossfade
    shots, k, subs, t = [], 0, [], 0.0
    for i, sc in enumerate(scenes):
        dramatic = sc.get("efek") == "dramatis"
        has_b = os.path.exists(f"{OUT}/b{i}.jpg")
        parts = [(f"{OUT}/a{i}.jpg", durs[i] * (0.55 if has_b else 1.0))]
        if has_b: parts.append((f"{OUT}/b{i}.jpg", durs[i] * 0.45))
        for img, d in parts:
            out = f"{OUT}/s{len(shots)}.mp4"
            shot(img, d + XF, MOVES[k % len(MOVES)], dramatic, out); shots.append((out, d)); k += 1
        lab = sc.get("label", ""); words = readable(sc["narasi"]).split()
        chunks = [" ".join(words[j:j+7]) for j in range(0, len(words), 7)] or [""]
        per = ds[i] / len(chunks)
        for j, c in enumerate(chunks):
            pre = f"{{\\c&H0000D7FF&}}{lab}{{\\c&H00FFFFFF&}}\\N" if lab else ""
            subs.append((t + lead + j*per, t + lead + (j+1)*per, pre + c))
        t += durs[i]
    log(f"{len(shots)} shot kamera selesai")
    inp = []; [inp.extend(["-i", s]) for s, _ in shots]
    fc, prev, off = [], "[0:v]", 0.0
    for j in range(1, len(shots)):
        off += shots[j-1][1]
        trans = "fadeblack" if scenes and j % 5 == 0 else "fade"
        fc.append(f"{prev}[{j}:v]xfade=transition={trans}:duration={XF}:offset={off:.3f}[x{j}]"); prev = f"[x{j}]"
    run(["ffmpeg", "-y", *inp, "-filter_complex", ";".join(fc) if fc else "[0:v]null[x0]", "-map", prev if fc else "[x0]",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", f"{OUT}/joined.mp4"])

    # 5) subtitle, judul, watermark
    ass = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {WIDTH}", f"PlayResY: {HEIGHT}", "",
           "[V4+ Styles]", "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV",
           "Style: Sub,DejaVu Sans,34,&H00FFFFFF,&H00000000,&H64000000,1,1,3,1,2,50,50,175",
           "Style: Studio,DejaVu Sans,20,&H99FFFFFF,&H00000000,&H00000000,1,1,1,0,9,20,24,24",
           "Style: Judul,DejaVu Sans,46,&H0000D7FF,&H00000000,&H80000000,1,1,4,2,5,40,40,40",
           "Style: Seri,DejaVu Sans,26,&H00FFFFFF,&H00000000,&H80000000,1,1,2,1,5,40,40,40", "",
           "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    title = story.get("judul", ""); seri, _, ep = title.partition(" — ")
    ass.append(f"Dialogue: 1,{ts(0.2)},{ts(3.6)},Seri,,0,0,0,,{{\\fad(400,400)\\pos(360,560)}}{seri}")
    ass.append(f"Dialogue: 1,{ts(0.4)},{ts(3.6)},Judul,,0,0,0,,{{\\fad(400,400)\\pos(360,640)}}{(ep or title)}")
    ass.append(f"Dialogue: 0,{ts(0)},{ts(TARGET)},Studio,,0,0,0,,{story.get('studio','')}")
    for a, b, c in subs: ass.append(f"Dialogue: 0,{ts(a)},{ts(b)},Sub,,0,0,0,,{{\\fad(120,120)}}{c}")
    open(f"{OUT}/sub.ass", "w").write("\n".join(ass))
    final = f"{OUT}/video.mp4"
    vbit = int((9.2 * 8 * 1024) / TARGET - 135)
    run(["ffmpeg", "-y", "-i", f"{OUT}/joined.mp4", "-i", f"{OUT}/audio.m4a",
         "-vf", f"subtitles={OUT}/sub.ass,tpad=stop_mode=clone:stop_duration=1", "-map", "0:v", "-map", "1:a",
         "-t", str(TARGET), "-c:v", "libx264", "-preset", "medium", "-b:v", f"{vbit}k", "-maxrate", f"{vbit}k",
         "-bufsize", f"{vbit*2}k", "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.0", "-c:a", "copy", "-movflags", "+faststart", final])
    log(f"Render selesai: {dur(final):.2f} detik, {os.path.getsize(final)/1e6:.1f} MB")
    with open(final, "rb") as f:
        r = requests.post(f"{W}/render/upload", headers={**H, "x-job": JOB, "content-type": "video/mp4"}, data=f, timeout=300)
    if not r.ok: raise RuntimeError(f"Upload gagal {r.status_code}: {r.text[:300]}")

if __name__ == "__main__":
    try: main()
    except QuotaError:
        log("⏸️ Kuota gambar AI harian habis. Render otomatis dilanjutkan setelah kuota reset pukul 07.10 WIB.")
        try: requests.post(f"{W}/render/wait", headers=H, json={"job": JOB}, timeout=20)
        except Exception: pass
        sys.exit(0)
    except Exception as e:
        log(f"❌ Render gagal: {e}"); sys.exit(1)
