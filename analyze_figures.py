#!/usr/bin/env python3
"""Analyze a Dwarf Fortress legends XML file to find the most interesting historical figures.

Usage:
    python3 analyze_figures.py <file>           # Top 20 figures + timeline for #1
    python3 analyze_figures.py <file> <id>      # Timeline for specific figure by ID
"""

import dataclasses
import xml.etree.ElementTree as ET
from collections import defaultdict, Counter
import re
import sys
import os


@dataclasses.dataclass
class WorldData:
    sites: dict
    entities: dict
    artifacts: dict
    artifact_by_holder: dict
    hf_info: dict
    event_counts: Counter
    kill_counts: Counter
    killed_by: dict
    event_type_counts: dict
    all_events: dict
    hfid_to_events: dict
    collections: list

# Fields in events that reference historical figure IDs
HF_FIELDS = {
    'hfid', 'slayer_hfid', 'hfid1', 'hfid2', 'group_hfid', 'snatcher_hfid',
    'changee_hfid', 'changer_hfid', 'woundee_hfid', 'wounder_hfid',
    'doer_hfid', 'target_hfid', 'attacker_hfid', 'defender_hfid',
    'hist_fig_id', 'body_hfid', 'hfid_target', 'hfid_attacker',
    'hfid_defender', 'trickster_hfid', 'cover_hfid', 'student_hfid',
    'teacher_hfid', 'trainer_hfid', 'seeker_hfid',
}

DF_MONTHS = [
    "Granite", "Slate", "Felsite", "Hematite", "Malachite", "Galena",
    "Limestone", "Sandstone", "Timber", "Moonstone", "Opal", "Obsidian"
]


def clean_xml(filepath):
    """Read XML file and strip invalid control characters."""
    print("Cleaning XML of invalid characters...")
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', content)


def parse_all(xml_string):
    """Parse the full XML tree and extract all relevant data."""
    print("Parsing full XML tree...")
    root = ET.fromstring(xml_string)
    print("XML parsed!")
    return root


def extract_sites(root):
    sites = {}
    for site in root.findall(".//sites/site"):
        sites[site.findtext("id", "")] = site.findtext("name", "unknown")
    print(f"  {len(sites)} sites")
    return sites


def extract_artifacts(root):
    artifacts = {}
    artifact_by_holder = defaultdict(list)
    for art in root.findall(".//artifacts/artifact"):
        aid = art.findtext("id", "")
        item_el = art.find("item")
        item_name = item_el.findtext("name_string", "") if item_el is not None else ""
        holder = art.findtext("holder_hfid", "")
        artifacts[aid] = item_name
        if holder and holder != "-1":
            artifact_by_holder[holder].append(item_name or "artifact#" + aid)
    print(f"  {len(artifacts)} artifacts")
    return artifacts, artifact_by_holder


def extract_entities(root):
    entities = {}
    for ent in root.findall(".//entities/entity"):
        entities[ent.findtext("id", "")] = ent.findtext("name", "unnamed")
    print(f"  {len(entities)} entities")
    return entities


def extract_historical_figures(root):
    print("Parsing historical figures...")
    hf_info = {}
    for hf in root.findall(".//historical_figures/historical_figure"):
        hfid = hf.findtext("id", "")
        ai_list = [ai.text for ai in hf.findall("active_interaction") if ai.text]
        el_list = [{"type": el.findtext("link_type", ""), "eid": el.findtext("entity_id", "")}
                   for el in hf.findall("entity_link")]
        hl_list = [{"type": hl.findtext("link_type", ""), "hfid": hl.findtext("hfid", "")}
                   for hl in hf.findall("hf_link")]
        sk_list = [{"skill": sk.findtext("skill", ""), "ip": int(sk.findtext("total_ip", "0"))}
                   for sk in hf.findall("hf_skill")]
        sp_list = [s.text for s in hf.findall("sphere") if s.text]
        sl_list = [{"type": sl.findtext("link_type", ""), "sid": sl.findtext("site_id", "")}
                   for sl in hf.findall("site_link")]
        race = hf.findtext("race", "")
        assoc = hf.findtext("associated_type", "")
        hf_info[hfid] = {
            "name": hf.findtext("name", "unnamed"), "race": race,
            "caste": hf.findtext("caste", ""),
            "birth_year": hf.findtext("birth_year", "?"), "death_year": hf.findtext("death_year", "-1"),
            "associated_type": assoc, "active_interactions": ai_list, "entity_links": el_list,
            "hf_links": hl_list, "skills": sk_list, "spheres": sp_list, "site_links": sl_list,
            "vamp": any("VAMPIRE" in a.upper() for a in ai_list),
            "necro": any("NECROMANCER" in a.upper() or "RAISE" in a.upper() for a in ai_list),
            "deity": assoc == "DEITY", "force": assoc == "FORCE",
            "mega": race.upper() in {
                "DRAGON", "HYDRA", "COLOSSUS_BRONZE", "CYCLOPS", "ETTIN", "GIANT", "ROC", "TITAN"
            },
        }
    print(f"  {len(hf_info)} figures")
    return hf_info


def extract_events(root, hf_fields):
    print("Parsing events...")
    event_counts = Counter()
    kill_counts = Counter()
    killed_by = {}
    event_type_counts = defaultdict(Counter)
    all_events = {}
    hfid_to_events = defaultdict(list)

    for evt in root.findall(".//historical_events/historical_event"):
        eid = evt.findtext("id", "")
        etype = evt.findtext("type", "")
        ev_data = {
            "id": eid, "type": etype,
            "year": evt.findtext("year", "0"),
            "sec": evt.findtext("seconds72", "-1")
        }
        mentioned = set()
        slayer = victim = None

        for child in evt:
            if child.tag not in ("id", "type", "year", "seconds72"):
                ev_data[child.tag] = child.text or ""
            if child.text and child.tag in hf_fields:
                try:
                    v = int(child.text)
                    if v >= 0:
                        mentioned.add(str(v))
                except ValueError:
                    pass
            if child.tag == "slayer_hfid" and child.text:
                slayer = child.text
            if child.tag == "hfid" and etype == "hf died" and child.text:
                victim = child.text

        all_events[eid] = ev_data
        for hfid in mentioned:
            event_counts[hfid] += 1
            event_type_counts[hfid][etype] += 1
            hfid_to_events[hfid].append(eid)

        if slayer and slayer != "-1":
            kill_counts[slayer] += 1
        if victim and slayer and slayer != "-1":
            killed_by[victim] = slayer

    print(f"  {len(all_events)} events")
    return event_counts, kill_counts, killed_by, event_type_counts, all_events, hfid_to_events


def extract_collections(root):
    print("Parsing event collections...")
    collections = []
    for coll in root.findall(".//historical_event_collections/historical_event_collection"):
        c = {}
        coll_events = []
        for child in coll:
            if child.tag == "event":
                coll_events.append(child.text or "")
            else:
                c[child.tag] = child.text or ""
        c["_events"] = coll_events
        collections.append(c)
    print(f"  {len(collections)} collections")
    return collections


def score_figures(world):
    """Score each historical figure by 'interestingness'."""
    print("\nScoring figures...")
    scores = {}
    for hfid, hf in world.hf_info.items():
        s = min(world.event_counts.get(hfid, 0) * 2, 500)
        s += world.kill_counts.get(hfid, 0) * 15
        if hf["vamp"]: s += 80
        if hf["necro"]: s += 100
        if hf["deity"]: s += 120
        if hf["force"]: s += 90
        if hf["mega"]: s += 70
        s += min(len(hf["hf_links"]) * 3, 100)
        s += sum(20 for el in hf["entity_links"]
                 if el["type"] in ("position", "former_position", "position_claim"))
        s += len(world.artifact_by_holder.get(hfid, [])) * 30
        s += len(hf["spheres"]) * 10
        if hf["skills"]:
            s += min(len(hf["skills"]) * 2 + max(x["ip"] for x in hf["skills"]) // 5000, 80)
        s += min(len(hf["site_links"]) * 5, 50)
        s += min(len(hf["entity_links"]) * 3, 60)
        if hf["death_year"] != "-1":
            s += 5
        if hfid in world.killed_by:
            s += 5
        scores[hfid] = s
    return scores


def resolve_hf(hfid, hf_info):
    if hfid == "-1" or not hfid:
        return None
    info = hf_info.get(hfid, {})
    name = info.get("name", "fig#" + hfid)
    race = info.get("race", "")
    return name.title() + " (" + race + ")" if race else name.title()


def resolve_site(sid, sites):
    if sid == "-1" or not sid:
        return None
    return sites.get(sid, "site#" + sid)


def resolve_entity(eid, entities):
    if eid == "-1" or not eid:
        return None
    return entities.get(eid, "entity#" + eid)


def format_time(year, sec):
    ts = "Year " + str(year)
    if sec >= 0:
        try:
            doy = sec // 1200 + 1
            mo = min((doy - 1) // 28 + 1, 12)
            day = (doy - 1) % 28 + 1
            ts = f"Year {year}, {day} {DF_MONTHS[mo - 1]}"
        except (ValueError, IndexError):
            pass
    return ts


def print_top20(top20, world):
    print("\n" + "=" * 80)
    print("TOP 20 MOST INTERESTING HISTORICAL FIGURES")
    print("=" * 80)
    for rank, (hfid, score) in enumerate(top20, 1):
        hf = world.hf_info[hfid]
        alive = "ALIVE" if hf["death_year"] == "-1" else "died yr " + hf["death_year"]
        tags = []
        if hf["deity"]: tags.append("DEITY")
        if hf["force"]: tags.append("FORCE")
        if hf["vamp"]: tags.append("VAMPIRE")
        if hf["necro"]: tags.append("NECROMANCER")
        if hf["mega"]: tags.append("MEGABEAST")
        tag_str = " [" + ",".join(tags) + "]" if tags else ""
        kills = world.kill_counts.get(hfid, 0)
        evts = world.event_counts.get(hfid, 0)
        rels = len(hf["hf_links"])
        posns = sum(1 for el in hf["entity_links"] if el["type"] in ("position", "former_position"))
        print(f"\n  #{rank}: {hf['name'].title()} (ID:{hfid}) SCORE:{score}")
        print(f"    {hf['race']} {hf['caste']}, born yr {hf['birth_year']}, {alive}{tag_str}")
        print(f"    Events:{evts} Kills:{kills} Relations:{rels} Positions:{posns}")
        if hf["spheres"]:
            print("    Spheres: " + ", ".join(hf["spheres"]))
        if world.artifact_by_holder.get(hfid):
            print("    Artifacts: " + ", ".join(world.artifact_by_holder[hfid]))
        if hf["skills"]:
            tsk = sorted(hf["skills"], key=lambda x: x["ip"], reverse=True)[:3]
            print("    Top skills: " + ", ".join(
                x["skill"] + "(" + str(x["ip"]) + ")" for x in tsk))
        if hfid in world.event_type_counts:
            tev = world.event_type_counts[hfid].most_common(5)
            print("    Top events: " + ", ".join(
                t + "(" + str(c) + ")" for t, c in tev))


def print_timeline(winner_id, world):
    w = world.hf_info[winner_id]
    print("\n\n" + "=" * 80)
    print("FULL TIMELINE: " + w["name"].title() + " (ID:" + winner_id + ")")
    print("  " + w["race"] + " " + w["caste"] + ", born year " + w["birth_year"])
    if w["death_year"] != "-1":
        print("  Died year " + w["death_year"])
        if winner_id in world.killed_by:
            print("  Killed by: " + (resolve_hf(world.killed_by[winner_id], world.hf_info) or "unknown"))
    else:
        print("  Status: ALIVE")
    if w["spheres"]:
        print("  Spheres: " + ", ".join(w["spheres"]))
    if w["hf_links"]:
        print("  Relationships:")
        for hl in w["hf_links"][:20]:
            print("    - " + hl["type"] + ": " + (resolve_hf(hl["hfid"], world.hf_info) or "?"))
    if w["entity_links"]:
        print("  Entity affiliations:")
        for el in w["entity_links"]:
            print("    - " + el["type"] + ": " + (resolve_entity(el["eid"], world.entities) or "?"))
    print("=" * 80)

    # Sort events chronologically
    event_ids = world.hfid_to_events.get(winner_id, [])
    events_sorted = []
    for eid in event_ids:
        ev = world.all_events.get(eid, {})
        try:
            yr = int(ev.get("year", 0))
        except ValueError:
            yr = 0
        try:
            sc = int(ev.get("sec", -1))
        except ValueError:
            sc = -1
        events_sorted.append((yr, sc, eid, ev))
    events_sorted.sort()

    for yr, sc, eid, ev in events_sorted:
        etype = ev.get("type", "?")
        ts = format_time(yr, sc)
        details = []
        for k, v in sorted(ev.items()):
            if k in ("id", "type", "year", "sec") or v == "-1" or v == "" or v == "-1,-1":
                continue
            display = v
            if k == "site_id":
                r = resolve_site(v, world.sites)
                if r:
                    display = r
            elif "entity" in k or "civ" in k:
                r = resolve_entity(v, world.entities)
                if r:
                    display = r.title()
            elif "hfid" in k.lower():
                r = resolve_hf(v, world.hf_info)
                if r:
                    display = r
            elif k == "artifact_id":
                a = world.artifacts.get(v, "")
                if a:
                    display = a
            details.append(k.replace("_", " ").title() + ": " + display)
        print("\n  [" + ts + "] " + etype.upper())
        for d in details:
            print("      " + d)

    # Relevant event collections
    top_event_set = set(world.hfid_to_events.get(winner_id, []))
    rel_colls = [c for c in world.collections if top_event_set.intersection(set(c.get("_events", [])))]
    if rel_colls:
        print("\n\n  EVENT COLLECTIONS involving " + w["name"].title() + ":")
        for c in rel_colls[:30]:
            ctype = c.get("type", "?")
            cname = c.get("name", "")
            sy = c.get("start_year", "?")
            ey = c.get("end_year", "?")
            label = ctype.title()
            if cname:
                label += ": " + cname.title()
            label += " (years " + sy + "-" + ey + ")"
            for ekey in ("aggressor_ent_id", "defender_ent_id", "attacking_enid", "defending_enid"):
                ei = c.get(ekey, "")
                if ei and ei != "-1":
                    en = resolve_entity(ei, world.entities) or ei
                    nice = ekey.replace("_ent_id", "").replace("_enid", "").replace("_", " ").strip().title()
                    label += " [" + nice + ": " + en.title() + "]"
            print("    - " + label)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 analyze_figures.py <legends_xml_file> [figure_id]")
        sys.exit(1)

    xml_file = sys.argv[1]
    if not os.path.isfile(xml_file):
        print(f"ERROR: File not found: {xml_file}")
        sys.exit(1)

    target_id = sys.argv[2] if len(sys.argv) > 2 else None

    content = clean_xml(xml_file)
    root = parse_all(content)
    del content

    artifacts, artifact_by_holder = extract_artifacts(root)
    event_counts, kill_counts, killed_by, event_type_counts, all_events, hfid_to_events = \
        extract_events(root, HF_FIELDS)
    world = WorldData(
        sites=extract_sites(root),
        entities=extract_entities(root),
        artifacts=artifacts,
        artifact_by_holder=artifact_by_holder,
        hf_info=extract_historical_figures(root),
        event_counts=event_counts,
        kill_counts=kill_counts,
        killed_by=killed_by,
        event_type_counts=event_type_counts,
        all_events=all_events,
        hfid_to_events=hfid_to_events,
        collections=extract_collections(root),
    )
    root.clear()

    scores = score_figures(world)
    top20 = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:20]

    print_top20(top20, world)

    # Use target_id if specified, otherwise use the #1 figure
    winner_id = target_id if target_id else top20[0][0]
    if winner_id not in world.hf_info:
        print(f"\nERROR: Figure ID '{winner_id}' not found!")
        return

    print_timeline(winner_id, world)

    print("\n\nANALYSIS COMPLETE")


if __name__ == "__main__":
    main()
