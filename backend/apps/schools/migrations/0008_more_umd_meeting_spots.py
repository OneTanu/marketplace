"""More UMD meetup spots, named "Building · Spot" so two students can't end up on opposite
sides of a wall. Whether a spot is indoors is `is_indoor`, shown as a tag in the apps."""

from django.db import migrations

INDOOR_SAFETY = "Meet while the building is open and stay where other people are present."
OUTDOOR_SAFETY = "Choose daylight when possible and stay where other people are walking by."

RENAMED = {
    "Stamp Student Union lobby": "Stamp Student Union · Main lobby",
    "McKeldin Library front entrance": "McKeldin Library · Front entrance",
}

# (name, directions, is_indoor, sort_order). A building that works both inside and outside
# gets two spots, so each has its own directions and sellers can approve one but not the other.
NEW_SPOTS = [
    (
        "Stamp Student Union · Outside main doors",
        "Just outside Stamp's main entrance doors.",
        False,
        15,
    ),
    (
        "McKeldin Library · Inside lobby",
        "Inside McKeldin Library's main entrance, in the first-floor lobby.",
        True,
        25,
    ),
    (
        "Hornbake Library · Inside lobby",
        "Inside Hornbake Library's main entrance, in the ground-floor lobby.",
        True,
        65,
    ),
    (
        "ESJ · Main lobby",
        "Inside the Edward St. John Learning and Teaching Center, in the open lobby by the main doors.",
        True,
        30,
    ),
    (
        "McKeldin Mall · Testudo statue",
        "At the Testudo statue in front of McKeldin Library, facing the Mall.",
        False,
        40,
    ),
    (
        "Van Munching Hall · Atrium",
        "Inside the Smith School of Business, in the main atrium.",
        True,
        50,
    ),
    (
        "Hornbake Library · Plaza entrance",
        "On the plaza outside Hornbake Library's main entrance.",
        False,
        60,
    ),
    (
        "251 North · Main entrance",
        "Outside the main entrance of the 251 North dining hall. No meal swipe needed.",
        False,
        70,
    ),
    (
        "Iribe Center · Main lobby",
        "Inside the Brendan Iribe Center, in the ground-floor lobby by the main doors.",
        True,
        80,
    ),
    (
        "Yahentamitsi Dining Hall · Main entrance",
        "Outside the main entrance of Yahentamitsi Dining Hall. No meal swipe needed.",
        False,
        90,
    ),
    (
        "South Campus Dining Hall · Main entrance",
        "Outside the main entrance of South Campus Dining Hall. No meal swipe needed.",
        False,
        100,
    ),
    (
        "Kim Engineering Building · Atrium",
        "Inside the Jeong H. Kim Engineering Building, in the main atrium.",
        True,
        110,
    ),
    (
        "Physical Sciences Complex · Atrium",
        "Inside the Physical Sciences Complex, in the main atrium.",
        True,
        120,
    ),
    (
        "Eppley Recreation Center · Front lobby",
        "Inside the ERC's front doors, before the card-swipe gates.",
        True,
        130,
    ),
    (
        "The Clarice · Main lobby",
        "Inside the Clarice Smith Performing Arts Center, in the main lobby.",
        True,
        140,
    ),
]


def add_spots(apps, schema_editor):
    School = apps.get_model("schools", "School")
    MeetingSpot = apps.get_model("schools", "MeetingSpot")
    umd = School.objects.filter(slug="umd").first()
    if umd is None:
        return
    for old, new in RENAMED.items():
        MeetingSpot.objects.filter(school=umd, name=old).update(name=new)
    MeetingSpot.objects.bulk_create(
        [
            MeetingSpot(
                school=umd,
                name=name,
                directions=directions,
                safety_note=INDOOR_SAFETY if is_indoor else OUTDOOR_SAFETY,
                is_indoor=is_indoor,
                sort_order=sort_order,
            )
            for name, directions, is_indoor, sort_order in NEW_SPOTS
        ],
        ignore_conflicts=True,
    )


def remove_spots(apps, schema_editor):
    MeetingSpot = apps.get_model("schools", "MeetingSpot")
    MeetingSpot.objects.filter(
        school__slug="umd", name__in=[name for name, *_ in NEW_SPOTS]
    ).delete()
    for old, new in RENAMED.items():
        MeetingSpot.objects.filter(school__slug="umd", name=new).update(name=old)


class Migration(migrations.Migration):
    dependencies = [
        ("schools", "0007_meetingspot"),
    ]

    operations = [migrations.RunPython(add_spots, remove_spots)]
