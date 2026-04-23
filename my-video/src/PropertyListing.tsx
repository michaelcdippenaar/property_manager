import React from "react";
import {
  AbsoluteFill,
  Img,
  Sequence,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

// ---------- Types ----------

export type Photo = {
  src: string;
  caption?: string;
};

export type PropertyListingProps = {
  address: string;
  suburb: string;
  price: string; // pre-formatted e.g. "R 18 500 / month"
  beds: number;
  baths: number;
  sizeSqm?: number;
  parking?: number;
  photos: Photo[];
  agentName: string;
  agentPhone: string;
  ctaUrl: string; // e.g. "klikk.co.za/listings/123"
  tagline?: string; // optional headline, e.g. "Now available"
  brand?: {
    name?: string;
    navy?: string;
    accent?: string;
  };
};

// ---------- Timing ----------

export const FPS = 30;
export const INTRO_FRAMES = 60; // 2s
export const PHOTO_FRAMES = 90; // 3s per photo
export const OUTRO_FRAMES = 90; // 3s

export const totalDurationFrames = (photoCount: number) =>
  INTRO_FRAMES + Math.max(1, photoCount) * PHOTO_FRAMES + OUTRO_FRAMES;

// ---------- Defaults ----------

export const defaultProps: PropertyListingProps = {
  address: "12 Dorp Street",
  suburb: "Stellenbosch Central",
  price: "R 18 500 / month",
  beds: 2,
  baths: 1,
  sizeSqm: 78,
  parking: 1,
  photos: [
    {
      src: "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=1600",
    },
    {
      src: "https://images.unsplash.com/photo-1505691938895-1758d7feb511?w=1600",
    },
    {
      src: "https://images.unsplash.com/photo-1493809842364-78817add7ffb?w=1600",
    },
  ],
  agentName: "Sarah van der Merwe",
  agentPhone: "+27 82 555 0123",
  ctaUrl: "klikk.co.za/listing/demo",
  tagline: "Now available",
  brand: {
    name: "KLIKK",
    navy: "#2B2D6E",
    accent: "#FF3D7F",
  },
};

// ---------- Helpers ----------

const fontStack =
  '"Bricolage Grotesque", "DM Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';

// ---------- Sub-components ----------

const Intro: React.FC<{ brand: NonNullable<PropertyListingProps["brand"]>; tagline: string }> = ({
  brand,
  tagline,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const logoSpring = spring({ frame, fps, config: { damping: 14 } });
  const taglineOpacity = interpolate(frame, [20, 35], [0, 1], {
    extrapolateRight: "clamp",
  });
  const exit = interpolate(frame, [INTRO_FRAMES - 10, INTRO_FRAMES], [1, 0], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        background: brand.navy,
        opacity: exit,
        fontFamily: fontStack,
      }}
      className="flex items-center justify-center"
    >
      <div
        style={{ transform: `scale(${logoSpring})` }}
        className="flex flex-col items-center"
      >
        <div
          style={{ color: "white", letterSpacing: "0.3em" }}
          className="text-8xl font-black"
        >
          {brand.name}
        </div>
        <div
          style={{
            backgroundColor: brand.accent,
            height: 8,
            width: 160,
            marginTop: 24,
            borderRadius: 4,
          }}
        />
        <div
          style={{
            color: "white",
            opacity: taglineOpacity,
            marginTop: 40,
            letterSpacing: "0.2em",
          }}
          className="text-3xl font-medium uppercase"
        >
          {tagline}
        </div>
      </div>
    </AbsoluteFill>
  );
};

const PhotoSlide: React.FC<{ photo: Photo; index: number }> = ({ photo, index }) => {
  const frame = useCurrentFrame();

  // Ken Burns: slow scale + slight pan, alternating direction per slide
  const scale = interpolate(frame, [0, PHOTO_FRAMES], [1.05, 1.2]);
  const panDir = index % 2 === 0 ? 1 : -1;
  const translateX = interpolate(frame, [0, PHOTO_FRAMES], [0, 30 * panDir]);

  const fadeIn = interpolate(frame, [0, 10], [0, 1], { extrapolateRight: "clamp" });
  const fadeOut = interpolate(frame, [PHOTO_FRAMES - 10, PHOTO_FRAMES], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ opacity: fadeIn * fadeOut }}>
      <AbsoluteFill
        style={{
          transform: `scale(${scale}) translateX(${translateX}px)`,
        }}
      >
        <Img
          src={photo.src}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
          }}
        />
      </AbsoluteFill>
      {/* Bottom gradient for legibility */}
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(to bottom, rgba(0,0,0,0) 55%, rgba(0,0,0,0.75) 100%)",
        }}
      />
    </AbsoluteFill>
  );
};

const LowerThird: React.FC<{
  props: PropertyListingProps;
  startFrame: number;
}> = ({ props, startFrame }) => {
  const frame = useCurrentFrame();
  const local = frame - startFrame;
  const { fps } = useVideoConfig();
  const rise = spring({ frame: local, fps, config: { damping: 16 } });

  const brand = props.brand!;

  const chip = (label: string, value: string | number) => (
    <div
      style={{
        background: "rgba(255,255,255,0.15)",
        backdropFilter: "blur(8px)",
        borderRadius: 999,
        padding: "10px 22px",
        color: "white",
        fontWeight: 600,
        fontSize: 28,
      }}
    >
      <span style={{ opacity: 0.7, marginRight: 8 }}>{label}</span>
      {value}
    </div>
  );

  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-end",
        padding: 72,
        fontFamily: fontStack,
        transform: `translateY(${(1 - rise) * 60}px)`,
        opacity: rise,
      }}
    >
      <div
        style={{
          display: "inline-flex",
          alignSelf: "flex-start",
          background: brand.accent,
          color: "white",
          padding: "8px 20px",
          borderRadius: 999,
          letterSpacing: "0.2em",
          fontWeight: 700,
          fontSize: 22,
          marginBottom: 20,
        }}
      >
        TO LET
      </div>
      <div
        style={{
          color: "white",
          fontSize: 72,
          fontWeight: 800,
          lineHeight: 1.05,
          textShadow: "0 4px 30px rgba(0,0,0,0.5)",
        }}
      >
        {props.address}
      </div>
      <div
        style={{
          color: "white",
          opacity: 0.9,
          fontSize: 36,
          marginTop: 8,
          fontWeight: 500,
        }}
      >
        {props.suburb}
      </div>

      <div style={{ display: "flex", gap: 12, marginTop: 28, flexWrap: "wrap" }}>
        {chip("Beds", props.beds)}
        {chip("Baths", props.baths)}
        {props.sizeSqm ? chip("Size", `${props.sizeSqm} m²`) : null}
        {props.parking ? chip("Parking", props.parking) : null}
      </div>

      <div
        style={{
          marginTop: 28,
          color: "white",
          fontSize: 64,
          fontWeight: 900,
          letterSpacing: "-0.02em",
        }}
      >
        {props.price}
      </div>
    </AbsoluteFill>
  );
};

const Outro: React.FC<{ props: PropertyListingProps }> = ({ props }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const brand = props.brand!;

  const rise = spring({ frame, fps, config: { damping: 16 } });
  const pulse =
    1 + Math.sin(frame / 6) * 0.015 * (frame > 30 ? 1 : 0);

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(160deg, ${brand.navy} 0%, #1a1c52 100%)`,
        fontFamily: fontStack,
        padding: 80,
        justifyContent: "center",
      }}
    >
      <div style={{ opacity: rise, transform: `translateY(${(1 - rise) * 30}px)` }}>
        <div
          style={{
            color: brand.accent,
            fontWeight: 700,
            letterSpacing: "0.3em",
            fontSize: 28,
            marginBottom: 24,
          }}
        >
          BOOK A VIEWING
        </div>
        <div
          style={{
            color: "white",
            fontSize: 88,
            fontWeight: 900,
            lineHeight: 1,
            marginBottom: 32,
          }}
        >
          {props.price}
        </div>
        <div style={{ color: "white", fontSize: 40, fontWeight: 600 }}>
          {props.agentName}
        </div>
        <div style={{ color: "white", opacity: 0.8, fontSize: 36, marginTop: 8 }}>
          {props.agentPhone}
        </div>

        <div
          style={{
            marginTop: 64,
            background: brand.accent,
            color: "white",
            padding: "24px 40px",
            borderRadius: 24,
            display: "inline-block",
            fontSize: 36,
            fontWeight: 700,
            transform: `scale(${pulse})`,
          }}
        >
          {props.ctaUrl}
        </div>
      </div>

      <div
        style={{
          position: "absolute",
          bottom: 60,
          right: 80,
          color: "white",
          opacity: 0.6,
          letterSpacing: "0.3em",
          fontWeight: 800,
          fontSize: 28,
        }}
      >
        {brand.name}
      </div>
    </AbsoluteFill>
  );
};

// ---------- Main ----------

export const PropertyListing: React.FC<PropertyListingProps> = (props) => {
  const brand = { ...defaultProps.brand, ...props.brand } as NonNullable<
    PropertyListingProps["brand"]
  >;
  const tagline = props.tagline ?? defaultProps.tagline!;
  const photos = props.photos.length > 0 ? props.photos : defaultProps.photos;

  return (
    <AbsoluteFill style={{ background: "black" }}>
      {/* Intro */}
      <Sequence durationInFrames={INTRO_FRAMES}>
        <Intro brand={brand} tagline={tagline} />
      </Sequence>

      {/* Photos with lower-third */}
      {photos.map((photo, i) => {
        const from = INTRO_FRAMES + i * PHOTO_FRAMES;
        return (
          <Sequence key={i} from={from} durationInFrames={PHOTO_FRAMES}>
            <PhotoSlide photo={photo} index={i} />
            {i === 0 ? (
              <LowerThird props={{ ...props, brand }} startFrame={0} />
            ) : null}
          </Sequence>
        );
      })}

      {/* Outro */}
      <Sequence from={INTRO_FRAMES + photos.length * PHOTO_FRAMES} durationInFrames={OUTRO_FRAMES}>
        <Outro props={{ ...props, brand }} />
      </Sequence>
    </AbsoluteFill>
  );
};
