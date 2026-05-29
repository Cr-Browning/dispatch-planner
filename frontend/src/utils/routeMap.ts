import type { RouteStop, VehicleRoute } from "../api/types";

export type LatLng = [number, number];

export const ROUTE_COLORS = [
  "#2563eb",
  "#059669",
  "#d97706",
  "#dc2626",
  "#7c3aed",
  "#0891b2",
];

export function routeColor(routeOrder: number): string {
  return ROUTE_COLORS[(routeOrder - 1) % ROUTE_COLORS.length];
}

export function parseRouteGeometry(geometryJson: string | null): LatLng[] {
  if (!geometryJson) {
    return [];
  }
  try {
    const parsed = JSON.parse(geometryJson) as {
      type?: string;
      coordinates?: [number, number][];
    };
    if (parsed.type === "LineString" && Array.isArray(parsed.coordinates)) {
      return parsed.coordinates
        .filter((c) => c.length >= 2)
        .map((c) => [c[1], c[0]] as LatLng);
    }
  } catch {
    return [];
  }
  return [];
}

export function stopsToPath(stops: RouteStop[]): LatLng[] {
  return stops
    .filter((s) => s.latitude != null && s.longitude != null)
    .sort((a, b) => a.stop_order - b.stop_order)
    .map((s) => [s.latitude as number, s.longitude as number]);
}

export function routePath(route: VehicleRoute): LatLng[] {
  const fromGeometry = parseRouteGeometry(route.route_geometry_json);
  if (fromGeometry.length >= 2) {
    return fromGeometry;
  }
  return stopsToPath(route.stops);
}

export function boundsFromPaths(paths: LatLng[][]): LatLng[] | null {
  const points = paths.flat();
  if (points.length === 0) {
    return null;
  }
  return points;
}

export function stopMarkerLabel(
  stop: RouteStop,
  employeeName: (id: number) => string
): string {
  if (stop.stop_type === "job_site") {
    return "Job site";
  }
  if (stop.stop_type === "driver_start" && stop.employee_id) {
    return `Driver: ${employeeName(stop.employee_id)}`;
  }
  if (stop.stop_type === "pickup" && stop.employee_id) {
    return `Pickup: ${employeeName(stop.employee_id)}`;
  }
  return stop.location_label ?? stop.stop_type;
}

export function stopMarkerKind(stop: RouteStop): "job" | "pickup" | "driver" {
  if (stop.stop_type === "job_site") {
    return "job";
  }
  if (stop.stop_type === "driver_start") {
    return "driver";
  }
  return "pickup";
}
