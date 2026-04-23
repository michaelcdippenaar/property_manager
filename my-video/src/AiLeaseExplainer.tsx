import React from "react";
import {
  AbsoluteFill,
  Easing,
  Img,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { TransitionSeries, springTiming } from "@remotion/transitions";
import { slide } from "@remotion/transitions/slide";

// ── Brand tokens ─────────────────────────────────────────────────────────────
const NAVY   = "#2B2D6E";
const ACCENT = "#FF3D7F";
const WHITE  = "#FFFFFF";
const FONT   = '"Bricolage Grotesque", "DM Sans", -apple-system, BlinkMacSystemFont, sans-serif';

// ── Timing ────────────────────────────────────────────────────────────────────
const S1    = 90;   // 3s  — hook
const S2    = 300;  // 10s — dashboard
const S3    = 300;  // 10s — lease builder
const S4    = 150;  // 5s  — CTA
const TRANS = 15;   // 0.5s

export const AI_LEASE_DURATION = S1 + S2 + S3 + S4 - TRANS * 3; // 825 frames = 27.5s

// ── Helpers ───────────────────────────────────────────────────────────────────
const enter = (frame: number, fps: number, delay = 0, damping = 16) =>
  spring({ frame, fps, delay, config: { damping, stiffness: 120 } });

const fade = (frame: number, from: number, to: number) =>
  interpolate(frame, [from, to], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

// ── Browser frame wrapper ─────────────────────────────────────────────────────
const BrowserFrame: React.FC<{
  src: string;
  url: string;
  rise: number;
  zoomScale?: number;
  zoomOriginY?: string;
}> = ({ src, url, rise, zoomScale = 1.06, zoomOriginY = "20%" }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const zoom = interpolate(frame, [0, 10 * fps], [1, zoomScale], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        width: "100%",
        borderRadius: 20,
        overflow: "hidden",
        boxShadow: "0 32px 80px rgba(0,0,0,0.35)",
        transform: `translateY(${(1 - rise) * 60}px) scale(${0.92 + rise * 0.08})`,
        opacity: rise,
        background: WHITE,
      }}
    >
      {/* Browser chrome */}
      <div
        style={{
          background: "#F0F0F5",
          padding: "14px 20px",
          display: "flex",
          alignItems: "center",
          gap: 12,
          borderBottom: "1px solid #E0E0EA",
        }}
      >
        {/* Traffic lights */}
        <div style={{ display: "flex", gap: 7 }}>
          {["#FF5F57", "#FFBD2E", "#28C840"].map((c) => (
            <div key={c} style={{ width: 14, height: 14, borderRadius: "50%", background: c }} />
          ))}
        </div>
        {/* URL bar */}
        <div
          style={{
            flex: 1,
            background: WHITE,
            borderRadius: 8,
            padding: "7px 16px",
            fontSize: 22,
            color: "#555",
            fontFamily: FONT,
            letterSpacing: "0.01em",
            display: "flex",
            alignItems: "center",
            gap: 8,
          }}
        >
          <span style={{ color: "#28C840", fontSize: 18 }}>🔒</span>
          <span style={{ color: NAVY, fontWeight: 600 }}>app.klikk.co.za</span>
          <span style={{ color: "#999" }}> / {url}</span>
        </div>
      </div>

      {/* Screenshot */}
      <div style={{ overflow: "hidden", maxHeight: 680 }}>
        <Img
          src={src}
          style={{
            width: "100%",
            display: "block",
            transform: `scale(${zoom})`,
            transformOrigin: `center ${zoomOriginY}`,
          }}
        />
      </div>
    </div>
  );
};

// ── Badge callout ─────────────────────────────────────────────────────────────
const Badge: React.FC<{ text: string; delay: number; accent?: boolean }> = ({
  text,
  delay,
  accent,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = enter(frame, fps, delay, 10);
  return (
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 10,
        background: accent ? ACCENT : NAVY,
        color: WHITE,
        padding: "14px 28px",
        borderRadius: 999,
        fontSize: 28,
        fontWeight: 700,
        transform: `scale(${s})`,
        opacity: s,
        whiteSpace: "nowrap",
        boxShadow: "0 8px 24px rgba(0,0,0,0.2)",
      }}
    >
      {text}
    </div>
  );
};

// ── Scene 1 — Hook ────────────────────────────────────────────────────────────
const Scene1_Hook: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const rise  = enter(frame, fps);
  const line2 = fade(frame, 15, 35);
  const barW  = interpolate(frame, [10, 30], [0, 200], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

  return (
    <AbsoluteFill
      style={{
        background: NAVY,
        fontFamily: FONT,
        alignItems: "center",
        justifyContent: "center",
        flexDirection: "column",
        gap: 24,
        padding: 80,
        display: "flex",
      }}
    >
      <div style={{ opacity: 0.5, color: WHITE, fontSize: 28, fontWeight: 800, letterSpacing: "0.3em" }}>
        KLIKK
      </div>
      <div
        style={{
          color: WHITE,
          fontSize: 88,
          fontWeight: 900,
          lineHeight: 1.05,
          textAlign: "center",
          letterSpacing: "-0.02em",
          transform: `translateY(${(1 - rise) * 40}px)`,
          opacity: rise,
        }}
      >
        Rental management
        <br />
        that actually works.
      </div>
      <div style={{ width: barW, height: 7, background: ACCENT, borderRadius: 4 }} />
      <div
        style={{
          color: WHITE,
          fontSize: 38,
          fontWeight: 500,
          opacity: line2 * 0.75,
          textAlign: "center",
        }}
      >
        AI-native. SA-built. Free for 5 properties.
      </div>
    </AbsoluteFill>
  );
};

// ── Scene 2 — Dashboard ───────────────────────────────────────────────────────
const Scene2_Dashboard: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const bg  = fade(frame, 0, 10);
  const rise = enter(frame, fps, 5);
  const cap  = fade(frame, 20, 45);

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(160deg, ${NAVY} 0%, #1a1c52 100%)`,
        fontFamily: FONT,
        padding: 60,
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        gap: 36,
        opacity: bg,
      }}
    >
      {/* Caption above */}
      <div
        style={{
          opacity: cap,
          transform: `translateY(${(1 - Math.min(cap, 1)) * 20}px)`,
        }}
      >
        <div
          style={{
            display: "inline-flex",
            background: ACCENT,
            color: WHITE,
            padding: "10px 24px",
            borderRadius: 999,
            fontSize: 26,
            fontWeight: 800,
            letterSpacing: "0.08em",
            marginBottom: 16,
          }}
        >
          AGENCY DASHBOARD
        </div>
        <div
          style={{
            color: WHITE,
            fontSize: 64,
            fontWeight: 900,
            lineHeight: 1.05,
            letterSpacing: "-0.02em",
          }}
        >
          Your whole portfolio.
          <br />
          One screen.
        </div>
      </div>

      {/* Browser frame */}
      <BrowserFrame
        src={staticFile("Screenshot 2026-04-23 at 11.08.32.png")}
        url="dashboard"
        rise={rise}
        zoomScale={1.04}
        zoomOriginY="30%"
      />

      {/* Feature badges */}
      <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
        <Badge text="📋 Lease pipeline"      delay={40} />
        <Badge text="🔧 Maintenance"         delay={55} />
        <Badge text="✍️ Pending signatures"  delay={70} accent />
      </div>
    </AbsoluteFill>
  );
};

// ── Scene 3 — Lease builder ───────────────────────────────────────────────────
const Scene3_Lease: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const bg   = fade(frame, 0, 10);
  const rise  = enter(frame, fps, 5);
  const cap   = fade(frame, 20, 45);

  return (
    <AbsoluteFill
      style={{
        background: "#F4F5FF",
        fontFamily: FONT,
        padding: 60,
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        gap: 36,
        opacity: bg,
      }}
    >
      {/* Caption above */}
      <div
        style={{
          opacity: cap,
          transform: `translateY(${(1 - Math.min(cap, 1)) * 20}px)`,
        }}
      >
        <div
          style={{
            display: "inline-flex",
            background: NAVY,
            color: WHITE,
            padding: "10px 24px",
            borderRadius: 999,
            fontSize: 26,
            fontWeight: 800,
            letterSpacing: "0.08em",
            marginBottom: 16,
          }}
        >
          AI LEASE BUILDER
        </div>
        <div
          style={{
            color: NAVY,
            fontSize: 64,
            fontWeight: 900,
            lineHeight: 1.05,
            letterSpacing: "-0.02em",
          }}
        >
          RHA-compliant lease.
          <br />
          Generated in minutes.
        </div>
      </div>

      {/* Browser frame */}
      <BrowserFrame
        src={staticFile("Screenshot 2026-04-23 at 11.08.18.png")}
        url="leases / builder"
        rise={rise}
        zoomScale={1.05}
        zoomOriginY="25%"
      />

      {/* Feature badges */}
      <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
        <Badge text="⚖️ RHA-compliant"        delay={40} />
        <Badge text="✍️ Native e-signing"      delay={55} accent />
        <Badge text="📄 Full table of contents" delay={70} />
      </div>
    </AbsoluteFill>
  );
};

// ── Scene 4 — CTA ─────────────────────────────────────────────────────────────
const Scene4_CTA: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const logo   = enter(frame, fps, 0, 14);
  const free   = fade(frame, 20, 50);
  const cta    = enter(frame, fps, 25, 14);
  const pulse  = 1 + Math.sin(frame / 8) * 0.018 * (frame > fps ? 1 : 0);
  const small  = fade(frame, 60, 85);

  return (
    <AbsoluteFill
      style={{
        background: ACCENT,
        fontFamily: FONT,
        alignItems: "center",
        justifyContent: "center",
        flexDirection: "column",
        gap: 32,
        padding: 80,
        display: "flex",
      }}
    >
      <div
        style={{
          color: WHITE,
          fontSize: 80,
          fontWeight: 900,
          letterSpacing: "0.3em",
          transform: `scale(${logo})`,
          opacity: logo,
        }}
      >
        KLIKK
      </div>
      <div
        style={{
          color: WHITE,
          fontSize: 48,
          fontWeight: 700,
          textAlign: "center",
          lineHeight: 1.2,
          opacity: free,
        }}
      >
        Free for your first
        <br />5 properties
      </div>
      <div
        style={{
          background: WHITE,
          color: ACCENT,
          padding: "28px 56px",
          borderRadius: 999,
          fontSize: 44,
          fontWeight: 900,
          transform: `scale(${cta * pulse})`,
          opacity: cta,
        }}
      >
        klikk.co.za
      </div>
      <div
        style={{
          color: WHITE,
          opacity: small * 0.75,
          fontSize: 28,
          fontWeight: 500,
          letterSpacing: "0.05em",
        }}
      >
        No credit card required
      </div>
    </AbsoluteFill>
  );
};

// ── Root ──────────────────────────────────────────────────────────────────────
export const AiLeaseExplainer: React.FC = () => {
  const { fps } = useVideoConfig();
  const t = springTiming({ config: { damping: 200 }, durationInFrames: TRANS });

  return (
    <AbsoluteFill style={{ background: NAVY }}>
      <TransitionSeries>
        <TransitionSeries.Sequence durationInFrames={S1}>
          <Sequence premountFor={fps}><Scene1_Hook /></Sequence>
        </TransitionSeries.Sequence>

        <TransitionSeries.Transition presentation={slide({ direction: "from-right" })} timing={t} />

        <TransitionSeries.Sequence durationInFrames={S2}>
          <Sequence premountFor={fps}><Scene2_Dashboard /></Sequence>
        </TransitionSeries.Sequence>

        <TransitionSeries.Transition presentation={slide({ direction: "from-right" })} timing={t} />

        <TransitionSeries.Sequence durationInFrames={S3}>
          <Sequence premountFor={fps}><Scene3_Lease /></Sequence>
        </TransitionSeries.Sequence>

        <TransitionSeries.Transition presentation={slide({ direction: "from-right" })} timing={t} />

        <TransitionSeries.Sequence durationInFrames={S4}>
          <Sequence premountFor={fps}><Scene4_CTA /></Sequence>
        </TransitionSeries.Sequence>
      </TransitionSeries>
    </AbsoluteFill>
  );
};
