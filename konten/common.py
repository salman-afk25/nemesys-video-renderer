"""Konten Bot renderer: video (gaya MoneyPrinterTurbo), clip (gaya AutoClip), render (Remotion)."""
import asyncio, json, os, re, subprocess, sys, glob
import requests, edge_tts

API = os.environ["API"].rstrip("/"); JOB = os.environ["JOB_ID"]; KEY = os.environ["JOB_KEY"]
def u(op, **q):
    qs = "&".join(f"{k}={requests.utils.quote(str(v))}" for k, v in q.items())
    return f"{API}/a/{op}/{JOB}?k={KEY}" + (f"&{qs}" if qs else "")
def run(cmd, cwd=None):
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    if r.returncode != 0: raise RuntimeError((r.stderr or r.stdout)[-800:])
    return r.stdout
def dur(p): return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p]).strip())
def ts(t):
    h, r = divmod(max(t, 0), 3600); m, s = divmod(r, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"
def send(path, cap):
    size = os.path.getsize(path)
    if size > 48 * 1024 * 1024: raise RuntimeError(f"file terlalu besar ({size//1048576} MB)")
    r = requests.post(u("done", cap=cap), data=open(path, "rb"), headers={"content-type": "video/mp4"}, timeout=300)
    if not r.ok: raise RuntimeError(f"kirim gagal {r.status_code} {r.text[:200]}")
def llm(system, user, mx=600):
    return requests.post(u("llm"), json={"system": system, "user": user, "max": mx}, timeout=120).json()["text"]
def pjson(t):
    m = re.search(r"[\[{][\s\S]*[\]}]", t.replace("```json", "").replace("```", ""))
    return json.loads(m.group(0) if m else t)
W, H, FPS = 720, 1280, 25
STYLE = "FontName=DejaVu Sans,Fontsize=13,Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=0,Alignment=2,MarginV=70"

# ---------- video ----------
async def tts(text, out):
    await edge_tts.Communicate(text, "id-ID-ArdiNeural", rate="+8%").save(out)

def pexels(q):
    try:
        r = requests.get(u("pexels", q=q), timeout=30)
        return r.json().get("videos") or [] if r.ok else []
    except Exception: return []

used = set()
def stock(q, out, need):
    for query in [q, " ".join(q.split()[:2]), q.split()[0] if q.split() else ""]:
        if not query: continue
        for v in pexels(query):
            if v["id"] in used or v.get("dur", 0) < 3: continue
            try:
                with requests.get(v["link"], stream=True, timeout=120) as r:
                    r.raise_for_status()
                    with open(out, "wb") as f:
                        for ch in r.iter_content(1 << 20): f.write(ch)
                used.add(v["id"]); return True
            except Exception: continue
    return False

def ai_img(prompt, img):
    for _ in range(3):
        r = requests.post(u("img"), json={"prompt": prompt + ", vertical composition, high detail"}, timeout=120)
        if r.ok and len(r.content) > 5000: open(img, "wb").write(r.content); return
    raise RuntimeError(f"gambar gagal: {r.status_code}")

def video():
    job = requests.get(u("job"), timeout=30).json()
    scenes = job["adegan"][:8]; os.makedirs("o", exist_ok=True)
    clips, subs, t, nstock = [], [], 0.0, 0
    for i, s in enumerate(scenes):
        img = f"o/{i}.jpg"; aud = f"o/{i}.mp3"; vid = f"o/{i}.mp4"; src = f"o/s{i}.mp4"
        asyncio.run(tts(s["narasi"], aud))
        d = dur(aud) + 0.35
        enc = ["-t", f"{d:.2f}", "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-c:a", "aac", "-ar", "44100", "-ac", "2", vid]
        if stock(s.get("cari") or s["gambar"], src, d):
            nstock += 1
            run(["ffmpeg", "-y", "-stream_loop", "-1", "-i", src, "-i", aud, "-filter_complex",
                 f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H},fps={FPS},format=yuv420p[v];[1]apad=pad_dur=0.35[a]",
                 "-map", "[v]", "-map", "[a]"] + enc)
        else:
            ai_img(s["gambar"], img)
            fr = int(d * FPS) + 2
            # zoom halus: perbesar gambar 3x dulu supaya tidak goyang
            z = "1+0.10*on/%d" % fr if i % 2 == 0 else "1.10-0.10*on/%d" % fr
            run(["ffmpeg", "-y", "-loop", "1", "-i", img, "-i", aud, "-filter_complex",
                 f"[0]scale=2160:3840:force_original_aspect_ratio=increase:flags=lanczos,crop=2160:3840,zoompan=z='{z}':x='trunc(iw/2-(iw/zoom/2))':y='trunc(ih/2-(ih/zoom/2))':d={fr}:s={W}x{H}:fps={FPS},format=yuv420p[v];[1]apad=pad_dur=0.35[a]",
                 "-map", "[v]", "-map", "[a]"] + enc)
        words = s["narasi"].split()
        chunks = [" ".join(words[k:k+5]) for k in range(0, len(words), 5)] or [""]
        per = (d - 0.35) / len(chunks)
        for j, c in enumerate(chunks): subs.append((t + j*per, t + (j+1)*per, c))
        clips.append(vid); t += d
    open("o/list.txt", "w").write("".join(f"file '{os.path.basename(c)}'\n" for c in clips))
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "o/list.txt", "-c", "copy", "o/cat.mp4"])
    ass = "[Script Info]\nScriptType: v4.00+\nPlayResX: 360\nPlayResY: 640\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BorderStyle, Outline, Shadow, Alignment, MarginV, Bold\n" \
          "Style: D,DejaVu Sans,17,&H00FFFFFF,&H00000000,1,2,0,2,60,1\n\n[Events]\nFormat: Layer, Start, End, Style, Text\n"
    ass += "".join(f"Dialogue: 0,{ts(a)},{ts(b)},D,{c}\n" for a, b, c in subs)
    open("o/s.ass", "w").write(ass)
    run(["ffmpeg", "-y", "-i", "o/cat.mp4", "-vf", "ass=o/s.ass", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-c:a", "copy", "-movflags", "+faststart", "o/final.mp4"])
    cred = "\n📹 Video stok: Pexels" if nstock else ""
    send("o/final.mp4", f"🎬 {job.get('judul','Video')}{cred}")

# ---------- clip ----------
def vtt_text(path):
    out, last = [], ""
    for blk in open(path, encoding="utf-8").read().split("\n\n"):
        m = re.search(r"(\d+):(\d+):(\d+)\.\d+ -->", blk)
        if not m: continue
        sec = int(m.group(1))*3600 + int(m.group(2))*60 + int(m.group(3))
        txt = re.sub(r"<[^>]+>", "", " ".join(l for l in blk.splitlines() if "-->" not in l)).strip()
        if txt and txt != last: out.append(f"[{sec}] {txt}"); last = txt
    return out

def clip():
    job = requests.get(u("job"), timeout=30).json(); url = job["url"]; os.makedirs("o", exist_ok=True)
    base = ["yt-dlp", "--no-playlist", "--extractor-args", "youtube:player_client=web_safari,android,tv", "-o", "o/src.%(ext)s"]
    run(base + ["--skip-download", "--write-auto-subs", "--write-subs", "--sub-langs", "id.*,en.*", "--sub-format", "vtt", "--print-to-file", "%(duration)s|%(title)s", "o/meta.txt", url])
    meta = open("o/meta.txt").read().strip().split("|", 1); total = float(meta[0] or 0); title = meta[1] if len(meta) > 1 else ""
    subs = glob.glob("o/*.vtt")
    if subs:
        lines = vtt_text(subs[0]); trans = "\n".join(lines)[:14000]
        raw = llm("Kamu editor video viral (seperti AutoClip). Pilih SATU segmen paling menarik/lucu/informatif berdurasi 30-60 detik dari transkrip bertimestamp detik. Jawab HANYA JSON.",
                  f"Judul video: {title}\nTranskrip:\n{trans}\n\nFormat: {{\"start\":detik,\"end\":detik,\"judul\":\"judul klip singkat menarik\"}}")
        try:
            pick = pjson(raw); st = float(pick["start"]); en = float(pick["end"]); jud = pick.get("judul") or title
        except Exception:
            st, en, jud = 0, 60, title
    else:
        st, en, jud = max(0, total*0.3), max(0, total*0.3) + 45, title
    if en - st < 15 or en - st > 75: en = st + 50
    if total: en = min(en, total)
    run(base + ["-f", "bv*[height<=720][ext=mp4]+ba[ext=m4a]/b[height<=720]/b", "--download-sections", f"*{st}-{en}", "--force-keyframes-at-cuts", "--merge-output-format", "mp4", url])
    src = [f for f in glob.glob("o/src.*") if f.endswith((".mp4", ".mkv", ".webm"))][0]
    run(["ffmpeg", "-y", "-i", src, "-filter_complex",
         f"[0:v]split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=20:2[bg];[b]scale={W}:-2[fg];[bg][fg]overlay=0:(H-h)/2,format=yuv420p[v]",
         "-map", "[v]", "-map", "0:a?", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-c:a", "aac", "-movflags", "+faststart", "o/final.mp4"])
    send("o/final.mp4", f"✂️ {jud}\n⏱ {int(st)//60}:{int(st)%60:02d}–{int(en)//60}:{int(en)%60:02d}\n{url}")

# ---------- render (Remotion) ----------
def render():
    job = requests.get(u("job"), timeout=30).json()
    props = {"judul": job.get("judul") or "", "baris": job.get("baris") or []}
    os.makedirs("o", exist_ok=True)
    frames = 90 + 75 * max(1, len(props["baris"])) + 45
    run(["npx", "remotion", "render", "src/index.ts", "Konten", "../../o/final.mp4", f"--props={json.dumps(props)}", f"--frames=0-{frames-1}", "--log=error"], cwd="konten/remotion")
    send("o/final.mp4", f"🎞️ {props['judul']}")

if __name__ == "__main__":
    try: {"video": video, "clip": clip, "render": render}[sys.argv[1]]()
    except Exception as e:
        print(e)
        try: requests.post(u("fail"), json={"msg": str(e)[-400:]}, timeout=30)
        except Exception: pass
        sys.exit(1)
