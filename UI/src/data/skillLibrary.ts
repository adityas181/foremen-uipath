// A compact, display-only view of FOREMAN's learned-skill library. The full cards
// live as SKILL.md files (id, match_key, recipe, citations…); this is just enough
// to render the horizontal breadth on the Skills tab. Skills the agent learns at
// run time arrive as live `skill.written` events and are shown separately — any id
// here that also exists live is rendered as the richer live card instead.
export interface LibrarySkill {
  id: string
  domain: string
  equipment_class: string
  failure_mode: string
  diagnosis: string
  status: 'candidate' | 'trusted' | 'retired'
  approve_count: number
}

export const SKILL_LIBRARY: LibrarySkill[] = [
  {
    id: 'SK-pv-mc4-connector-burn',
    domain: 'Solar',
    equipment_class: 'pv_string',
    failure_mode: 'connector_burn',
    diagnosis: 'Cross-mated MC4 → contact heating → DC arc. Workmanship, not the module batch.',
    status: 'trusted',
    approve_count: 3,
  },
  {
    id: 'SK-coastal-rf-corrosion',
    domain: 'Telecom',
    equipment_class: 'rf_jumper_cable',
    failure_mode: 'salt_corrosion',
    diagnosis: 'Non-marine cable in coastal salt air → galvanic corrosion. Spec defect, vendor-liable.',
    status: 'trusted',
    approve_count: 4,
  },
  {
    id: 'SK-imm-checkring-suckback',
    domain: 'Injection Moulding',
    equipment_class: 'imm_screw',
    failure_mode: 'suck_back',
    diagnosis: 'Worn non-return valve → melt back-flow → short shots. Confirm via cushion drift.',
    status: 'trusted',
    approve_count: 5,
  },
  {
    id: 'SK-hvac-chiller-shortcycle',
    domain: 'HVAC',
    equipment_class: 'chiller',
    failure_mode: 'short_cycle',
    diagnosis: 'Low refrigerant charge → LP trips → compressor short-cycling. Leak-check before topping up.',
    status: 'trusted',
    approve_count: 3,
  },
  {
    id: 'SK-rail-axle-hotbox',
    domain: 'Rail',
    equipment_class: 'axle_bearing',
    failure_mode: 'hotbox',
    diagnosis: 'Bearing temperature rise vs train mean → incipient seizure. Trend, don’t threshold.',
    status: 'trusted',
    approve_count: 4,
  },
  {
    id: 'SK-dc-crac-condensate',
    domain: 'Data Center',
    equipment_class: 'crac_unit',
    failure_mode: 'condensate_flood',
    diagnosis: 'Blocked condensate drain → pan overflow under the raised floor. Clear + add float switch.',
    status: 'candidate',
    approve_count: 2,
  },
  {
    id: 'SK-transformer-bushing-pd',
    domain: 'Power',
    equipment_class: 'transformer',
    failure_mode: 'partial_discharge',
    diagnosis: 'Bushing partial discharge (DGA + acoustic) → insulation degradation. IEC 60599 thresholds.',
    status: 'candidate',
    approve_count: 1,
  },
  {
    id: 'SK-water-dosingpump-diaphragm',
    domain: 'Water',
    equipment_class: 'dosing_pump',
    failure_mode: 'diaphragm_rupture',
    diagnosis: 'Dosing pump diaphragm rupture → loss of prime → underdosing. Check leak-detect port.',
    status: 'trusted',
    approve_count: 3,
  },
]
