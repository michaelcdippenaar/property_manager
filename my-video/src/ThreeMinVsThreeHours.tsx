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

// ── Brand tokens ─────────────────────────────────────────────────────────────
const NAVY = "#2B2D6E";
const ACCENT = "#FF3D7F";
const WHITE = "#FFFFFF";
const GREY = "#9A9AB0";
const FONT =
  '"Bricolage Grotesque", "DM Sans", -apple-system, BlinkMacSystemFont, sans-serif';

// ── Timing (30fps, 15s total) ────────────────────────────────────────────────
// Hook (2s) → Split race (10s) → Payoff + CTA (3s)
const HOOK = 60;
const RACE = 300;
const CTA = 90;
export const THREE_MIN_DURATION = HOOK + RACE + CTA; // 450 frames = 15s

// ═══════════════════════════════════════════════════════════════════════════
// Scene 1 — Hook "3 MIN vs 3 HOURS"
// ═══════════════════════════════════════════════════════════════════════════
const Hook: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const leftX = spring({ frame, fps, config: { damping: 14 }, from: -600, to: 0 });
  const rightX = spring({
    frame: frame - 8,
    fps,
    config: { damping: 14 },
    from: 600,
    to: 0,
  });
  const vs = spring({ frame: frame - 20, fps, config: { damping: 10 }, from: 0, to: 1 });

  return (
    <AbsoluteFill style={{ background: NAVY, fontFamily: FONT }}>
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 40,
            color: WHITE,
            fontWeight: 800,
            fontSize: 140,
            lineHeight: 1,
            letterSpacing: -4,
          }}
        >
          <div style={{ transform: `translateX(${leftX}px)`, color: ACCENT }}>
            3 MIN
          </div>
          <div
            style={{
              transform: `scale(${vs})`,
              fontSize: 70,
              color: GREY,
              fontWeight: 700,
            }}
          >
            vs
          </div>
          <div
            style={{
              transform: `translateX(${rightX}px)`,
              textDecoration: "line-through",
              textDecorationColor: ACCENT,
              textDecorationThickness: 8,
            }}
          >
            3 HOURS
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// Scene 2 — Split-screen race: Word template (left) vs Klikk (right)
// ═══════════════════════════════════════════════════════════════════════════
const SplitRace: React.FC = () => {
  const frame = useCurrentFrame();

  // Timer in seconds — Word goes 0 → 180min, Klikk stops at 3min
  const wordMinutes = Math.floor(interpolate(frame, [0, RACE - 30], [0, 180], { extrapolateRight: "clamp" }));
  const klikkSeconds = Math.min(
    180,
    Math.floor(interpolate(frame, [0, 90], [0, 180], { extrapolateRight: "clamp" }))
  );

  const klikkDone = frame > 90;
  const doneScale = spring({
    frame: frame - 90,
    fps: 30,
    config: { damping: 12 },
    from: 0,
    to: 1,
  });

  return (
    <AbsoluteFill style={{ fontFamily: FONT, display: "flex", flexDirection: "row" }}>
      {/* LEFT — Word template chaos */}
      <div
        style={{
          flex: 1,
          background: "#F3F3F5",
          padding: 60,
          position: "relative",
          overflow: "hidden",
        }}
      >
        <div style={{ fontSize: 28, fontWeight: 700, color: "#555", marginBottom: 20 }}>
          Word template
        </div>
        <div
          style={{
            fontSize: 110,
            fontWeight: 800,
            color: NAVY,
            fontVariantNumeric: "tabular-nums",
            letterSpacing: -4,
          }}
        >
          {wordMinutes}:00
        </div>
        <div style={{ fontSize: 22, color: GREY, marginTop: 8 }}>minutes elapsed</div>

        {/* Chaos indicators */}
        <div style={{ marginTop: 50, display: "flex", flexDirection: "column", gap: 16 }}>
          {[
            { t: "Find-and-replace names", at: 20 },
            { t: "Check deposit clause", at: 50 },
            { t: "Add escalation %", at: 90 },
            { t: "Print, scan, email…", at: 140 },
            { t: "Tenant asks to change it", at: 200 },
            { t: "Email again", at: 250 },
          ].map((item, i) => {
            const visible = frame > item.at;
            const opacity = visible ? 1 : 0;
            const strikethrough = frame > item.at + 30;
            return (
              <div
                key={i}
                style={{
                  fontSize: 26,
                  color: "#444",
                  opacity,
                  transition: "opacity 0.2s",
                  textDecoration: strikethrough ? "line-through" : "none",
                  textDecorationColor: "#c00",
                }}
              >
                ✗ {item.t}
              </div>
            );
          })}
        </div>
      </div>

      {/* RIGHT — Klikk flow */}
      <div
        style={{
          flex: 1,
          background: NAVY,
          padding: 60,
          position: "relative",
          color: WHITE,
        }}
      >
        <div style={{ fontSize: 28, fontWeight: 700, color: ACCENT, marginBottom: 20 }}>
          Klikk
        </div>
        <div
          style={{
            fontSize: 110,
            fontWeight: 800,
            color: WHITE,
            fontVariantNumeric: "tabular-nums",
            letterSpacing: -4,
          }}
        >
          {Math.floor(klikkSeconds / 60)}:{String(klikkSeconds % 60).padStart(2, "0")}
        </div>
        <div style={{ fontSize: 22, color: "#a8a9d1", marginTop: 8 }}>
          minutes elapsed
        </div>

        <div style={{ marginTop: 50, display: "flex", flexDirection: "column", gap: 16 }}>
          {[
            { t: "Answer 8 questions", at: 10 },
            { t: "AI drafts lease", at: 40 },
            { t: "Tenant signs on phone", at: 70 },
          ].map((item, i) => {
            const visible = frame > item.at;
            return (
              <div
                key={i}
                style={{
                  fontSize: 28,
                  opacity: visible ? 1 : 0,
                  color: WHITE,
                }}
              >
                <span style={{ color: ACCENT, marginRight: 12 }}>✓</span>
                {item.t}
              </div>
            );
          })}
        </div>

        {/* Done badge */}
        {klikkDone && (
          <div
            style={{
              position: "absolute",
              bottom: 60,
              left: 60,
              right: 60,
              background: ACCENT,
              padding: "28px 36px",
              borderRadius: 18,
              transform: `scale(${doneScale})`,
              transformOrigin: "left center",
              display: "flex",
              alignItems: "center",
              gap: 16,
            }}
          >
            <div style={{ fontSize: 38, fontWeight: 800, color: WHITE }}>
              ✓ Lease signed
            </div>
          </div>
        )}
      </div>

      {/* Center divider */}
      <div
        style={{
          position: "absolute",
          left: "50%",
          top: 0,
          bottom: 0,
          width: 4,
          background: ACCENT,
          transform: "translateX(-50%)",
        }}
      />
    </AbsoluteFill>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// Scene 3 — CTA
// ═══════════════════════════════════════════════════════════════════════════
const CTAScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pop = spring({ frame, fps, config: { damping: 10 }, from: 0.9, to: 1 });
  const pulse = 1 + Math.sin(frame / 6) * 0.02;

  return (
    <AbsoluteFill
      style={{
        background: ACCENT,
        fontFamily: FONT,
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      <div
        style={{
          color: WHITE,
          fontSize: 90,
          fontWeight: 800,
          letterSpacing: -3,
          transform: `scale(${pop})`,
          textAlign: "center",
          lineHeight: 1.05,
        }}
      >
        Stop rewriting
        <br />
        your lease.
      </div>
      <div
        style={{
          marginTop: 40,
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
          marginTop: 24,
          color: WHITE,
          fontSize: 26,
          fontWeight: 600,
          opacity: 0.9,
        }}
      >
        Free for your first 5 properties
      </div>
    </AbsoluteFill>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// Root
// ═══════════════════════════════════════════════════════════════════════════
export const ThreeMinVsThreeHours: React.FC = () => {
  return (
    <AbsoluteFill style={{ background: WHITE }}>
      <Sequence from={0} durationInFrames={HOOK}>
        <Hook />
      </Sequence>
      <Sequence from={HOOK} durationInFrames={RACE}>
        <SplitRace />
      </Sequence>
      <Sequence from={HOOK + RACE} durationInFrames={CTA}>
        <CTAScene />
      </Sequence>
    </AbsoluteFill>
  );
};
