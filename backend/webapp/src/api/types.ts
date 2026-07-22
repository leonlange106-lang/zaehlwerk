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

// ---------- Dashboard-Layout (Kacheln) ----------
export type TileType =
  | 'latest_reading' | 'line_chart' | 'pie_chart' | 'cost_summary' | 'trend' | 'cost_forecast';
export type Timeframe = '7d' | '30d' | '90d' | 'ytd' | '12m' | 'all' | 'custom';

export interface DashboardTile {
  id: string;
  type: TileType;
  x: number;
  y: number;
  w: number;
  h: number;
  system_id?: string | null;
  system_ids?: string[];
  timeframe?: Timeframe;
  title?: string | null;
  range_from?: string | null;
  range_to?: string | null;
}

export interface DashboardLayoutResponse {
  tiles: DashboardTile[];
  is_default: boolean;
  recovered?: boolean;
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
  value_kwh?: number | null;
  consumption_kwh?: number | null;
  consumption_per_day_kwh?: number | null;
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
  kwh_factor?: number | null;
  total_consumption_kwh?: number | null;
  avg_per_day_kwh?: number | null;
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
  consumption_per_day_kwh?: (number | null)[];
  kwh_factor?: number | null;
}

// Antwort von POST /api/ocr/scan
export interface OcrResult {
  value?: number | null;
  confidence?: number | null;
  datum?: string | null;
  previous?: number | null;
  text?: string | null;
}

// ---------- Zähler-Metadaten (Meters) ----------
export interface Meter {
  id: string;
  system_id: string;
  hersteller?: string | null;
  modell?: string | null;
  zaehlernummer?: string | null;
  bauart?: string | null;
  baujahr?: number | null;
  eichung_bis?: string | null;
  messstellenbetreiber?: string | null;
  stellen_vor?: number | null;
  stellen_nach?: number | null;
  eingebaut_am?: string | null;
  ausgebaut_am?: string | null;
  notiz?: string | null;
  aktiv: boolean;
  eichung_faellig_in_tagen?: number | null;
  eichung_abgelaufen: boolean;
}

// ---------- Admin ----------
export interface AdminUserStatus {
  id: string;
  username: string;
  display_name: string;
  role: string;
  is_admin: boolean;
  aktiv: boolean;
  source: string;
  two_factor_enabled: boolean;
  two_factor_status: string;
  password_status: string;
  is_first_login: boolean;
  last_seen: string | null;
  online: boolean;
  active_sessions: number;
}

export interface AdminSession {
  jti: string;
  user_id: string;
  username: string;
  created_at: string;
  last_seen: string;
  expires_at: string;
  user_agent: string | null;
  ip: string | null;
  current: boolean;
}

export interface AdminDatabase {
  id: string;
  name: string;
  is_default: boolean;
  db_kind: string;
  owner_user_id: string;
  owner_name: string | null;
  size_bytes: number;
  shared_with: number;
}

export interface DatabaseAccessEntry {
  user_id: string;
  role: string;
  implicit: boolean;
}

export interface LogEntry {
  ts: string;
  level: string;
  logger: string;
  message: string;
}

export interface QueryResult {
  columns: string[];
  rows: unknown[][];
  row_count: number;
  truncated: boolean;
}

export interface UpdateStatus {
  supported: boolean;
  current: string;
  latest?: string | null;
  update_available?: boolean;
  pending?: unknown;
}

export interface AppSettings {
  offline_mode: boolean;
  notify_enabled: boolean;
  notify_interval_hours: number;
  outlier_sigma: number;
  backup_enabled: boolean;
  backup_time: string;
  backup_keep_days: number;
  audit_keep_days: number;
  telemetry_keep_days: number;
  default_role: string;
  [key: string]: unknown;
}

export interface TenantDatabase {
  id: string;
  name: string;
  role: string;
  is_default: boolean;
  owner_user_id: string;
  db_kind: string;
  size_bytes: number;
}

export interface DatabaseListResponse {
  active_id: string | null;
  databases: TenantDatabase[];
}

export interface BackupInfo {
  filename: string;
  size_bytes: number;
  created_at?: string | null;
}

export interface TariffPlan {
  id: string;
  system_id: string;
  name?: string | null;
  anbieter?: string | null;
  gueltig_ab: string;
  gueltig_bis?: string | null;
  arbeitspreis: number;
  grundpreis: number;
  notiz?: string | null;
  aktiv: boolean;
}

export interface AuditEntry {
  id: number;
  ts: string;
  user_id?: string | null;
  username?: string | null;
  action: string;
  target_table: string;
  target_id?: string | null;
  old_value?: unknown;
  new_value?: unknown;
}

export interface AuditResponse {
  entries: AuditEntry[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface AuditFacets {
  actions: string[];
  tables: string[];
  users: { id: string; username: string }[];
}
