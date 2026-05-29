import { describe, expect, it } from "vitest";
import {
  parseRouteGeometry,
  routeColor,
  routePath,
  stopMarkerKind,
  stopMarkerLabel,
  stopsToPath,
} from "../utils/routeMap";
import type { RouteStop, VehicleRoute } from "../api/types";

const baseRoute = (overrides: Partial<VehicleRoute> = {}): VehicleRoute => ({
  id: 1,
  job_id: 10,
  driver_employee_id: 2,
  vehicle_capacity: 4,
  passenger_ids: [],
  route_order: 1,
  total_duration_minutes: 20,
  total_distance_miles: 5,
  arrival_time: null,
  is_late: false,
  google_maps_url: null,
  route_geometry_json: null,
  reasoning: null,
  warnings: [],
  stops: [],
  ...overrides,
});

describe("routeMap utils", () => {
  it("parses GeoJSON LineString as lat/lng pairs", () => {
    const json = JSON.stringify({
      type: "LineString",
      coordinates: [
        [-75.16, 39.95],
        [-75.15, 39.96],
      ],
    });
    expect(parseRouteGeometry(json)).toEqual([
      [39.95, -75.16],
      [39.96, -75.15],
    ]);
  });

  it("prefers geometry over stop coordinates for route path", () => {
    const route = baseRoute({
      route_geometry_json: JSON.stringify({
        type: "LineString",
        coordinates: [
          [-75.1, 40.0],
          [-75.0, 40.1],
        ],
      }),
      stops: [
        {
          stop_order: 1,
          stop_type: "driver_start",
          employee_id: 2,
          location_label: null,
          address: null,
          latitude: 39.0,
          longitude: -74.0,
          eta: null,
          ride_time_minutes: null,
        },
      ],
    });
    expect(routePath(route)).toEqual([
      [40.0, -75.1],
      [40.1, -75.0],
    ]);
  });

  it("falls back to ordered stops when geometry missing", () => {
    const stops: RouteStop[] = [
      {
        stop_order: 2,
        stop_type: "pickup",
        employee_id: 3,
        location_label: null,
        address: null,
        latitude: 39.96,
        longitude: -75.15,
        eta: null,
        ride_time_minutes: null,
      },
      {
        stop_order: 1,
        stop_type: "driver_start",
        employee_id: 2,
        location_label: null,
        address: null,
        latitude: 39.95,
        longitude: -75.16,
        eta: null,
        ride_time_minutes: null,
      },
    ];
    expect(stopsToPath(stops)).toEqual([
      [39.95, -75.16],
      [39.96, -75.15],
    ]);
  });

  it("assigns distinct colors per route order", () => {
    expect(routeColor(1)).not.toBe(routeColor(2));
  });

  it("labels stops by type", () => {
    const jobStop: RouteStop = {
      stop_order: 9,
      stop_type: "job_site",
      employee_id: null,
      location_label: "Site",
      address: null,
      latitude: null,
      longitude: null,
      eta: null,
      ride_time_minutes: null,
    };
    expect(stopMarkerKind(jobStop)).toBe("job");
    expect(stopMarkerLabel(jobStop, () => "X")).toBe("Job site");
  });
});
