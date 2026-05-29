export interface EmployeeListItem {
  id: number;
  first_name: string;
  last_name: string;
  display_name: string | null;
  active: boolean;
  is_driver: boolean;
  is_supervisor: boolean;
  default_vehicle_capacity: number;
  phone: string | null;
}

export interface EmployeeSkill {
  id: number;
  skill_id: number;
  proficiency: number;
  skill_name: string | null;
}

export interface EmployeeLocation {
  id: number;
  label: string;
  address: string;
  latitude: number | null;
  longitude: number | null;
  is_primary: boolean;
}

export interface Employee extends EmployeeListItem {
  notes: string | null;
  locations: EmployeeLocation[];
  skills: EmployeeSkill[];
}

export interface Skill {
  id: number;
  name: string;
  active: boolean;
}

export interface SkillWithUsage extends Skill {
  job_usage_count: number;
  employee_usage_count: number;
}

export interface DispatchValidationIssue {
  level: "error" | "warning" | string;
  message: string;
}

export interface DispatchValidation {
  ready: boolean;
  issues: DispatchValidationIssue[];
}

export interface JobListItem {
  id: number;
  job_name: string | null;
  client_name: string | null;
  address: string;
  required_arrival_time: string;
  required_headcount: number;
  roles_summary?: string;
}

export interface Job extends JobListItem {
  latitude: number | null;
  longitude: number | null;
  tolls_allowed: boolean;
  return_trip_enabled: boolean;
  dropoff_return_enabled: boolean;
  notes: string | null;
  required_skills: Array<{
    id: number;
    skill_id: number;
    skill_name: string | null;
    required_quantity: number;
    minimum_proficiency: number;
    is_preferred: boolean;
  }>;
}

export interface DispatchRun {
  id: number;
  run_date: string;
  name: string;
  status: string;
  optimization_profile_id: number | null;
  reasoning_summary: string | null;
  job_ids: number[];
}

export interface Assignment {
  employee_id: number;
  job_id: number;
  assigned_skill_id: number | null;
  assigned_role: string | null;
  substitution_used: boolean;
  substitution_reason: string | null;
  manually_overridden: boolean;
  warnings: string[];
}

export interface RouteStop {
  stop_order: number;
  stop_type: string;
  employee_id: number | null;
  location_label: string | null;
  address: string | null;
  latitude: number | null;
  longitude: number | null;
  eta: string | null;
  ride_time_minutes: number | null;
}

export interface VehicleRoute {
  id: number;
  job_id: number;
  driver_employee_id: number;
  vehicle_capacity: number;
  passenger_ids: number[];
  route_order: number;
  total_duration_minutes: number | null;
  total_distance_miles: number | null;
  arrival_time: string | null;
  is_late: boolean;
  google_maps_url: string | null;
  route_geometry_json: string | null;
  reasoning: string | null;
  warnings: string[];
  stops: RouteStop[];
}

export interface SolveResult {
  dispatch_run_id: number;
  status: string;
  assignments: Assignment[];
  vehicle_routes: VehicleRoute[];
  warnings: string[];
  reasoning_summary: string;
  route_reasoning_summary: string;
}

export interface PlanResponse {
  dispatch_run_id: number;
  status: string;
  assignments: Assignment[];
  vehicle_routes: VehicleRoute[];
  warnings: string[];
  reasoning_summary?: string;
  route_reasoning_summary?: string;
  override_type?: string;
}

export interface AppSettings {
  routing_provider: string;
  export_columns: string[];
}

export interface ExportResult {
  dispatch_run_id: number;
  export_record_id: number;
  file_path: string;
  row_count: number;
}

export interface DispatchCopyTemplate {
  source_run_id: number;
  source_run_name: string;
  source_run_date: string;
  job_ids: number[];
  job_ids_on_run_date?: number[];
  job_ids_off_run_date?: number[];
  jobs_on_run_date_count?: number;
  suggested_run_date: string;
  suggested_name: string;
}

export interface BackupRecord {
  id: number;
  file_path: string;
  notes: string | null;
  created_at: string;
}
