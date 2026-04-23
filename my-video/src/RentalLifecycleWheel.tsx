import React from "react";
import {
  AbsoluteFill,
  Easing,
  Sequence,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

// ── Brand tokens ─────────────────────────────────────────────────────────────
const NAVY = "#2B2D6E";
const ACCENT = "#FF3D7F";
const WHITE = "#FFFFFF";
const GREY = "#9A9AB0";
const DIM = "#1A1B4B";
const FONT =
  '"Bricolage Grotesque", "DM Sans", -apple-system, BlinkMacSystemFont, sans-serif';

// ── Timing (30fps, 30s) ──────────────────────────────────────────────────────
const HOOK = 90;   // 3s
const WHEEL = 600; // 20s — build + spin + highlight turnaround
const CTA = 210;   // 7s
export const WHEEL_DURATION = HOOK + WHEEL + CTA; // 900 frames = 30s

// ── 15 stages ────────────────────────────────────────────────────────────────
type Stage = { n: number; label: string; phase: "pre" | "turn" | "active" | "close" };
const STAGES: Stage[] = [
  { n: 1, label: "Notice Given", phase: "pre" },
  { n: 2, label: "Marketing", phase: "pre" },
  { n: 3, label: "Viewings", phase: "pre" },
  { n: 4, label: "Screening", phase: "pre" },
  { n: 5, label: "Lease Execution", phase: "pre" },
  { n: 6, label: "Invoice Setup", phase: "pre" },
  { n: 7, label: "Deposit Payment", phase: "pre" },
  { n: 8, label: "Move-Out Inspection", phase: "turn" },
  { n: 9, label: "Repairs & Cleaning", phase: "turn" },
  { n: 10, label: "Move-In Inspection", phase: "turn" },
  { n: 11, label: "Onboarding", phase: "turn" },
  { n: 12, label: "Rent Collection", phase: "active" },
  { n: 13, label: "Maintenance", phase: "active" },
  { n: 14, label: "Renewal / Notice", phase: "active" },
  { n: 15, label: "Deposit Refund", phase: "close" },
];

const phaseColour = (p: Stage["phase"]) =>
  p === "pre" ? NAVY : p === "turn" ? ACCENT : p === "active" ? WHITE : GREY;

// ── Brand components ─────────────────────────────────────────────────────────
const KlikkWordmark: React.FC<{ size?: number; colour?: string }> = ({
  size = 44,
  colour = WHITE,
}) => (
  <div
    style={{
      fontFamily: FONT,
      fontSize: size,
      fontWeight: 800,
      color: colour,
      letterSpacing: -2,
      display: "flex",
      alignItems: "center",
      gap: size * 0.18,
      lineHeight: 1,
    }}
  >
    <span
      style={{
        width: size * 0.9,
        height: size * 0.9,
        borderRadius: size * 0.22,
        background: ACCENT,
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        color: WHITE,
        fontSize: size * 0.62,
        fontWeight: 800,
      }}
    >
      K
    </span>
    <span>klikk</span>
  </div>
);

const BrandBar: React.FC<{ dark?: boolean; opacity?: number }> = ({
  dark = false,
  opacity = 1,
}) => (
  <div
    style={{
      position: "absolute",
      top: 36,
      left: 48,
      right: 48,
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      opacity,
      zIndex: 10,
    }}
  >
    <KlikkWordmark size={44} colour={dark ? NAVY : WHITE} />
    <div
      style={{
        fontFamily: FONT,
        fontSize: 18,
        fontWeight: 700,
        color: dark ? NAVY : WHITE,
        letterSpacing: 3,
        textTransform: "uppercase",
        opacity: 0.8,
      }}
    >
      Rental Property Management · 🇿🇦
    </div>
  </div>
);

// House/key icon for wheel centre
const PropertyIcon: React.FC<{ size?: number }> = ({ size = 84 }) => (
  <svg width={size} height={size} viewBox="0 0 64 64" fill="none">
    <path
      d="M8 28 L32 8 L56 28 L56 56 L40 56 L40 38 L24 38 L24 56 L8 56 Z"
      fill={ACCENT}
      stroke={WHITE}
      strokeWidth={2}
      strokeLinejoin="round"
    />
    <rect x={28} y={18} width={8} height={4} fill={WHITE} />
  </svg>
);

// ═══════════════════════════════════════════════════════════════════════════
// Scene 1 — Hook
// ═══════════════════════════════════════════════════════════════════════════
const Hook: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const line1 = spring({ frame, fps, config: { damping: 14 }, from: 60, to: 0 });
  const line1op = interpolate(frame, [0, 12], [0, 1], { extrapolateRight: "clamp" });

  const line2 = spring({ frame: frame - 20, fps, config: { damping: 14 }, from: 60, to: 0 });
  const line2op = interpolate(frame, [20, 32], [0, 1], { extrapolateRight: "clamp" });

  const threeScale = spring({ frame: frame - 30, fps, config: { damping: 10 }, from: 0.6, to: 1 });
  const fifteenScale = spring({ frame: frame - 55, fps, config: { damping: 9 }, from: 0, to: 1 });

  return (
    <AbsoluteFill
      style={{
        background: NAVY,
        fontFamily: FONT,
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      <BrandBar />
      <div
        style={{
          color: WHITE,
          fontSize: 52,
          fontWeight: 600,
          opacity: line1op,
          transform: `translateY(${line1}px)`,
          letterSpacing: -1,
          textAlign: "center",
        }}
      >
        Most rental software handles
      </div>
      <div
        style={{
          marginTop: 8,
          color: WHITE,
          fontSize: 140,
          fontWeight: 800,
          letterSpacing: -5,
          opacity: line2op,
          transform: `translateY(${line2}px) scale(${threeScale})`,
          lineHeight: 1,
        }}
      >
        3 stages.
      </div>
      <div
        style={{
          marginTop: 40,
          color: ACCENT,
          fontSize: 140,
          fontWeight: 800,
          letterSpacing: -5,
          transform: `scale(${fifteenScale})`,
          lineHeight: 1,
        }}
      >
        Klikk handles 15.
      </div>
      <div
        style={{
          marginTop: 28,
          color: WHITE,
          fontSize: 26,
          fontWeight: 600,
          opacity: interpolate(frame, [70, 85], [0, 0.85], { extrapolateRight: "clamp" }),
          letterSpacing: 2,
        }}
      >
        SA rental property management · end to end
      </div>
    </AbsoluteFill>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// Scene 2 — The Wheel
// ═══════════════════════════════════════════════════════════════════════════
const Wheel: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  const cx = width / 2;
  const cy = height / 2;
  const radius = Math.min(width, height) * 0.34;

  // Ring fades/draws in over first 30 frames
  const ringOpacity = interpolate(frame, [0, 30], [0, 1], { extrapolateRight: "clamp" });

  // Rotation: slow constant spin
  const rotation = interpolate(frame, [0, WHEEL], [0, 360], { easing: Easing.inOut(Easing.ease) });

  // Stage reveal: stagger dots in 30 → 180 frames (5s)
  const dotStart = 30;
  const dotEnd = 180;
  const perDot = (dotEnd - dotStart) / STAGES.length;

  // Which stage is "active" label? After 180f, sweep through them
  const sweepStart = 200;
  const sweepEnd = 440;
  const activeIndex = Math.min(
    14,
    Math.max(
      0,
      Math.floor(interpolate(frame, [sweepStart, sweepEnd], [0, 15], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }))
    )
  );

  // Zoom into turnaround (stages 8-11) at frame 460
  const zoomIn = spring({ frame: frame - 460, fps, config: { damping: 20 }, from: 1, to: 1.25 });
  const zoomOut = frame < 460 ? 1 : zoomIn;

  return (
    <AbsoluteFill style={{ background: NAVY, fontFamily: FONT }}>
      <BrandBar />
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          transform: `scale(${zoomOut})`,
          transformOrigin: "center center",
        }}
      >
        {/* Centre label with property icon + Klikk */}
        <div
          style={{
            position: "absolute",
            textAlign: "center",
            color: WHITE,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
          }}
        >
          <PropertyIcon size={72} />
          <div style={{ fontSize: 22, fontWeight: 600, color: GREY, letterSpacing: 4, marginTop: 12 }}>
            THE KLIKK
          </div>
          <div style={{ fontSize: 56, fontWeight: 800, letterSpacing: -2, lineHeight: 1.1 }}>
            RENTAL
          </div>
          <div style={{ fontSize: 56, fontWeight: 800, letterSpacing: -2, lineHeight: 1.1 }}>
            LIFECYCLE
          </div>
          <div style={{ fontSize: 22, fontWeight: 600, color: ACCENT, marginTop: 10 }}>
            15 stages · 4 phases
          </div>
        </div>

        {/* Outer ring */}
        <svg
          width={width}
          height={height}
          style={{ position: "absolute", opacity: ringOpacity }}
        >
          <g transform={`rotate(${rotation} ${cx} ${cy})`}>
            <circle
              cx={cx}
              cy={cy}
              r={radius}
              fill="none"
              stroke={DIM}
              strokeWidth={2}
              strokeDasharray="4 8"
            />

            {STAGES.map((s, i) => {
              const angle = (i / STAGES.length) * Math.PI * 2 - Math.PI / 2;
              const x = cx + Math.cos(angle) * radius;
              const y = cy + Math.sin(angle) * radius;

              const dotAppearFrame = dotStart + i * perDot;
              const appear = spring({
                frame: frame - dotAppearFrame,
                fps,
                config: { damping: 12 },
                from: 0,
                to: 1,
              });

              const isActive = frame >= sweepStart && activeIndex === i;
              const dotR = isActive ? 26 : 18;
              const colour = phaseColour(s.phase);
              const stroke = s.phase === "active" ? NAVY : "transparent";

              return (
                <g
                  key={s.n}
                  transform={`translate(${x} ${y}) scale(${appear}) rotate(${-rotation})`}
                >
                  <circle
                    r={dotR}
                    fill={colour}
                    stroke={stroke}
                    strokeWidth={3}
                  />
                  <text
                    x={0}
                    y={5}
                    textAnchor="middle"
                    fontFamily={FONT}
                    fontSize={18}
                    fontWeight={800}
                    fill={s.phase === "active" ? NAVY : WHITE}
                  >
                    {s.n}
                  </text>

                  {/* Glow ring on active */}
                  {isActive && (
                    <circle
                      r={dotR + 10}
                      fill="none"
                      stroke={ACCENT}
                      strokeWidth={3}
                      opacity={0.6}
                    />
                  )}
                </g>
              );
            })}
          </g>
        </svg>

        {/* Active stage label — bottom */}
        {frame >= sweepStart && (
          <div
            style={{
              position: "absolute",
              bottom: 80,
              left: 0,
              right: 0,
              textAlign: "center",
              color: WHITE,
            }}
          >
            <div
              style={{
                fontSize: 22,
                color: ACCENT,
                fontWeight: 700,
                letterSpacing: 3,
                textTransform: "uppercase",
              }}
            >
              Stage {STAGES[activeIndex].n}
            </div>
            <div style={{ fontSize: 48, fontWeight: 800, letterSpacing: -1 }}>
              {STAGES[activeIndex].label}
            </div>
          </div>
        )}

        {/* Phase legend — top */}
        <div
          style={{
            position: "absolute",
            top: 60,
            display: "flex",
            gap: 28,
            opacity: interpolate(frame, [30, 60], [0, 1], { extrapolateRight: "clamp" }),
          }}
        >
          {[
            { c: NAVY, label: "Pre-Tenancy", border: WHITE },
            { c: ACCENT, label: "Turnaround", border: "transparent" },
            { c: WHITE, label: "Active", border: "transparent" },
            { c: GREY, label: "Closeout", border: "transparent" },
          ].map((p) => (
            <div key={p.label} style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div
                style={{
                  width: 14,
                  height: 14,
                  borderRadius: 7,
                  background: p.c,
                  border: `2px solid ${p.border}`,
                }}
              />
              <div style={{ color: WHITE, fontSize: 18, fontWeight: 600 }}>{p.label}</div>
            </div>
          ))}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// Scene 3 — CTA
// ═══════════════════════════════════════════════════════════════════════════
const CTAScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const headline = spring({ frame, fps, config: { damping: 12 }, from: 0.9, to: 1 });
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
          fontSize: 80,
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
          marginTop: 48,
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
export const RentalLifecycleWheel: React.FC = () => {
  return (
    <AbsoluteFill style={{ background: NAVY }}>
      <Sequence from={0} durationInFrames={HOOK}>
        <Hook />
      </Sequence>
      <Sequence from={HOOK} durationInFrames={WHEEL}>
        <Wheel />
      </Sequence>
      <Sequence from={HOOK + WHEEL} durationInFrames={CTA}>
        <CTAScene />
      </Sequence>
    </AbsoluteFill>
  );
};
