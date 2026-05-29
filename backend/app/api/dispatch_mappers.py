"""Dispatch response mappers shared by API and services."""

import json

from app.schemas.dispatch import RouteStopResponse, VehicleRouteResponse


def route_to_response(route) -> VehicleRouteResponse:
    warnings: list[str] = []
    if route.warning_json:
        try:
            warnings = json.loads(route.warning_json)
        except json.JSONDecodeError:
            warnings = []
    passenger_ids = [
        s.employee_id
        for s in sorted(route.stops, key=lambda x: x.stop_order)
        if s.stop_type == "pickup" and s.employee_id is not None
    ]
    return VehicleRouteResponse(
        id=route.id,
        job_id=route.job_id,
        driver_employee_id=route.driver_employee_id,
        vehicle_capacity=route.vehicle_capacity,
        passenger_ids=passenger_ids,
        route_order=route.route_order,
        total_duration_minutes=route.total_duration_minutes,
        total_distance_miles=route.total_distance_miles,
        arrival_time=route.arrival_time,
        is_late=route.is_late,
        google_maps_url=route.google_maps_url,
        route_geometry_json=route.route_geometry_json,
        reasoning=route.reasoning,
        warnings=warnings if isinstance(warnings, list) else [],
        stops=[
            RouteStopResponse(
                stop_order=s.stop_order,
                stop_type=s.stop_type,
                employee_id=s.employee_id,
                job_id=s.job_id,
                location_label=s.location_label,
                address=s.address,
                latitude=s.latitude,
                longitude=s.longitude,
                eta=s.eta,
                ride_time_minutes=s.ride_time_minutes,
            )
            for s in sorted(route.stops, key=lambda x: x.stop_order)
        ],
    )
