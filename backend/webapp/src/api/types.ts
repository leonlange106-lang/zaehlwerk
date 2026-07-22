// Typisierte Spiegel der Backend-Schemata (schrittweise erweitert während der
// Migration). Namen folgen bewusst den JSON-Feldern der REST-API.

export interface RoleInfo {
  key: string;
  label: string;
  hint: string;
}

export interface User {
  id: string;
  username: string;
  display_name: string;
  role: string;
  is_admin: boolean;
  aktiv: boolean;
  source?: string;
  two_factor_enabled: boolean;
  is_first_login: boolean;
  temp_password_active: boolean;
}

export interface AuthStatus {
  mode: string;
  authenticated: boolean;
  setup_required: boolean;
  recovery: boolean;
  crypto_available?: boolean;
  user: User | null;
  permissions?: Record<string, boolean>;
  roles?: RoleInfo[];
}

export interface SystemRead {
  id: string;
  name: string;
  typ: string;
  einheit: string;
  farbe: string;
  icon: string;
  aktiv: boolean;
  zusatzfelder?: Record<string, unknown>;
}

export interface SeriesPoint {
  d: string;
  v: number;
}

export interface Prognosis {
  projected_consumption?: number | null;
  projected_cost?: number | null;
  abschlag_annual?: number | null;
  exceeds_abschlag?: boolean | null;
}

export interface DashboardSystem {
  id: string;
  name: string;
  typ: string;
  einheit: string;
  farbe: string;
  latest?: number | null;
  latest_datum?: string | null;
  total_consumption?: number | null;
  total_cost?: number | null;
  total_cost_tariff?: number | null;
  avg_per_day?: number | null;
  series: SeriesPoint[];
  prognosis?: Prognosis | null;
}

export interface RecentReading {
  id: string;
  system_id: string;
  system: string;
  farbe?: string | null;
  einheit: string;
  datum?: string | null;
  value: number;
  source: string;
}

export interface DashboardData {
  systems: DashboardSystem[];
  months: number;
  recent: RecentReading[];
}

export interface Reading {
  id: string;
  system_id: string;
  datum: string;
  value: number;
  cost?: number | null;
  meter_replaced: boolean;
  meter_start?: number | null;
  note?: string | null;
  source: string;
  consumption?: number | null;
  consumption_per_day?: number | null;
  is_outlier: boolean;
  cost_effective?: number | null;
  cost_estimated: boolean;
}

export interface SystemStats {
  total_consumption: number;
  total_cost: number;
  total_days: number;
  avg_per_day?: number | null;
  cost_per_day?: number | null;
  cost_per_unit?: number | null;
  min_per_day?: number | null;
  max_per_day?: number | null;
  total_cost_tariff?: number | null;
  avg_price_effective?: number | null;
  coverage_ratio: number;
}

export interface ChartData {
  system_id: string;
  name: string;
  unit: string;
  color: string;
  labels: string[];
  values: (number | null)[];
  consumption: (number | null)[];
  consumption_per_day: (number | null)[];
  outliers: boolean[];
  meter_replaced: boolean[];
}

// Antwort von POST /api/ocr/scan
export interface OcrResult {
  value?: number | null;
  confidence?: number | null;
  datum?: string | null;
  previous?: number | null;
  text?: string | null;
}
