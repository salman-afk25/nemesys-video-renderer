import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig, Sequence } from "remotion";
const COLORS = ["#7c3aed", "#db2777", "#0ea5e9", "#f59e0b", "#10b981"];
const Line: React.FC<{ text: string; i: number }> = ({ text, i }) => {
  const f = useCurrentFrame(); const { fps } = useVideoConfig();
  const s = spring({ frame: f, fps, config: { damping: 14 } });
  const out = interpolate(f, [60, 75], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", padding: 60 }}>
      <div style={{ fontSize: 64, fontWeight: 800, color: "white", textAlign: "center", fontFamily: "sans-serif",
        transform: `translateY(${(1 - s) * 120}px) scale(${0.8 + 0.2 * s})`, opacity: s * out,
        textShadow: "0 6px 30px rgba(0,0,0,.4)" }}>
        <span style={{ display: "block", fontSize: 40, opacity: 0.8, marginBottom: 16 }}>{i + 1}</span>{text}
      </div>
    </AbsoluteFill>);
};
export const Konten: React.FC<{ judul: string; baris: string[] }> = ({ judul, baris }) => {
  const f = useCurrentFrame(); const { fps } = useVideoConfig();
  const bgIdx = Math.floor(f / 75) % COLORS.length;
  const t = spring({ frame: f, fps, config: { damping: 12 } });
  const tOut = interpolate(f, [75, 90], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ background: `linear-gradient(160deg, ${COLORS[bgIdx]}, #111827)` }}>
      <Sequence durationInFrames={90}>
        <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", padding: 60 }}>
          <div style={{ fontSize: 84, fontWeight: 900, color: "white", textAlign: "center", fontFamily: "sans-serif",
            transform: `scale(${t})`, opacity: tOut }}>{judul}</div>
        </AbsoluteFill>
      </Sequence>
      {baris.map((b, i) => (
        <Sequence key={i} from={90 + i * 75} durationInFrames={75}><Line text={b} i={i} /></Sequence>))}
      <Sequence from={90 + baris.length * 75}>
        <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
          <div style={{ fontSize: 56, color: "white", fontFamily: "sans-serif", fontWeight: 700 }}>✨ Selesai ✨</div>
        </AbsoluteFill>
      </Sequence>
    </AbsoluteFill>);
};
