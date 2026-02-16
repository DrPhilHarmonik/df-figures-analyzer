# analyze_figures.py

Command-line utility to analyze a **Dwarf Fortress** *legends.xml* file
and identify the most “interesting” historical figures based on events,
kills, relationships, special statuses, skills, affiliations, and
artifact ownership. The script prints a ranked Top 20 list and a full
timeline for either the top-ranked figure or a specified figure ID.

## Features

- Parses a *legends.xml* file and extracts:

  - Sites
  - Entities
  - Artifacts (including artifact holders)
  - Historical figures (metadata, relationships, affiliations, skills,
    spheres, site links)
  - Historical events (mentions of historical figures, kills, event
    types)
  - Historical event collections (e.g., wars/battles/attacks)

- Computes an “interestingness” score per historical figure

- Prints:

  - Top 20 ranked figures with key summary details
  - Full chronological timeline for a selected figure (top \#1 by
    default, or a provided ID)
  - Relevant event collections that include events from the selected
    figure’s timeline

## Requirements

- Python 3.x
- Standard library only (no external dependencies)

## Installation

No installation required. Save the script as *analyze_figures.py* and
run it with Python.

## Usage

### Top 20 figures and timeline for the \#1 figure

*python3 analyze_figures.py \<legends_xml_file\>*

### Timeline for a specific figure by ID

*python3 analyze_figures.py \<legends_xml_file\> \<figure_id\>*

## Output

### Top 20 list

Prints 20 figures ranked by score. For each figure, output includes:

- Name and ID

- Race and caste

- Birth year and (if applicable) death year

- Tags (when detected):

  - DEITY
  - FORCE
  - VAMPIRE
  - NECROMANCER
  - MEGABEAST

- Summary counts:

  - Event mentions
  - Kills credited to the figure
  - Relationship links
  - Positions held (entity links of type *position* / *former_position*)

- Optional detail sections (when present):

  - Spheres
  - Artifacts held
  - Top skills (up to 3, by total IP)
  - Top event types involving the figure (up to 5)

### Timeline (detail output)

For the selected figure (top-ranked by default, or the provided ID),
prints:

- Header with identity and life status

- If dead and the killer is known: “Killed by …”

- Spheres (if any)

- Relationship list (up to 20)

- Entity affiliations (all recorded *entity_link* entries)

- Full chronological event timeline, with ID resolution for:

  - *site_id* → site name
  - entity/civ fields → entity name
  - *\*hfid\** fields → historical figure name (+ race)
  - *artifact_id* → artifact name

- Event collections that include any events from the figure’s timeline
  (up to 30 shown)

## Scoring Model

Each historical figure receives a score based on the following
components:

- **Event mentions:** *min(event_mentions \* 2, 500)*

- **Kills credited:** *kills \* 15*

- **Special statuses:**

  - Vampire: *+80*
  - Necromancer: *+100*
  - Deity: *+120*
  - Force: *+90*
  - Megabeast (by race): *+70*

- **Relationships (hf links):** *min(relationship_links \* 3, 100)*

- **Positions held (entity links):** *+20* per link type in:

  - *position*
  - *former_position*
  - *position_claim*

- **Artifacts held:** *+30* per artifact where *holder_hfid* matches the
  figure

- **Spheres:** *+10* per sphere

- **Skills:** *min((num_skills \* 2) + (max_total_ip // 5000), 80)*

- **Site links:** *min(site_links \* 5, 50)*

- **Entity links (all types):** *min(entity_links \* 3, 60)*

- **Death recorded (death_year != -1):** *+5*

- **Killed by someone (victim appears in killed_by map):** *+5*

The score is used only for ranking output.

## Time Formatting

Events provide *year* and *seconds72*. When *seconds72* is available
(\>= 0), the script converts it to a calendar date using:

- 12 months, 28 days per month
- Dwarf Fortress month names (*Granite* through *Obsidian*)

If conversion fails or *seconds72* is unavailable, the script prints
*Year \<year\>*.

## Limitations

- Loads the full XML into memory (reads, cleans, then parses). Large
  legends files may require significant RAM.
- Event mention detection is based on a fixed set of historical-figure
  ID fields (*HF_FIELDS*). If DF introduces fields not included in this
  set, they will not be counted as mentions.
- Kill attribution is based on *slayer_hfid* and *hf died* events where
  the victim ID is found in the event’s *hfid* field.
- Event collections are not expanded through nested sub-collections;
  only direct *event* entries in each collection are used.

## Troubleshooting

- **File not found**

  - Verify the path passed as the first argument points to an existing
    file.

- **Parse errors**

  - The script removes control characters before parsing, but malformed
    or truncated XML files may still fail. Ensure the legends file is
    complete and valid.

## License

No license is included. Add a license file if you plan to redistribute.
