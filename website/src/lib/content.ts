/**
 * Content Hub Loader
 *
 * Reads YAML/Markdown from the content/ directory at the project root.
 * This is the bridge between the content hub and the Astro website.
 *
 * The content hub is the single source of truth for:
 * - Feature statuses (features.yaml)
 * - Lifecycle stages (lifecycle.yaml)
 * - Integration partners (integrations.yaml)
 * - Pricing tiers (pricing.yaml)
 *
 * See content/README.md for conventions.
 */
import yaml from 'js-yaml';
import fs from 'fs';
import path from 'path';

// Content directory is at the monorepo root.
// Use process.cwd() which is always the website/ dir during dev/build.
const CONTENT_DIR = path.resolve(process.cwd(), '../content');

// ── Types ──────────────────────────────────────────────────

export interface Feature {
  name: string;
  slug: string;
  status: 'BUILT' | 'IN_PROGRESS' | 'PLANNED' | 'BETA';
  shipped_date?: string;
  category: string;
  backend_app?: string;
  key_files?: string[];
  headline: string;
  tagline: string;
  description: string;
  icon: string;
  show_on_homepage?: boolean;
  homepage_section?: string;
  lifecycle_step?: number | null;
}

export interface LifecycleStep {
  step: number;
  title: string;
  description: string;
  feature_ref: string;
  /** Resolved from features.yaml — never stored in lifecycle.yaml */
  status: Feature['status'];
  icon: string;
}

export interface Integration {
  name: string;
  slug: string;
  status: 'BUILT' | 'IN_PROGRESS' | 'PLANNED';
  priority: string;
  category: string;
  description: string;
  tagline: string;
  logo_abbrev: string;
  logo_color: string;
}

export interface PricingTier {
  name: string;
  slug: string;
  units: string;
  price: string;
  price_numeric: number;
  billing: string;
  highlight?: boolean;
  features: string[];
  cta_text: string;
  cta_url: string;
}

// ── Loaders ────────────────────────────────────────────────

/**
 * Load all features from features.yaml.
 * Returns a Map keyed by feature ID (e.g. "ai_lease_generation").
 */
export function getFeatures(): Record<string, Feature> {
  const raw = fs.readFileSync(path.join(CONTENT_DIR, 'product/features.yaml'), 'utf8');
  const data = yaml.load(raw) as { features: Record<string, Feature> };
  return data.features;
}

/**
 * Get features that should appear on the homepage.
 */
export function getHomepageFeatures(): Feature[] {
  const features = getFeatures();
  return Object.values(features).filter(f => f.show_on_homepage);
}

/**
 * Load lifecycle steps with status resolved from features.yaml.
 * Status is NEVER duplicated in lifecycle.yaml — always resolved here.
 */
export function getLifecycle(): LifecycleStep[] {
  const features = getFeatures();
  const raw = fs.readFileSync(path.join(CONTENT_DIR, 'product/lifecycle.yaml'), 'utf8');
  const data = yaml.load(raw) as { rental_lifecycle?: Array<{ step: number; title: string; description: string; feature_ref: string }>; lifecycle?: Array<{ step: number; title: string; description: string; feature_ref: string }> };

  const steps = data.rental_lifecycle || data.lifecycle || [];
  return steps.map(step => ({
    ...step,
    status: features[step.feature_ref]?.status || 'PLANNED',
    icon: features[step.feature_ref]?.icon || 'circle',
  }));
}

/**
 * Load integrations from integrations.yaml.
 */
export function getIntegrations(): Integration[] {
  const raw = fs.readFileSync(path.join(CONTENT_DIR, 'product/integrations.yaml'), 'utf8');
  const data = yaml.load(raw) as { integrations: Record<string, Integration> };
  return Object.values(data.integrations);
}

/**
 * Load pricing tiers from pricing.yaml.
 */
export function getPricing(): { tiers: PricingTier[]; annual_discount: string } {
  const raw = fs.readFileSync(path.join(CONTENT_DIR, 'product/pricing.yaml'), 'utf8');
  const data = yaml.load(raw) as any;
  return {
    tiers: data.tiers,
    annual_discount: data.annual_discount || '15%',
  };
}

/**
 * Resolve a status string to a badge class and label.
 * Used by Astro components to render status badges consistently.
 */
export function statusBadge(status: string): { class: string; label: string } {
  switch (status) {
    case 'BUILT':
      return { class: 'built', label: 'Live' };
    case 'IN_PROGRESS':
      return { class: 'in-progress', label: 'In Development' };
    case 'BETA':
      return { class: 'beta', label: 'Beta' };
    case 'PLANNED':
    default:
      return { class: 'planned', label: 'Coming Soon' };
  }
}
