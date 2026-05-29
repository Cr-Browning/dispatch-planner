import { useEffect, useMemo, useState } from "react";
import { MapContainer, TileLayer, Polyline, CircleMarker, Popup, useMap } from "react-leaflet";
import type { RouteStop, VehicleRoute } from "../api/types";
import { formatDisplayTime } from "../utils/dates";
import {
  boundsFromPaths,
  routeColor,
  routePath,
  stopMarkerKind,
  stopMarkerLabel,
  type LatLng,
} from "../utils/routeMap";
import "leaflet/dist/leaflet.css";

interface RouteMapPreviewProps {
  routes: VehicleRoute[];
  employeeName: (id: number) => string;
  jobName: (jobId: number) => string;
}

function FitBounds({ points }: { points: LatLng[] }) {
  const map = useMap();
  useEffect(() => {
    if (points.length === 0) {
      return;
    }
    if (points.length === 1) {
      map.setView(points[0], 13);
      return;
    }
    map.fitBounds(points, { padding: [32, 32] });
  }, [map, points]);
  return null;
}

function markerStyle(route: VehicleRoute, stop: RouteStop) {
  const color = routeColor(route.route_order);
  const kind = stopMarkerKind(stop);
  if (kind === "job") {
    return { fillColor: "#1e293b", radius: 9 };
  }
  if (kind === "driver") {
    return { fillColor: color, radius: 8 };
  }
  return { fillColor: color, radius: 7 };
}

function RouteMapInner({ routes, employeeName, jobName }: RouteMapPreviewProps) {
  const paths = useMemo(
    () => routes.map((route) => routePath(route)).filter((p) => p.length >= 2),
    [routes]
  );
  const allPoints = useMemo(() => boundsFromPaths(paths) ?? [], [paths]);
  const defaultCenter: LatLng = [39.9526, -75.1652];

  if (routes.length === 0 || allPoints.length === 0) {
    return (
      <div className="map-preview empty">
        No route coordinates available to display on the map.
      </div>
    );
  }

  return (
    <div className="map-preview">
      <MapContainer
        center={allPoints[0] ?? defaultCenter}
        zoom={12}
        className="map-canvas"
        scrollWheelZoom={false}
        dragging
        doubleClickZoom
        zoomControl
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <FitBounds points={allPoints} />
        {routes.map((route) => {
          const path = routePath(route);
          const color = routeColor(route.route_order);
          if (path.length < 2) {
            return null;
          }
          return (
            <Polyline
              key={`line-${route.id}`}
              positions={path}
              pathOptions={{ color, weight: 4, opacity: 0.85 }}
            />
          );
        })}
        {routes.flatMap((route) =>
          route.stops
            .filter((s) => s.latitude != null && s.longitude != null)
            .map((stop) => {
              const style = markerStyle(route, stop);
              return (
                <CircleMarker
                  key={`${route.id}-${stop.stop_order}-${stop.stop_type}`}
                  center={[stop.latitude as number, stop.longitude as number]}
                  radius={style.radius}
                  pathOptions={{
                    color: "#ffffff",
                    weight: 2,
                    fillColor: style.fillColor,
                    fillOpacity: 0.95,
                  }}
                >
                  <Popup>
                    <strong>{stopMarkerLabel(stop, employeeName)}</strong>
                    <br />
                    Vehicle {route.route_order} — {jobName(route.job_id)}
                    {stop.eta && (
                      <>
                        <br />
                        ETA: {formatDisplayTime(stop.eta)}
                      </>
                    )}
                  </Popup>
                </CircleMarker>
              );
            })
        )}
      </MapContainer>
      <div className="map-legend">
        {routes.map((route) => (
          <div key={route.id} className="map-legend-item">
            <span
              className="map-legend-swatch"
              style={{ background: routeColor(route.route_order) }}
            />
            <span>
              Vehicle {route.route_order} — {jobName(route.job_id)}
              {route.is_late ? " (late)" : ""}
            </span>
            {route.google_maps_url && (
              <a href={route.google_maps_url} target="_blank" rel="noreferrer">
                Google Maps
              </a>
            )}
          </div>
        ))}
        <p className="map-legend-note">
          Read-only preview (OpenStreetMap). Pins: driver start, pickups, job site. Lines use saved
          geometry when available.
        </p>
      </div>
    </div>
  );
}

export function RouteMapPreview(props: RouteMapPreviewProps) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    setMounted(true);
  }, []);
  if (!mounted) {
    return <div className="map-preview loading">Loading map…</div>;
  }
  return <RouteMapInner {...props} />;
}
