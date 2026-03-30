export interface Listing {
  id: number
  source_site: string
  source_url: string
  title: string
  price: number | null
  surface_m2: number | null
  nb_rooms: number | null
  nb_bedrooms: number | null
  property_type: string | null
  transaction_type: string
  description: string | null
  postal_code: string
  city: string | null
  department: string | null
  seller_name: string | null
  seller_phone: string | null
  seller_email: string | null
  image_urls: string[]
  publication_date: string | null
  created_at: string
}

export interface UrgencyInfo {
  score: number | null
  level: string | null
  factors: string[]
}

export interface PriceGapInfo {
  gap_pct: number | null
  price_m2_market: number | null
  comment: string | null
}

export interface ChronologyInfo {
  type: string | null
  days_on_market: number | null
  previous_price: number | null
  comment: string | null
}

export interface StrategicInfo {
  priority: string | null
  angle: string | null
  sms_script: string | null
}

export interface Lead {
  id: number
  listing_id: number
  status: string
  notes: string | null
  last_contacted_at: string | null
  last_interaction_at: string
  auto_purge_at: string
  created_at: string
  is_suspicious: boolean
  commission_amount: number | null
  commission_rate: number | null
  listing: Listing | null
  urgency: UrgencyInfo | null
  price_gap: PriceGapInfo | null
  chronology: ChronologyInfo | null
  strategic: StrategicInfo | null
}

export interface PipelineColumn {
  count: number
  total_value: number
  total_commission: number
}

export interface PipelineValue {
  pipeline: Record<string, PipelineColumn>
  totaux: {
    leads_actifs: number
    valeur_biens: number
    ca_potentiel: number
    taux_applique: number
  }
}

export interface DashboardStats {
  total_leads: number
  by_status: Record<string, number>
  by_site: Record<string, number>
}

export interface TerritoireDashboard {
  leads_24h: number
  leads_par_zone_24h: Record<string, number>
  zones_exclusives: { postal_code: string; user_id: number }[]
  top_zones: { postal_code: string; total_leads: number }[]
}

export type LeadStatus = 'nouveau' | 'tentative_appel' | 'rdv_estimation' | 'mandat_signe' | 'archive'

export const KANBAN_COLUMNS: { key: LeadStatus; label: string; color: string }[] = [
  { key: 'nouveau', label: 'Nouveau Lead', color: '#3b82f6' },
  { key: 'tentative_appel', label: 'Tentative Appel', color: '#f59e0b' },
  { key: 'rdv_estimation', label: 'RDV Estimation', color: '#8b5cf6' },
  { key: 'mandat_signe', label: 'Mandat Signe', color: '#10b981' },
  { key: 'archive', label: 'Archive', color: '#6b7280' },
]
