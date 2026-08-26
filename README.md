Morning Traffic Checker → WhatsApp Alert
Checks your Ajman → work commute every weekday at 6:00 AM (Gulf time) using
live Google Maps traffic data. If it's noticeably worse than your usual ~60
minutes, you get a WhatsApp message telling you to leave earlier. Runs
entirely in the cloud (GitHub Actions, free tier) — your PC doesn't need to
be on.
What you need to set up (one-time, ~15 minutes)
A free GitHub account (to host the code + run the free scheduler)
A Google Cloud API key (free tier covers this easily)
A CallMeBot WhatsApp opt-in (free, takes 1 minute)
---
Step 1 — Get a Google Maps API key
Go to https://console.cloud.google.com/ and sign in / create a project.
Enable the Directions API (APIs & Services → Library → search "Directions API" → Enable).
Go to APIs & Services → Credentials → Create Credentials → API key.
Copy the key. (Optional but recommended: click "Restrict key" → restrict it
to the Directions API only, so it can't be misused if leaked.)
Google requires a billing account to be linked, but you get $200/month
free credit — this script makes ~60 calls/month, costing well under $1.
You will not be charged unless you far exceed the free tier.
Step 2 — Get your WhatsApp API key from CallMeBot (free)
Save this number in your phone contacts: +34 644 62 79 61
Send it a WhatsApp message with exactly this text: `I allow callmebot to send me messages`
You'll get a reply with your personal API key (a number). Save it.
Note your own WhatsApp phone number in international format with no `+`
or spaces, e.g. `9715XXXXXXXX`.
Step 3 — Create the GitHub repository
Go to https://github.com/new, create a new private repository (e.g. `traffic-checker`).
Upload the two files from this project into it, keeping the folder structure:
`check_traffic.py`
`.github/workflows/traffic-check.yml`
(Easiest way: on the repo page, click "Add file → Upload files" and drag both,
making sure the workflow file lands in `.github/workflows/`.)
Step 4 — Add your secrets and variables
In your repo: Settings → Secrets and variables → Actions
Secrets tab (sensitive — click "New repository secret" for each):
Name	Value
`GOOGLE_MAPS_API_KEY`	the key from Step 1
`CALLMEBOT_PHONE`	your WhatsApp number, e.g. `9715XXXXXXXX`
`CALLMEBOT_APIKEY`	the key CallMeBot texted you
Variables tab (non-sensitive — click "Variables" sub-tab, "New repository variable"):
Name	Value
`ORIGIN_ADDRESS`	`Al Muwaihat 3, Ajman, United Arab Emirates`
`DESTINATION_ADDRESS`	`Arif & Bintoak Building, Zaa'beel St, Al Karama, Dubai, United Arab Emirates`
`WAYPOINT_ADDRESS`	`City Centre Mirdif, Dubai, United Arab Emirates` (keeps the route via Mohammed Bin Zayed Rd → Rebat St, matching how you actually drive)
`NORMAL_MINUTES`	`60`
`THRESHOLD_MINUTES`	`15`
These are now also the script's built-in defaults, so even if you skip setting
these four as repo Variables, it will still work correctly out of the box —
you only must set the three Secrets (API keys).
You can tweak `NORMAL_MINUTES` and `THRESHOLD_MINUTES` any time without touching code —
e.g. lower the threshold to `10` if you want earlier warnings.
Step 5 — Test it
Go to the Actions tab in your repo → "Morning Traffic Check" → Run workflow
(this uses the `workflow_dispatch` trigger, so you don't have to wait until 6am).
Check the run logs to confirm it fetched a traffic time, and check your WhatsApp
if traffic conditions happen to be bad.
Once that works, it will run automatically every weekday at 6:00 AM Gulf time —
no further action needed.
How it decides to alert you
It compares the live traffic-aware travel time to your `NORMAL_MINUTES`
baseline (default 60). If it's `THRESHOLD_MINUTES` (default 15) or more above
that, you get a WhatsApp message with the estimated time and a nudge to leave
early. If a run fails (e.g. API quota issue), it also tries to WhatsApp you a
failure notice so you're never silently left without your morning check.
Adjusting the route
Google's Directions API automatically picks the fastest current route, which
should normally match your usual Mohammed Bin Zayed Road → Rebat Street path
since that already is the fastest option. If you ever notice it's routing you
somewhere unexpected, set `WAYPOINT_ADDRESS` to a landmark on your route (e.g.
near the Mirdif City Centre exit) to force it through that point.
