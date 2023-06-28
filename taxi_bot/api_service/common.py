"""Common methods."""

import functools
import logging

from flask import jsonify, send_from_directory
from marshmallow import fields
from sqlalchemy import exc
from webargs import flaskparser, validate

from taxi_bot.api_service.schema import app

logger = logging.getLogger(__name__)

use_body = functools.partial(flaskparser.use_args, location="json", error_status_code=400)

LocationField = {
    "latitude": fields.Float(required=True, validate=[validate.Range(min=-90, max=90)]),
    "longitude": fields.Float(required=True, validate=[validate.Range(min=-180, max=180)]),
}


def calculate_price(distance):
    """Calculate the cost of a ride.

       cost_per_km = 1 # 1$ per km
       cost = distance * cost_per_km

    :param float distance: ride distance
    :return int: route price in dollars
    """
    return round(distance)


def resp(status=200, data=None):
    """Return response for http status."""
    logger.debug("response: status=%s, data=%s", status, data)
    return jsonify(data or {}), status


def not_found(detail):
    """Return response for 404 (not found) http status."""
    return resp(404, {"detail": detail})


def conflict(error):
    """Return response for 409 (conflict) http status."""
    return resp(409, {"detail": error})


@app.errorhandler(exc.IntegrityError)
def storage_error(error):
    """Return response for 409 (conflict) http status."""
    return conflict(str(error))


@app.route("/images/<filename>")
def download_file(filename):
    """Download file."""
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)
