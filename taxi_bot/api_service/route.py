"""Openrouteservice client."""
import logging
import uuid

import openrouteservice
import plotly.graph_objects as go
from haversine import haversine
from openrouteservice import convert, exceptions

logger = logging.getLogger(__name__)


def _zoom(min_lat, max_lat, min_lon, max_lon):
    """Get (empirical) zoom parameter depending from route rectangle.

    :param float min_lat: Minimal route latitude
    :param float max_lat: Maximal route latitude
    :param float min_lon: Minimal route longitude
    :param float max_lon: Maximal route longitude
    :return float: zoom
    """
    max_distance = haversine((max_lat, max_lon), (min_lat, min_lon))
    zoom_map = [
        (1, 13.7),
        (2, 13.2),
        (3, 12.6),
        (4, 12.4),
        (5, 12.2),
        (6, 11.8),
        (7, 11.5),
        (8, 11.3),
        (9, 10.5),
        (10, 10.2),
        (25, 9),
        (100, 8.5),
        (300, 8),
    ]
    result = 8
    for distance, zoom in zoom_map:
        if max_distance < distance:
            result = zoom
            break
    logger.debug("rectangle: max=%s max_distance=%s", (max_lat, max_lon), (min_lat, min_lon))
    logger.debug("image: zoom=%s max_distance=%s", zoom, max_distance)
    return result


def _save_route_image(to_customer_route, ride_route, path):
    """Create and save image with route.

    :param [dict(lat=float, lon=float})] to_customer_route: route from driver to customer.
    :param [dict(lat=float, lon=float})] ride_route: route from start customer location to finish location
    :param path str: Result image local path
    """
    fig = go.Figure(
        go.Scattermapbox(
            mode="lines",
            name="Route to customer",
            lon=to_customer_route["lon"],
            lat=to_customer_route["lat"],
            line={"width": 4, "color": "green"},
        )
    )
    fig.add_trace(
        go.Scattermapbox(
            mode="lines",
            name="Ride route",
            lon=ride_route["lon"],
            lat=ride_route["lat"],
            line={"width": 3, "color": "blue"},
        )
    )
    max_lon = max(ride_route["lon"] + to_customer_route["lon"])
    min_lon = min(ride_route["lon"] + to_customer_route["lon"])
    max_lat = max(ride_route["lat"] + to_customer_route["lat"])
    min_lat = min(ride_route["lat"] + to_customer_route["lat"])
    center = {"lon": (max_lon + min_lon) / 2, "lat": (max_lat + min_lat) / 2}
    zoom = _zoom(min_lat, max_lat, min_lon, max_lon)
    mapbox = {"center": center, "style": "open-street-map", "zoom": zoom}
    fig.update_layout(margin={"l": 0, "t": 0, "b": 0, "r": 0}, mapbox=mapbox)
    fig.update(layout_showlegend=False)
    logger.debug("Image path: %s", path)
    fig.write_image(path)


class _RouteClient:
    """Create and save route from driver to customer and from customer to finish location.

    See https://openrouteservice.org/ service for create route
    See https://github.com/GIScience/openrouteservice-py client library for openrouteservice
    See https://plotly.com/python/ create geo-map image with routes

    Route colors:
      green: route from driver to customer
      blue: route from start customer location to finish location
    """

    def __init__(self):
        self.client = None
        self.upload_image_path = None
        self.image_storage_url = None

    def set_config(self, upload_image_path, image_storage_url, open_route_service_key):
        """Set configuration.

        :param str upload_image_path: Local path for image storage
        :param str image_storage_url: Image storage url
        :param str open_route_service_key: See https://openrouteservice.org/dev/#/api-docs
        """
        self.client = openrouteservice.Client(key=open_route_service_key)
        self.upload_image_path = upload_image_path
        self.image_storage_url = image_storage_url

    def get_ors_route(
        self,
        start_latitude,
        start_longitude,
        finish_latitude,
        finish_longitude,
    ):
        """Create route.

        :param float start_latitude: start latitude
        :param float start_longitude: start longitude
        :param float finish_latitude: finish latitude
        :param float finish_longitude: finish longitude
        :return [dict(lat=float, lon=float})], dict(duration, distance))
        """
        coords = (
            (start_longitude, start_latitude),
            (finish_longitude, finish_latitude),
        )
        data = None
        try:
            data = self.client.directions(coords)
        except exceptions.ApiError as e:
            logger.error("ORS ApiError: %s", e)
        except exceptions.Timeout as e:
            logger.error("ORS Timeout: %s", e)
        except exceptions.HTTPError as e:
            logger.error("ORS HTTPError: %s", e)

        # Skip if received any ORS error.
        if not data:
            return None
        geometry = data["routes"][0]["geometry"]
        coordinates = convert.decode_polyline(geometry)["coordinates"]
        routes = {
            "lon": [c[0] for c in coordinates],
            "lat": [c[1] for c in coordinates],
        }
        summary = {
            "duration": round(data["routes"][0]["summary"].get("duration", 0) / 60),
            "distance": round(data["routes"][0]["summary"].get("distance", 0) / 1000, 2),
        }
        return routes, summary

    def create_route_image(self, to_customer_route, ride_route):
        """Create route image.

        :param [dict(lat=float, lon=float})] to_customer_route: route to customer
        :param [dict(lat=float, lon=float})] ride_route: ride route
        :return str: image url
        """
        image_name = f"{uuid.uuid4()}.png"
        image_path = f"{self.upload_image_path}/{image_name}"
        image_url = f"{self.image_storage_url}/{image_name}"
        _save_route_image(to_customer_route, ride_route, image_path)
        return image_url


route_client = _RouteClient()
