"""Listings background jobs. Procrastinate finds this module by name (tasks.py) when Django
starts; the work itself lives in services."""

from procrastinate.contrib.django import app

from . import services


# Named explicitly so queued jobs still run if this module moves.
@app.task(name="listings.make_photo_thumbnail")
def make_photo_thumbnail(photo_id: int) -> None:
    services.make_photo_thumbnail(photo_id)
