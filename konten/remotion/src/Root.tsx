import React from "react";
import { Composition } from "remotion";
import { Konten } from "./Konten";
export const Root: React.FC = () => (
  <Composition id="Konten" component={Konten as any} durationInFrames={900} fps={30} width={720} height={1280}
    defaultProps={{ judul: "Judul", baris: ["Baris satu", "Baris dua"] }} />
);
