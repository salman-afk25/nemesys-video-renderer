import React from "react";
import { AbsoluteFill, Audio, Img, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig, Easing, random } from "remotion";

type Cap = { from: number; to: number; text: string };
type Scene = { img: string; audio: string; frames: number; caps: Cap[] };
export type VideoProps = { judul: string; scenes: Scene[] };

const FADE = 14;
const ACC = ["#fde047", "#f472b6", "#38bdf8", "#4ade80", "#fb923c", "#c084fc"];
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

// 6 gerakan kamera berbeda
const motion = (i: number, p: number) => {
  switch (i % 6) {
    case 0: return { s: 1.05 + 0.12 * p, x: 0, y: 0, r: 0 };                 // zoom in
    case 1: return { s: 1.17 - 0.12 * p, x: 0, y: 0, r: 0 };                 // zoom out
    case 2: return { s: 1.15, x: -45 + 90 * p, y: 0, r: 0 };                 // geser kanan
    case 3: return { s: 1.15, x: 0, y: 50 - 100 * p, r: 0 };                 // geser atas
    case 4: return { s: 1.08 + 0.08 * p, x: 0, y: 0, r: -1.5 + 3 * p };      // zoom + putar
    default: return { s: 1.15, x: 45 - 90 * p, y: -30 + 60 * p, r: 0 };      // diagonal
  }
};

// 5 transisi masuk berbeda
const enter = (i: number, f: number, w: number) => {
  const t = interpolate(f, [0, FADE], [0, 1], { ...clamp, easing: Easing.out(Easing.cubic) });
  if (i === 0) return { opacity: 1 };
  switch (i % 5) {
    case 0: return { opacity: t };
    case 1: return { transform: `translateX(${(1 - t) * w}px)` };
    case 2: return { transform: `translateY(${(1 - t) * -1280}px)` };
    case 3: return { transform: `scale(${0.4 + 0.6 * t})`, opacity: t, borderRadius: (1 - t) * 80 };
    default: return { clipPath: `circle(${t * 120}% at 50% 50%)` };
  }
};

const Pic: React.FC<{ src: string; frames: number; i: number }> = ({ src, frames, i }) => {
  const f = useCurrentFrame(); const { width } = useVideoConfig();
  const p = interpolate(f, [0, frames + FADE], [0, 1], { ...clamp, easing: Easing.inOut(Easing.quad) });
  const m = motion(i, p);
  const flash = i > 0 ? interpolate(f, [FADE - 4, FADE, FADE + 6], [0, 0.35, 0], clamp) : 0;
  return (
    <AbsoluteFill style={{ overflow: "hidden", backgroundColor: "black", ...enter(i, f, width) }}>
      <Img src={staticFile(src)} style={{ width: "100%", height: "100%", objectFit: "cover",
        transform: `translate(${m.x}px, ${m.y}px) scale(${m.s}) rotate(${m.r}deg)` }} />
      <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(0,0,0,.25) 0%, rgba(0,0,0,0) 30%, rgba(0,0,0,0) 55%, rgba(0,0,0,.6) 100%)" }} />
      <AbsoluteFill style={{ backgroundColor: "white", opacity: flash }} />
    </AbsoluteFill>
  );
};

// partikel berkilau melayang
const Sparkles: React.FC<{ seed: number }> = ({ seed }) => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {new Array(18).fill(0).map((_, k) => {
        const x = random(`x${seed}${k}`) * 720, sp = 0.6 + random(`s${seed}${k}`) * 1.6;
        const y = 1300 - ((f * sp * 2 + random(`y${seed}${k}`) * 1300) % 1400);
        const sz = 4 + random(`z${seed}${k}`) * 8;
        const tw = 0.3 + 0.7 * Math.abs(Math.sin((f + k * 7) / 9));
        return <div key={k} style={{ position: "absolute", left: x + Math.sin((f + k * 20) / 25) * 15, top: y, width: sz, height: sz,
          borderRadius: "50%", background: ACC[k % ACC.length], opacity: tw * 0.8, boxShadow: `0 0 ${sz * 2}px ${ACC[k % ACC.length]}` }} />;
      })}
    </AbsoluteFill>
  );
};

// 3 gaya teks bergantian
const Caption: React.FC<{ text: string; style: number }> = ({ text, style }) => {
  const f = useCurrentFrame(); const { fps } = useVideoConfig();
  const words = text.split(" ");
  const acc = ACC[style % ACC.length];
  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: 220 }}>
      <div style={{ maxWidth: 650, textAlign: "center", lineHeight: 1.3 }}>
        {words.map((w, k) => {
          const s = spring({ frame: f - k * 3, fps, config: { damping: 11, stiffness: 200 } });
          const active = f >= k * 5 && f < (k + 1) * 5 + 8;
          const kind = style % 3;
          const tr = kind === 0 ? `translateY(${(1 - s) * 40}px) scale(${0.6 + 0.4 * s})`
                   : kind === 1 ? `scale(${s}) rotate(${(1 - s) * -12}deg)`
                   : `translateX(${(1 - s) * -60}px)`;
          return (
            <span key={k} style={{ display: "inline-block", margin: "4px 7px", fontFamily: "sans-serif", fontWeight: 900, fontSize: 56,
              color: kind === 2 ? "black" : active ? acc : "white",
              background: kind === 2 ? (active ? acc : "white") : "transparent", padding: kind === 2 ? "2px 12px" : 0, borderRadius: 10,
              WebkitTextStroke: kind === 2 ? "0" : "2.5px black", textShadow: kind === 2 ? "none" : "0 4px 14px rgba(0,0,0,.8)",
              transform: tr, opacity: s }}>{w}</span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

const Title: React.FC<{ text: string }> = ({ text }) => {
  const f = useCurrentFrame(); const { fps } = useVideoConfig();
  const s = spring({ frame: f, fps, config: { damping: 10 } });
  const out = interpolate(f, [70, 85], [1, 0], clamp);
  const wob = Math.sin(f / 6) * 1.5;
  return (
    <AbsoluteFill style={{ justifyContent: "flex-start", alignItems: "center", paddingTop: 160 }}>
      <div style={{ background: "linear-gradient(135deg,#7c3aed,#db2777)", color: "white", fontFamily: "sans-serif", fontWeight: 900, fontSize: 48,
        padding: "18px 30px", borderRadius: 22, maxWidth: 640, textAlign: "center", opacity: s * out, border: "4px solid white",
        transform: `scale(${0.5 + 0.5 * s}) rotate(${(1 - s) * -10 + wob}deg)`, boxShadow: "0 12px 34px rgba(0,0,0,.5)" }}>{text}</div>
    </AbsoluteFill>
  );
};

const Badge: React.FC<{ n: number; total: number }> = ({ n, total }) => {
  const f = useCurrentFrame(); const { fps } = useVideoConfig();
  const s = spring({ frame: f - 4, fps, config: { damping: 9 } });
  return (
    <div style={{ position: "absolute", top: 70, right: 40, width: 92, height: 92, borderRadius: "50%", background: ACC[n % ACC.length],
      display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "sans-serif", fontWeight: 900, fontSize: 38,
      color: "black", border: "4px solid white", transform: `scale(${s}) rotate(${(1 - s) * 180}deg)`, boxShadow: "0 6px 20px rgba(0,0,0,.5)" }}>
      {n + 1}/{total}
    </div>
  );
};

const Progress: React.FC<{ total: number }> = ({ total }) => {
  const f = useCurrentFrame();
  return <div style={{ position: "absolute", top: 0, left: 0, height: 10, width: `${(f / total) * 100}%`,
    background: "linear-gradient(90deg,#fde047,#f472b6,#38bdf8)" }} />;
};

export const Video: React.FC<VideoProps> = ({ judul, scenes }) => {
  const total = scenes.reduce((a, s) => a + s.frames, 0) || 1;
  let start = 0;
  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      {scenes.map((sc, i) => {
        const from = start; start += sc.frames;
        return (
          <Sequence key={i} from={from} durationInFrames={sc.frames + (i < scenes.length - 1 ? FADE : 0)}>
            <Pic src={sc.img} frames={sc.frames} i={i} />
            <Sparkles seed={i} />
            {i > 0 && <Sequence from={FADE} durationInFrames={sc.frames}><Badge n={i} total={scenes.length} /></Sequence>}
            <Sequence durationInFrames={sc.frames}><Audio src={staticFile(sc.audio)} /></Sequence>
            {sc.caps.map((c, j) => (
              <Sequence key={j} from={c.from} durationInFrames={Math.max(1, c.to - c.from)}><Caption text={c.text} style={i} /></Sequence>
            ))}
          </Sequence>
        );
      })}
      <Sequence durationInFrames={85}><Title text={judul} /></Sequence>
      <Progress total={total} />
    </AbsoluteFill>
  );
};
