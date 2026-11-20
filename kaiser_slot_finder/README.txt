KAISER APPOINTMENT SLOT FINDER (Windows)
=========================================

IMPORTANT
- This is a search/notification tool only. It does not book appointments.
- Your pasted curl contained live authentication/session material. Sign out of Kaiser,
  sign back in, and use fresh values. Do not send cookies/tokens to anyone or commit
  config.json to Git.
- The script currently has only DUB configured because that is the only facility ID
  established by your request. Do not guess facility IDs. Add other IDs after obtaining
  them from the Kaiser website's Network tab.

SETUP
1. Install Python 3.10+.
2. Open PowerShell in this folder and run:
      py -m pip install requests winotify
3. Edit config.json:
   - Put current x-apiKey, x-IBM-Client-Id and Cookie values in headers.
   - Add current sessionId and pcpServiceState to payload_template.json.
   - Keep credentials only on your own PC.
4. Run:
      py kaiser_finder.py

WHAT IT DOES
- Queries the /v1/slots endpoint every 10 minutes.
- Searches today through the next 30 days.
- Starts with Dublin (DUB); add verified facility IDs to config.json.
- Saves raw JSON responses under raw_responses/ for troubleshooting.
- Saves already-seen possible slots in seen_slots.sqlite3 and alerts only for new ones.
- Logs activity to kaiser_finder.log.

IMPORTANT LIMITATION
The exact response schema has not been supplied yet. The built-in parser is deliberately
generic and may not recognize Kaiser's actual slot objects. On the first run, inspect
raw_responses/*.json. If it finds no slots, provide ONE response JSON with all personal
and session data removed; the parser can then be adapted to the actual schema.

SESSION EXPIRY
Kaiser may expire or rotate session cookies, access tokens, sessionId, or pcpServiceState.
A 401/403 or authentication error usually means you must sign in again and refresh the
local values. Do not try to bypass MFA, access controls, rate limits, or bot protections.

FACILITY EXPANSION
Use the Kaiser appointment page normally. In browser Developer Tools > Network, inspect
the facility/location search requests or the /slots request after selecting another
medical center. Record the actual facilityId and facilityName. Add a line such as:
    {"id": "VERIFIED_ID", "name": "Verified Medical Center"}
to the facilities array. Do not infer IDs from city names.

PRIVACY
config.json contains credentials. Keep it private. Consider restricting file access to
your Windows account. Delete it securely when no longer needed.
