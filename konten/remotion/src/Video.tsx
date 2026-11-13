import React from "react";
import { AbsoluteFill, Audio, Img, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig, Easing } from "remotion";

type Cap = { from: number; to: number; text: string };
type Scene = { img: string; audio: string; frames: number; caps: Cap[] };
export type VideoProps = { judul: string; scenes: Scene[] };

const FADE = 12;

const Pic: React.FC<{ src: string; frames: number; i: number }> = ({ src, frames, i }) => {
  const f = useCurrentFrame();
  const p = interpolate(f, [0, frames + FADE], [0, 1], { extrapolateRight: "clamp", easing: Easing.inOut(Easing.quad) });
  const zoomIn = i % 2 === 0;
  const scale = zoomIn ? 1.04 + 0.1 * p : 1.14 - 0.1 * p;
  const dir = [[-1, 0], [1, 0], [0, -1], [0, 1]][i % 4];
  const tx = dir[0] * 30 * (p - 0.5), ty = dir[1] * 40 * (p - 0.5);
  const op = interpolate(f, [0, FADE], [0, 1], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ opacity: i === 0 ? 1 : op, overflow: "hidden", backgroundColor: "black" }}>
      <Img src={staticFile(src)} style={{ width: "100%", height: "100%", objectFit: "cover",
        transform: `translate(${tx}px, ${ty}px) scale(${scale})`, willChange: "transform" }} />
      <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(0,0,0,0) 55%, rgba(0,0,0,.55) 100%)" }} />
    </AbsoluteFill>
  );
};

const Caption: React.FC<{ text: string }> = ({ text }) => {
  const f = useCurrentFrame(); const { fps } = useVideoConfig();
  const words = text.split(" ");
  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: 230 }}>
      <div style={{ maxWidth: 640, textAlign: "center", lineHeight: 1.25 }}>
        {words.map((w, k) => {
          const s = spring({ frame: f - k * 3, fps, config: { damping: 12, stiffness: 180 } });
          return (
            <span key={k} style={{ display: "inline-block", margin: "0 8px", fontFamily: "sans-serif", fontWeight: 900,
              fontSize: 54, color: k === words.length - 1 ? "#fde047" : "white",
              WebkitTextStroke: "2px black", textShadow: "0 4px 14px rgba(0,0,0,.7)",
              transform: `translateY(${(1 - s) * 30}px) scale(${0.7 + 0.3 * s})`, opacity: s }}>{w}</span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

const Title: React.FC<{ text: string }> = ({ text }) => {
  const f = useCurrentFrame(); const { fps } = useVideoConfig();
  const s = spring({ frame: f, fps, config: { damping: 14 } });
  const out = interpolate(f, [55, 70], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ justifyContent: "flex-start", alignItems: "center", paddingTop: 170 }}>
      <div style={{ background: "#7c3aed", color: "white", fontFamily: "sans-serif", fontWeight: 900, fontSize: 46,
        padding: "16px 28px", borderRadius: 18, maxWidth: 620, textAlign: "center", opacity: s * out,
        transform: `scale(${0.6 + 0.4 * s}) rotate(${(1 - s) * -6}deg)`, boxShadow: "0 10px 30px rgba(0,0,0,.4)" }}>{text}</div>
    </AbsoluteFill>
  );
};

export const Video: React.FC<VideoProps> = ({ judul, scenes }) => {
  let start = 0;
  return (
    <AbsoluteFill style={{ backgroundColor: "black" }}>
      {scenes.map((sc, i) => {
        const from = start; start += sc.frames;
        return (
          <Sequence key={i} from={from} durationInFrames={sc.frames + (i < scenes.length - 1 ? FADE : 0)}>
            <Pic src={sc.img} frames={sc.frames} i={i} />
            <Sequence durationInFrames={sc.frames}><Audio src={staticFile(sc.audio)} /></Sequence>
            {sc.caps.map((c, j) => (
              <Sequence key={j} from={c.from} durationInFrames={Math.max(1, c.to - c.from)}><Caption text={c.text} /></Sequence>
            ))}
          </Sequence>
        );
      })}
      <Sequence durationInFrames={70}><Title text={judul} /></Sequence>
    </AbsoluteFill>
  );
};
