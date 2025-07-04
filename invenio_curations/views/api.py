# -*- coding: utf-8 -*-
#
# Copyright (C) 2024-2025 Graz University of Technology.
#
# Invenio-Curations is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""View functions for curations."""

from typing import cast

from flask import Blueprint, Flask


def create_curations_bp(app: Flask) -> Blueprint:
    """Create curations blueprint."""
    ext = app.extensions["invenio-curations"]
    return cast(Blueprint, ext.curations_resource.as_blueprint())
