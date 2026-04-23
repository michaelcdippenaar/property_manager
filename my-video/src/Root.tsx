import "./index.css";
import { CalculateMetadataFunction, Composition } from "remotion";
import {
  PropertyListing,
  PropertyListingProps,
  defaultProps,
  totalDurationFrames,
  FPS,
} from "./PropertyListing";
import { AiLeaseExplainer, AI_LEASE_DURATION } from "./AiLeaseExplainer";
import { ThreeMinVsThreeHours, THREE_MIN_DURATION } from "./ThreeMinVsThreeHours";
import { RentalLifecycleWheel, WHEEL_DURATION } from "./RentalLifecycleWheel";
import { LifecycleWithBroll, BROLL_DURATION } from "./LifecycleWithBroll";

const calculateMetadata: CalculateMetadataFunction<PropertyListingProps> = ({
  props,
}) => {
  const photoCount = props.photos?.length ?? 0;
  const slug = (props.address ?? "listing")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");

  return {
    durationInFrames: totalDurationFrames(photoCount),
    defaultOutName: `listing-${slug}`,
  };
};

export const RemotionRoot: React.FC = () => {
  return (
    <>
      {/* Vertical 9:16 — Instagram Reels / TikTok / Shorts */}
      <Composition
        id="PropertyListing"
        component={PropertyListing}
        fps={FPS}
        width={1080}
        height={1920}
        durationInFrames={totalDurationFrames(defaultProps.photos.length)}
        defaultProps={defaultProps}
        calculateMetadata={calculateMetadata}
      />

      {/* Landscape 16:9 — for website embeds */}
      <Composition
        id="PropertyListingLandscape"
        component={PropertyListing}
        fps={FPS}
        width={1920}
        height={1080}
        durationInFrames={totalDurationFrames(defaultProps.photos.length)}
        defaultProps={defaultProps}
        calculateMetadata={calculateMetadata}
      />

      {/* AI Lease Explainer — 1:1 square for LinkedIn / Meta ads */}
      <Composition
        id="AiLeaseExplainer"
        component={AiLeaseExplainer}
        fps={30}
        width={1080}
        height={1080}
        durationInFrames={AI_LEASE_DURATION}
      />

      {/* AI Lease Explainer — 9:16 vertical for Reels / TikTok */}
      <Composition
        id="AiLeaseExplainerVertical"
        component={AiLeaseExplainer}
        fps={30}
        width={1080}
        height={1920}
        durationInFrames={AI_LEASE_DURATION}
      />

      {/* 3 min vs 3 hours — 15s split-screen for LinkedIn/Meta */}
      <Composition
        id="ThreeMinVsThreeHours"
        component={ThreeMinVsThreeHours}
        fps={30}
        width={1080}
        height={1080}
        durationInFrames={THREE_MIN_DURATION}
      />
      <Composition
        id="ThreeMinVsThreeHoursVertical"
        component={ThreeMinVsThreeHours}
        fps={30}
        width={1080}
        height={1920}
        durationInFrames={THREE_MIN_DURATION}
      />

      {/* 15-stage rental lifecycle wheel — 30s hero ad */}
      <Composition
        id="RentalLifecycleWheel"
        component={RentalLifecycleWheel}
        fps={30}
        width={1080}
        height={1080}
        durationInFrames={WHEEL_DURATION}
      />
      <Composition
        id="RentalLifecycleWheelVertical"
        component={RentalLifecycleWheel}
        fps={30}
        width={1080}
        height={1920}
        durationInFrames={WHEEL_DURATION}
      />

      {/* Lifecycle wheel mixed with AI-generated B-roll footage */}
      <Composition
        id="LifecycleWithBroll"
        component={LifecycleWithBroll}
        fps={30}
        width={1080}
        height={1080}
        durationInFrames={BROLL_DURATION}
      />
      <Composition
        id="LifecycleWithBrollVertical"
        component={LifecycleWithBroll}
        fps={30}
        width={1080}
        height={1920}
        durationInFrames={BROLL_DURATION}
      />
    </>
  );
};
