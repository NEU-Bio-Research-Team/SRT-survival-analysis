# Prompt for a browser agent: capture the TRAINS Online NTM request

*Paste the block below into a browser-driving agent that has access to a session
already signed in to TRAINS Online. Everything above the `---` is context for
the human; the prompt itself starts after it.*

**Why this exists.** UNCTAD TRAINS Online is the only source of non-tariff
measures at HS6 × year. Its front end talks to `api-trains2.unctad.org`, whose
reference endpoints are open but whose one data endpoint,
`POST /denormalisedMeasures`, requires a signed-in bearer token. We do not need
the agent to download the data — we need it to capture **one working request**
precisely enough that the pull can be scripted for every country and year.

**The part agents usually get wrong:** capturing a single request is not enough.
Without a second request that differs in exactly one filter, there is no way to
tell which body field carries the country and which carries the year. The prompt
below therefore insists on two captures and a diff.

---

## THE PROMPT

You are working in a browser that is already signed in to UNCTAD TRAINS Online
(`https://trainsonline.unctad.org`). Your job is to capture, precisely and
verbatim, the network request that the site uses to fetch non-tariff measure
(NTM) records, so that the pull can later be scripted. **Do not try to download
the whole dataset yourself.**

### Step 0 — check whether a bulk export exists first

Look through the site for any "Download", "Bulk download", "Export", "Data
download" or "Researcher file" option. If one exists:

- Use it. Select **NTM / measures data**, at **HS6** product detail, **all
  reporting (imposing) countries**, and **all available years**. CSV, Excel or
  STATA `.dta` are all fine.
- Save the downloaded file to `~/Downloads/` and report its exact filename,
  size, and the filter settings you chose.
- Then **stop** — you do not need the rest of these steps.

If no bulk export exists, or it only allows one country at a time, continue.

### Step 1 — make the site issue a real data request

1. Open DevTools (F12) → **Network** tab. Enable "Preserve log". Filter on
   `denormalised` or on `api-trains2`.
2. In the site's NTM search/browse interface, run a query for **one single
   country and one single year** — pick **Viet Nam** (or Indonesia, which is
   known to have many collection years) and any year from 2015 onward.
3. Wait for results to appear on screen.

### Step 2 — capture the first request

Find the request to `api-trains2.unctad.org/denormalisedMeasures` (method
`POST`). Right-click it → **Copy** → **Copy as cURL** (use "bash" if offered,
not "cmd" and not "PowerShell").

Save that string to a file at exactly this path:

```
~/.trains_request_1.txt
```

Then restrict its permissions: `chmod 600 ~/.trains_request_1.txt`

### Step 3 — capture a SECOND request that differs in exactly one filter

This step is the important one. Go back to the interface and run the query
again, changing **only one thing** — ideally the **country**, keeping the same
year. (If the country cannot be changed, change only the year instead, and say
so in your report.)

Copy that request as cURL the same way and save it to:

```
~/.trains_request_2.txt
```

`chmod 600` it as well.

### Step 4 — record the response shape

For the first request, open its **Response** (or **Preview**) tab and record:

- the **first two records** of the response, in full, field names included —
  paste them into your report, since they contain no credentials;
- the **total number of records** returned;
- whether the response or the request body shows any sign of **pagination**
  (fields named anything like `page`, `pageSize`, `offset`, `limit`, `skip`,
  `take`, `totalCount`, `totalRecords`);
- whether the record carries, in some form: an **HS6 product code**, a **year**,
  the **imposing/reporting country**, the **affected partner country**, and the
  **NTM measure code** (a MAST chapter letter such as `A`, `B`, `E` followed by
  digits).

### Step 5 — note the filters the interface actually offers

List every filter the NTM search screen exposes (for example: reporter country,
partner country, year, HS chapter/heading/code, NTM chapter, measure type,
in-force status). This tells us what the API is capable of, which decides how
the scripted pull is shaped.

### Step 6 — note the time

Record the **exact local date and time** you captured the requests. The bearer
token is short-lived, so whoever replays it needs to know how old it is.

---

## Rules

- **Do not paste the cURL strings, the `Authorization` header, or any token into
  your chat reply, into a commit, or into any file inside a git repository.**
  They belong only in the two `~/.trains_request_*.txt` files. Everything else
  in your report is safe to write out.
- Do not change any account setting, do not alter the user's saved queries, and
  do not submit anything that looks like a bulk export job unless Step 0 told
  you to.
- Do not retry a failing request more than twice, and leave at least a second
  between requests. This is a public-good research database, not a load target.
- If the site logs you out or a request returns 401/403, say so plainly rather
  than working around it.

## What to report back

A short written report containing:

1. Whether a bulk export exists (Step 0), and if so the saved filename and size.
2. Confirmation that `~/.trains_request_1.txt` and `~/.trains_request_2.txt`
   exist, and **which single filter differs between them** (state it explicitly:
   "request 1 is Viet Nam 2020, request 2 is Indonesia 2020").
3. The first two response records, verbatim.
4. The total record count and whatever you found about pagination.
5. The list of filters the interface offers.
6. The capture timestamp.

Do not include the token or the cURL strings anywhere in that report.
