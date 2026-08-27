#!/usr/bin/env python3
"""
Morning Traffic Checker
------------------------
Checks live, traffic-aware travel time for a fixed commute route using the
TomTom Routing API (free tier: 2,500 requests/day, no credit card required),
compares it against a "normal" baseline, and sends a WhatsApp message (via
CallMeBot) if the commute is significantly worse than usual.

Intended to run every weekday morning at 6:00 AM Gulf time via GitHub Actions
(see .github/workflows/traffic-check.yml), but can also be run manually or
via any other scheduler (cron, Windows Task Scheduler, etc.).

All configuration is read from environment variables so no secrets are
hardcoded in the script itself.
"""

import os
import sys
import requests
from datetime import datetime

# ---------------------------------------------------------------------------
# Configuration (set these as environment variables / GitHub Secrets)
# ---------------------------------------------------------------------------

TOMTOM_API_KEY = os.environ.get("TOMTOM_API_KEY")
CALLMEBOT_PHONE = os.environ.get("CALLMEBOT_PHONE")          # e.g. "9715XXXXXXXX" (no + or spaces)
CALLMEBOT_APIKEY = os.environ.get("CALLMEBOT_APIKEY")        # obtained from CallMeBot opt-in

# Coordinates as "lat,lon". Defaults are pre-filled for:
#   Origin      = Al Muwaihat 3, Ajman
#   Waypoint    = City Centre Mirdif (keeps routing via Mohammed Bin Zayed Rd -> Rebat St)
#   Destination = Arif & Bintoak Building, Al Karama, Dubai
ORIGIN = os.environ.get("ORIGIN_COORDS", "25.3665736,55.4900918")
WAYPOINT = os.environ.get("WAYPOINT_COORDS", "25.2160947,55.4080985")
DESTINATION = os.environ.get("DESTINATION_COORDS", "25.238249,55.3048201")

# Your normal/expected commute time in minutes under typical 6-9am traffic.
NORMAL_MINUTES = float(os.environ.get("NORMAL_MINUTES", "60"))

# How many EXTRA minutes over normal counts as "worse than usual" before
# alerting you. E.g. 15 means: alert if commute looks like 75+ minutes.
THRESHOLD_MINUTES = float(os.environ.get("THRESHOLD_MINUTES", "15"))

TOMTOM_URL_TEMPLATE = "https://api.tomtom.com/routing/1/calculateRoute/{locations}/json"
CALLMEBOT_URL = "https://api.callmebot.com/whatsapp.php"


def get_traffic_duration():
    """Query TomTom Routing API for current traffic-aware travel time."""
    if not TOMTOM_API_KEY:
        raise RuntimeError("TOMTOM_API_KEY is not set")

    locations = f"{ORIGIN}:{WAYPOINT}:{DESTINATION}"
    url = TOMTOM_URL_TEMPLATE.format(locations=locations)

    params = {
        "key": TOMTOM_API_KEY,
        "traffic": "true",
        "departAt": "now",
        "computeTravelTimeFor": "all",  # also returns no-traffic baseline
    }

    resp = requests.get(url, params=params, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    if "routes" not in data or not data["routes"]:
        raise RuntimeError(f"TomTom API returned no route: {data}")

    summary = data["routes"][0]["summary"]
    seconds_in_traffic = summary["travelTimeInSeconds"]
    seconds_no_traffic = summary.get("noTrafficTravelTimeInSeconds", seconds_in_traffic)

    minutes_in_traffic = seconds_in_traffic / 60.0
    minutes_no_traffic = seconds_no_traffic / 60.0

    return minutes_in_traffic, minutes_no_traffic


def send_whatsapp(message):
    """Send a WhatsApp message via CallMeBot's free personal API."""
    if not (CALLMEBOT_PHONE and CALLMEBOT_APIKEY):
        raise RuntimeError("CALLMEBOT_PHONE / CALLMEBOT_APIKEY not set")

    params = {
        "phone": CALLMEBOT_PHONE,
        "text": message,
        "apikey": CALLMEBOT_APIKEY,
    }
    resp = requests.get(CALLMEBOT_URL, params=params, timeout=20)
    resp.raise_for_status()
    print(f"CallMeBot response: {resp.text}")


def main():
    now = datetime.now()
    print(f"[{now.isoformat()}] Checking traffic from '{ORIGIN}' via '{WAYPOINT}' to '{DESTINATION}'...")

    try:
        minutes_in_traffic, minutes_no_traffic = get_traffic_duration()
    except Exception as e:
        print(f"ERROR checking traffic: {e}", file=sys.stderr)
        # Optionally notify you that the check itself failed, so you're never
        # left silently uninformed. Comment this out if you don't want that.
        try:
            send_whatsapp(f"⚠️ Traffic checker failed to run this morning: {e}")
        except Exception as e2:
            print(f"Also failed to send failure notice: {e2}", file=sys.stderr)
        sys.exit(1)

    delta = minutes_in_traffic - NORMAL_MINUTES
    print(f"Traffic time: {minutes_in_traffic:.0f} min | Free-flow time: {minutes_no_traffic:.0f} min "
          f"| Normal baseline: {NORMAL_MINUTES:.0f} min | Delta: {delta:+.0f} min")

    if delta >= THRESHOLD_MINUTES:
        message = (
            f"🚧 Heavier traffic than usual this morning!\n"
            f"Estimated commute: ~{minutes_in_traffic:.0f} min\n"
            f"That's {delta:.0f} min more than your usual {NORMAL_MINUTES:.0f} min.\n"
            f"Consider leaving earlier to make it to work by 8am."
        )
        print("ALERT: sending WhatsApp notification")
        send_whatsapp(message)
    else:
        print("Traffic is normal - no notification sent.")


if __name__ == "__main__":
    main()
