#!/usr/bin/env python3
"""
Morning Traffic Checker
------------------------
Checks live, traffic-aware travel time for a fixed commute route using the
Google Maps Directions API, compares it against a "normal" baseline, and
sends a WhatsApp message (via CallMeBot) if the commute is significantly
worse than usual.

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

GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")
CALLMEBOT_PHONE = os.environ.get("CALLMEBOT_PHONE")          # e.g. "9715XXXXXXXX" (no + or spaces)
CALLMEBOT_APIKEY = os.environ.get("CALLMEBOT_APIKEY")        # obtained from CallMeBot opt-in

ORIGIN = os.environ.get("ORIGIN_ADDRESS", "Al Muwaihat 3, Ajman, United Arab Emirates")
DESTINATION = os.environ.get("DESTINATION_ADDRESS", "Arif & Bintoak Building, Zaa'beel St, Al Karama, Dubai, United Arab Emirates")
# Optional: bias the route through a specific point (e.g. the Mirdif City Centre
# exit onto Rebat Street) so Google doesn't silently reroute you elsewhere.
WAYPOINT = os.environ.get("WAYPOINT_ADDRESS", "City Centre Mirdif, Dubai, United Arab Emirates")

# Your normal/expected commute time in minutes under typical 6-9am traffic.
NORMAL_MINUTES = float(os.environ.get("NORMAL_MINUTES", "60"))

# How many EXTRA minutes over normal counts as "worse than usual" before
# alerting you. E.g. 15 means: alert if commute looks like 75+ minutes.
THRESHOLD_MINUTES = float(os.environ.get("THRESHOLD_MINUTES", "15"))

DIRECTIONS_URL = "https://maps.googleapis.com/maps/api/directions/json"
CALLMEBOT_URL = "https://api.callmebot.com/whatsapp.php"


def get_traffic_duration():
    """Query Google Directions API for current traffic-aware travel time."""
    if not GOOGLE_MAPS_API_KEY:
        raise RuntimeError("GOOGLE_MAPS_API_KEY is not set")
    if not DESTINATION:
        raise RuntimeError("DESTINATION_ADDRESS is not set")

    params = {
        "origin": ORIGIN,
        "destination": DESTINATION,
        "departure_time": "now",       # required to get duration_in_traffic
        "traffic_model": "best_guess",
        "key": GOOGLE_MAPS_API_KEY,
    }
    if WAYPOINT:
        params["waypoints"] = f"via:{WAYPOINT}"

    resp = requests.get(DIRECTIONS_URL, params=params, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    if data.get("status") != "OK":
        raise RuntimeError(f"Directions API error: {data.get('status')} - {data.get('error_message', '')}")

    route = data["routes"][0]
    # Sum duration_in_traffic across all legs (in case of waypoints)
    total_seconds = 0
    total_seconds_normal = 0
    for leg in route["legs"]:
        # duration_in_traffic falls back to duration if traffic data unavailable
        leg_traffic = leg.get("duration_in_traffic", leg["duration"])
        total_seconds += leg_traffic["value"]
        total_seconds_normal += leg["duration"]["value"]

    minutes_in_traffic = total_seconds / 60.0
    minutes_no_traffic = total_seconds_normal / 60.0
    summary_text = route["legs"][0].get("duration_in_traffic", route["legs"][0]["duration"])["text"]

    return minutes_in_traffic, minutes_no_traffic, summary_text


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
    print(f"[{now.isoformat()}] Checking traffic from '{ORIGIN}' to '{DESTINATION}'...")

    try:
        minutes_in_traffic, minutes_no_traffic, human_text = get_traffic_duration()
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
            f"Estimated commute: ~{minutes_in_traffic:.0f} min ({human_text})\n"
            f"That's {delta:.0f} min more than your usual {NORMAL_MINUTES:.0f} min.\n"
            f"Consider leaving earlier to make it to work by 8am."
        )
        print("ALERT: sending WhatsApp notification")
        send_whatsapp(message)
    else:
        print("Traffic is normal - no notification sent.")


if __name__ == "__main__":
    main()
