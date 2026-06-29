import type { LucideIcon } from 'lucide-react'
import {
  Activity,
  Bot,
  BrainCircuit,
  CloudSun,
  Eye,
  Factory,
  Network,
  Package,
  Scale,
  ShieldAlert,
  ShieldCheck,
  TrendingDown,
  Truck,
} from 'lucide-react'

// Shared id → icon map for the crew (used by the Crew tab + the Console strip).
export const CREW_ICON: Record<string, LucideIcon> = {
  supervisor: Bot,
  vision: Eye,
  diagnosis_recommendation_engine: BrainCircuit,
  fleet_blast_radius: Network,
  warranty_entitlement: ShieldCheck,
  sla_commercial_impact: TrendingDown,
  safety_compliance: ShieldAlert,
  parts_logistics: Package,
  field_dispatch: Truck,
  telemetry_predictive: Activity,
  vendor_supply_chain: Factory,
  site_access_weather: CloudSun,
  cost_optimization: Scale,
}
