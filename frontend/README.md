# Movie Trailer Maker — Frontend

Plain **HTML / CSS / JavaScript** frontend (no framework) for the Movie Trailer Maker system. It collects source material and creative inputs, sends them to a backend API for processing, and displays the generated trailer along with a creative brief and edit decision list (EDL).

---

## Folder Structure

```
frontend/
├── index.html
├── README.md
├── css/
│   ├── style.css
│   ├── components.css
│   └── output.css
├── js/
│   ├── main.js
│   ├── inputs.js
│   ├── category.js
│   ├── api.js
│   ├── render-output.js
│   └── validate.js
├── assets/
│   ├── icons/
│   └── placeholder/
└── data/
    └── sample-trailer.json
```

---

## Inputs

| # | Input | Format / File Type |
|---|-------|----------------------|
| 1 | Episode package | Video upload (`.mp4`/`.mov`), single or multiple clips, with stable timecodes |
| 2 | Scene descriptions | Text area or JSON upload (human and/or AI descriptions per scene) |
| 3 | Dialogue & subtitles | Source dialogue text + 2 dialect subtitle files (`.srt`/`.vtt`) |
| 4 | Rating policies | File upload (`.json`/`.pdf`) — rules for Family / Young Adult / Regional |
| 5 | Contracts | File upload (`.json`/`.pdf`) — actor, music, territory, promo-use restrictions |
| 6 | Audience profiles | File upload or fetched from backend |
| 7 | Historic performance | File upload (`.json`/`.csv`) or fetched from backend |
| 8 | Cost sheet | File upload (`.json`/`.csv`) or fetched from backend |

**Category selection** (after inputs):
- Family viewers / Young Adult viewers / Dialect-region viewers
- If Dialect-region is selected → free-text field to type the dialect name

---

## Output

1. **Playable video** — rendered generated trailer
2. **Creative brief + Edit Decision List (EDL)**, built from the trailer JSON schema:

```json
{
  "trailer_id": "string",
  "audience": "string",
  "duration_seconds": 0,
  "audience_promise": "string",
  "segments": [
    {
      "source_in": "HH:MM:SS.ms",
      "source_out": "HH:MM:SS.ms",
      "video": "string",
      "audio": "string",
      "subtitle": "string",
      "reason": "string",
      "evidence": ["string"],
      "risk_flags": []
    }
  ],
  "validation": { "status": "PASS_WITH_WARNINGS" }
}
```

Rendered as:
- Overview (audience, objective, central promise, emotional journey)
- Segment-by-segment EDL table (timecodes, video/audio/subtitle, reason, evidence, risk flags)
- Compliance/validation status banner
- Warnings, assumptions, required approvals
- Estimated cost + fallback plan

---

## Processing State

While waiting on the backend response, the UI shows:
- A progress indicator (spinner/progress bar)
- Stage-by-stage status text (uploading → validating → generating → compliance checks → building brief → finalizing)
- A disabled "Processing…" submit button
- An error state with a "Try Again" option if the request fails or times out

---

## Backend Integration

All API calls live in `js/api.js`. Placeholder endpoints are used until the real backend URL is provided:

```js
// js/api.js (placeholder — replace with real backend URL)
const API_BASE = "/api";

async function submitTrailerRequest(formData) {
  const res = await fetch(`${API_BASE}/generate-trailer`, {
    method: "POST",
    body: formData
  });
  return res.json();
}
```

---

## Getting Started

1. Open `index.html` in a browser, or serve the `frontend/` folder with any static server.
2. Fill in the 8 input sections and select a category.
3. Submit — the UI will show a processing state, then render the output once the backend responds.

No build step, no dependencies — plain HTML/CSS/JS.