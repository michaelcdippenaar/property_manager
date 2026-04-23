import React from "react";
import {
  AbsoluteFill,
  Sequence,
  Video,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { RentalLifecycleWheel } from "./RentalLifecycleWheel";

// ── Brand tokens ─────────────────────────────────────────────────────────────
const NAVY = "#2B2D6E";
const ACCENT = "#FF3D7F";
const WHITE = "#FFFFFF";
const FONT =
  '"Bricolage Grotesque", "DM Sans", -apple-system, BlinkMacSystemFont, sans-serif';

// Flip to true once you've dropped MP4s into /public/broll/
const USE_BROLL = false;

// ── Timing (30fps, 30s) ──────────────────────────────────────────────────────
const OPEN = 120;   // 4s — drone establishing shot
const BROLL2 = 90;  // 3s — phone scroll ("viewing")
const BROLL3 = 90;  // 3s — signing ("lease")
const WHEEL = 450;  // 15s — the full lifecycle wheel
const CLOSE = 150;  // 5s — cosy interior + CTA
export const BROLL_DURATION = OPEN + BROLL2 + BROLL3 + WHEEL + CLOSE; // 900 = 30s

// ═══════════════════════════════════════════════════════════════════════════
// Reusable: B-roll clip with overlay text
// ═══════════════════════════════════════════════════════════════════════════
type BRollSceneProps = {
  src: string;               // filename under /public/broll/, e.g. "drone-suburb.mp4"
  eyebrow?: string;          // small accent label
  headline: string;          // big white headline
  placeholderGradient: [string, string]; // fallback if USE_BROLL=false
};

const BRollScene: React.FC<BRollSceneProps> = ({
  src,
  eyebrow,
  headline,
  placeholderGradient,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const fadeIn = interpolate(frame, [0, 12], [0, 1], { extrapolateRight: "clamp" });
  const textY = spring({ frame: frame - 8, fps, config: { damping: 14 }, from: 30, to: 0 });

  return (
    <AbsoluteFill style={{ background: NAVY, fontFamily: FONT, opacity: fadeIn }}>
      {/* Background: AI B-roll or brand-gradient fallback */}
      {USE_BROLL ? (
        <Video
          src={staticFile(`broll/${src}`)}
          muted
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
          }}
        />
      ) : (
        <AbsoluteFill
          style={{
            background: `linear-gradient(135deg, ${placeholderGradient[0]}, ${placeholderGradient[1]})`,
          }}
        />
      )}

      {/* Navy darkening gradient — keeps text legible over any footage */}
      <AbsoluteFill
        style={{
          background: `linear-gradient(180deg, rgba(43,45,110,0.2) 0%, rgba(43,45,110,0.85) 100%)`,
        }}
      />

      {/* Overlay text */}
      <AbsoluteFill
        style={{
          justifyContent: "flex-end",
          alignItems: "flex-start",
          padding: 80,
          transform: `translateY(${textY}px)`,
        }}
      >
        {eyebrow && (
          <div
            style={{
              color: ACCENT,
              fontSize: 22,
              fontWeight: 700,
              letterSpacing: 4,
              textTransform: "uppercase",
              marginBottom: 14,
            }}
          >
            {eyebrow}
          </div>
        )}
        <div
          style={{
            color: WHITE,
            fontSize: 72,
            fontWeight: 800,
            letterSpacing: -3,
            lineHeight: 1.02,
            maxWidth: "90%",
          }}
        >
          {headline}
        </div>
      </AbsoluteFill>

      {/* Placeholder label — only shown when USE_BROLL=false */}
      {!USE_BROLL && (
        <div
          style={{
            position: "absolute",
            top: 40,
            right: 40,
            background: "rgba(0,0,0,0.5)",
            color: WHITE,
            fontSize: 18,
            padding: "8px 14px",
            borderRadius: 8,
            fontFamily: "monospace",
          }}
        >
          B-roll: {src}
        </div>
      )}
    </AbsoluteFill>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// Root composition
// ═══════════════════════════════════════════════════════════════════════════
export const LifecycleWithBroll: React.FC = () => {
  return (
    <AbsoluteFill style={{ background: NAVY }}>
      {/* 0-4s — Drone over SA suburb: establish location */}
      <Sequence from={0} durationInFrames={OPEN}>
        <BRollScene
          src="drone-suburb.mp4"
          eyebrow="South Africa"
          headline={"Rental property\nmanagement,\nend to end."}
          placeholderGradient={["#1a1b4b", "#2B2D6E"]}
        />
      </Sequence>

      {/* 4-7s — Phone scrolling: viewing */}
      <Sequence from={OPEN} durationInFrames={BROLL2}>
        <BRollScene
          src="phone-scroll.mp4"
          eyebrow="Stage 3"
          headline="From the first viewing…"
          placeholderGradient={["#2B2D6E", "#FF3D7F"]}
        />
      </Sequence>

      {/* 7-10s — Signing: lease */}
      <Sequence from={OPEN + BROLL2} durationInFrames={BROLL3}>
        <BRollScene
          src="signing-phone.mp4"
          eyebrow="Stage 5"
          headline="…to a signed lease…"
          placeholderGradient={["#FF3D7F", "#2B2D6E"]}
        />
      </Sequence>

      {/* 10-25s — The Klikk rental lifecycle wheel (hero moment) */}
      <Sequence from={OPEN + BROLL2 + BROLL3} durationInFrames={WHEEL}>
        <RentalLifecycleWheel />
      </Sequence>

      {/* 25-30s — Cosy interior + CTA */}
      <Sequence from={OPEN + BROLL2 + BROLL3 + WHEEL} durationInFrames={CLOSE}>
        <CloseScene />
      </Sequence>
    </AbsoluteFill>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// Close scene — B-roll interior with CTA pill
// ═══════════════════════════════════════════════════════════════════════════
const CloseScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const headline = spring({ frame, fps, config: { damping: 14 }, from: 0.9, to: 1 });
  const pulse = 1 + Math.sin(frame / 6) * 0.02;

  return (
    <AbsoluteFill style={{ background: NAVY, fontFamily: FONT }}>
      {USE_BROLL ? (
        <Video
          src={staticFile("broll/empty-lounge.mp4")}
          muted
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
        />
      ) : (
        <AbsoluteFill
          style={{
            background: `linear-gradient(135deg, #2B2D6E, #FF3D7F)`,
          }}
        />
      )}

      {/* Darkening overlay */}
      <AbsoluteFill
        style={{
          background: `linear-gradient(180deg, rgba(43,45,110,0.4) 0%, rgba(255,61,127,0.8) 100%)`,
        }}
      />

      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          padding: 60,
        }}
      >
        <div
          style={{
            color: WHITE,
            fontSize: 72,
            fontWeight: 800,
            letterSpacing: -3,
            textAlign: "center",
            lineHeight: 1.05,
            transform: `scale(${headline})`,
          }}
        >
          One platform.
          <br />
          One tenancy.
          <br />
          Start to finish.
        </div>
        <div
          style={{
            marginTop: 44,
            background: WHITE,
            color: NAVY,
            padding: "28px 56px",
            borderRadius: 999,
            fontSize: 52,
            fontWeight: 800,
            transform: `scale(${pulse})`,
          }}
        >
          klikk.co.za
        </div>
        <div
          style={{
            marginTop: 20,
            color: WHITE,
            fontSize: 24,
            fontWeight: 600,
            opacity: 0.9,
          }}
        >
          Free for your first 5 properties
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
