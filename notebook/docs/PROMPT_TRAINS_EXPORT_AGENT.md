# Prompt B2 for a browser agent: export the TRAINS NTM data country by country

*Use this when the API route is rate-limited. The first prompt
([PROMPT_TRAINS_BROWSER_AGENT.md](PROMPT_TRAINS_BROWSER_AGENT.md)) captured a
request; it worked, and proved no login is needed. What blocks the bulk pull is
Cloudflare: `pageSize` is capped at 20 and the host returns error 1015 after
about six requests, so several thousand pages is neither practical nor polite.*

**A real browser session is not rate-limited the same way** — it carries the
Cloudflare clearance cookie and a full browser fingerprint. So the portal's own
Export button can do in one action what the API would need dozens of requests
for.

**Step 1 is cheap and might make the rest unnecessary** — read it before
starting the exports.

---

## THE PROMPT

You are working in a browser on UNCTAD TRAINS Online
(`https://trainsonline.unctad.org`). There is no login requirement for this
data. Your job is to export the non-tariff measure (NTM) records, one file per
imposing country, so they can be processed offline.

### Step 1 — first, check whether a clearance cookie exists (2 minutes)

Open DevTools (F12) → **Network**. Run any NTM search in the interface. Find the
request to `api-trains2.unctad.org/denormalisedMeasures` and look at its
**Request Headers**.

- Report whether a **`cookie:`** header is present, and if so, whether it
  contains a name starting with **`cf_clearance`** or `__cf`.
- If it is present, right-click the request → **Copy → Copy as cURL (bash)**,
  save it to `~/.trains_request_3.txt`, and `chmod 600` it. Then **report back
  and stop** — that cookie may be enough to make the scripted pull work, which
  is far less work for you than the exports below.
- If there is no `cookie:` header at all, continue to Step 2.

### Step 2 — export, one imposing country at a time

For each country in the list at the end of this prompt:

1. In the NTM search interface, set **Imposing country** to that country.
2. Set **affected countries** to **all** (do not narrow it).
3. Set **products** to **all** (do not narrow to a chapter or code).
4. Leave every other filter unset — no NTM chapter, no date range, no
   in-force-only restriction. We want everything.
5. Before exporting, turn **on** every available column, and in particular make
   sure these are included, because they are off by default and they are the
   ones that matter most:
   - **HS code**
   - **Implementation date**
   - **Repeal date**
   - **Years of data collection**
   - **NTM code**
   - **Affected countries**
6. Use the **Export** button (Excel or CSV, whichever is offered).
7. Save the file as `~/Downloads/trains_ntm/<ISO3>.xlsx` (or `.csv`), using the
   three-letter code from the list — for example `IDN.xlsx`, `EUN.xlsx`.

**Pace yourself: wait about 10 seconds between exports.** If an export fails or
the site shows a rate-limit or "too many requests" message, stop for two
minutes, then resume from the country that failed. Do not run exports in
parallel tabs.

**Keep a running note** of: countries exported, countries that returned an
error, and any country where the interface says there is no data. An empty
result is a real answer and should be recorded as such, not retried repeatedly.

### Step 3 — report

Report:
1. The Step 1 answer about the cookie (this is the single most useful thing).
2. How many files you exported, and the total size of `~/Downloads/trains_ntm/`.
3. Any country that errored or returned no data, by ISO3 code.
4. Which columns the export actually contained — paste the header row of one
   file.
5. Roughly how long one export took, and whether you hit any rate limiting.

## Rules

- Do not paste any `cookie:` value, `Authorization` header, or token into your
  chat reply or into any file inside a git repository. `~/.trains_request_3.txt`
  is the only place a captured request belongs.
- Do not change account settings or saved queries.
- If the site becomes unresponsive or starts refusing requests, stop and report
  rather than working around it. This is a public-good research database.
- If a country's export would exceed what the interface will produce in one go,
  say so and move on — do not try to split it into dozens of partial exports
  without reporting first.

## The countries

Export these 134. The three-letter codes are ISO3, except `EUN`, which is the
European Union as a bloc — it is listed because EU measures are filed at union
level, exactly as EU tariffs are, and skipping it would leave all 27 member
states empty.

```
ALB ARE ARG ARM ATG AUS AUT AZE BDI BEL BEN BFA BGD BGR BHR BIH BLR BOL BRA
BRB BRN BWA CAN CHL CHN CIV CMR COG COL COM CPV CRI CYP CZE DEU DMA DNK DZA
ECU EGY ESP EST ETH EUN FIN FJI FRA GAB GEO GHA GMB GRC GRD GTM GUY HKG HND
HRV HUN IDN IND IRL ISL ISR ITA JAM JOR JPN KAZ KEN KGZ KHM KOR KWT LBN LKA
LSO LTU LUX LVA MAR MDA MEX MKD MLI MLT MOZ MRT MUS MWI MYS NAM NER NGA NIC
NLD NOR NZL OMN PAK PAN PER PHL POL PRT PRY QAT ROU RUS RWA SAU SEN SGP SLB
SLV SUR SVK SVN SWE SWZ SYC TGO THA TON TTO TUN TUR TZA UGA URY USA VNM ZAF
ZMB
```

If the interface names a country slightly differently (for example "Viet Nam"
rather than "Vietnam", or "Türkiye" rather than "Turkey"), use the interface's
name and keep the ISO3 code in the filename.
