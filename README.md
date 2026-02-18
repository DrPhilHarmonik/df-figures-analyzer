# analyze_figures.py

Command-line utility to analyze a **Dwarf Fortress** *legends.xml* file
and identify the most "interesting" historical figures based on events,
kills, relationships, special statuses, skills, affiliations, and
artifact ownership.

## Requirements

- Python 3.x
- [`defusedxml`](https://pypi.org/project/defusedxml/) (optional but recommended — falls back to `xml.etree.ElementTree` if not installed)

```
pip install defusedxml
```

## Usage

```
python3 analyze_figures.py <file> [options]
```

| Argument | Description |
|---|---|
| `file` | Path to the legends XML file |
| `-f`, `--figure ID` | Historical figure ID to show a timeline for (default: top-ranked figure) |
| `-n`, `--top N` | Number of top figures to display (default: `20`) |
| `--format text\|json` | Output format (default: `text`) |

Progress messages (loading, parsing, extraction counts) are written to
**stderr**. Analysis output goes to **stdout**, so they can be separated:

```bash
# Clean output only
python3 analyze_figures.py legends.xml 2>/dev/null

# JSON to a file, progress visible in terminal
python3 analyze_figures.py legends.xml --format json > out.json
```

### Examples

```bash
# Top 20 figures + timeline for the #1 figure
python3 analyze_figures.py legends.xml

# Top 10 figures only
python3 analyze_figures.py legends.xml -n 10

# Full timeline for figure ID 1234
python3 analyze_figures.py legends.xml -f 1234

# JSON output, piped through a formatter
python3 analyze_figures.py legends.xml --format json 2>/dev/null | python3 -m json.tool
```

## Output

### Text mode

**Top-N list** — one entry per figure, including:

- Name, ID, and interestingness score
- Race, caste, birth year, and status (alive or death year)
- Tags: `DEITY`, `FORCE`, `VAMPIRE`, `NECROMANCER`, `MEGABEAST`
- Counts: event mentions, kills, relationship links, positions held
- Spheres, artifacts held, top skills (up to 3 by total IP), top event types (up to 5)

**Figure timeline** — for the selected figure:

- Header: identity, life/death status, killer if known
- Spheres, relationships (up to 20), entity affiliations
- Full chronological event list with resolved names:
  - `site_id` → site name
  - entity/civ fields → entity name
  - `*hfid*` fields → figure name and race
  - `artifact_id` → artifact name
- Related event collections (wars, battles, etc.) that include events from this figure's timeline (up to 30)

### JSON mode

```json
{
  "top_figures": [
    {
      "rank": 1,
      "id": "...",
      "name": "...",
      "race": "...",
      "caste": "...",
      "birth_year": "...",
      "death_year": "...",
      "score": 0,
      "kills": 0,
      "events": 0,
      "relations": 0,
      "positions": 0,
      "tags": [],
      "spheres": [],
      "artifacts": [],
      "top_skills": [{"skill": "...", "ip": 0}]
    }
  ],
  "timeline": {
    "id": "...",
    "name": "...",
    "race": "...",
    "caste": "...",
    "birth_year": "...",
    "death_year": "...",
    "killed_by": null,
    "spheres": [],
    "relationships": [{"type": "...", "figure": "..."}],
    "entity_links": [{"type": "...", "entity": "..."}],
    "events": [
      {
        "id": "...",
        "type": "...",
        "year": 0,
        "timestamp": "Year 100, 1 Granite",
        "details": {}
      }
    ],
    "collections": [{"type": "...", "name": "...", "start_year": "...", "end_year": "..."}]
  }
}
```

`events[].details` keeps raw IDs (no name resolution) for machine consumption.
`timeline` is `null` if no figure was selected.

## Scoring model

Each historical figure receives a score used only for ranking:

| Component | Points |
|---|---|
| Event mentions | `min(mentions × 2, 500)` |
| Kills credited | `kills × 15` |
| Vampire | +80 |
| Necromancer | +100 |
| Deity | +120 |
| Force | +90 |
| Megabeast (by race) | +70 |
| Relationship links | `min(links × 3, 100)` |
| Positions held (position / former_position / position_claim) | +20 each |
| Artifacts held | +30 each |
| Spheres | +10 each |
| Skills | `min((count × 2) + (max_ip // 5000), 80)` |
| Site links | `min(links × 5, 50)` |
| Entity links (all types) | `min(links × 3, 60)` |
| Death year recorded | +5 |
| Appears in killed-by map | +5 |

## Time formatting

Events carry `year` and `seconds72`. When `seconds72 >= 0` the script
converts it to a DF calendar date (12 months × 28 days, named *Granite*
through *Obsidian*). If conversion fails it falls back to `Year <year>`.

## Limitations

- Loads the full XML into memory (clean → parse). Very large legends
  files may use significant RAM.
- HF-field detection relies on the fixed `HF_FIELDS` set. Fields added
  in newer DF versions may not be counted as figure mentions.
- Kill attribution uses `slayer_hfid` on `hf died` events only.
- Event collections are not expanded through nested `eventcol`
  references; only direct `event` children are used.

## Troubleshooting

**File not found** — verify the path passed as the first argument.

**XML parse errors** — the script strips control characters before
parsing, but truncated or otherwise malformed files may still fail.
Ensure the legends export completed successfully.
