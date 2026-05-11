#!/usr/bin/env python3
"""One-shot script: apply the round-2 audit findings.

The 20-agent round-2 audit of cities.txt surfaced more non-cities that
slipped through round 1. This script flips `loc_type` directly on each
of those files. It is not a reusable classifier — it's a list of
specific decisions made by reviewing each agent's output.

Borderline cases the audit flagged but that are arguably real small
settlements (Vezelay, Medjugorje, Mount Abu, Bowness, etc.) are kept
as city and not listed here.
"""

import re
import sys
from pathlib import Path

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"

FRONTMATTER_RE = re.compile(r"^---\n(.*?\n)---\n", re.DOTALL)
# Note: use [ \t]* on both sides — \s* would consume the trailing newline
# in MULTILINE mode and squash loc_type onto the closing --- marker.
LOC_TYPE_RE = re.compile(r"^loc_type:[ \t]*(\S+)[ \t]*$", re.MULTILINE)

# (path, target_loc_type) pairs.
CHANGES: list[tuple[str, str]] = [
    # --- Chunk 00 ---
    ("asia/thailand/kohsamui", "region"),
    ("asia/indonesia/sumatra/laketoba", "feature"),
    ("northamerica/thecaribbean/anguilla", "region"),
    ("europe/greece/corfu", "region"),
    ("australiaandpacific/cookislands/rarotonga", "region"),
    # --- Chunk 01 ---
    ("southamerica/peru/machupicchu", "feature"),
    ("northamerica/mexico/chichenitza", "feature"),
    ("africa/zimbabwe/victoriafalls", "feature"),
    ("europe/armenia/ani", "feature"),
    ("europe/greece/mycenae", "feature"),
    ("southamerica/ecuador/amazonbasin", "region"),
    ("asia/israel/negev", "region"),
    ("europe/unitedkingdom/england/south_east/the_new_forest", "feature"),
    ("northamerica/unitedstates/california/losangeles/beverlyhills", "neighbourhood"),
    ("asia/japan/tokyo/shinjuku", "neighbourhood"),
    ("southamerica/ecuador/galapagosislands/san_cristobal_island", "region"),
    # --- Chunk 02 ---
    ("europe/hungary/lakebalaton", "feature"),
    ("africa/botswana/okavangodelta", "feature"),
    ("asia/jordan/deadsea", "feature"),
    ("northamerica/costarica/corcovado", "feature"),
    ("europe/unitedkingdom/scotland/glencoe", "feature"),
    ("europe/unitedkingdom/scotland/edinburgh/newtown_1", "neighbourhood"),
    # --- Chunk 03 ---
    ("asia/myanmar/inlelake", "feature"),
    ("australiaandpacific/australia/newsouthwales/sydney/bondibeach", "neighbourhood"),
    ("europe/unitedkingdom/scotland/iona", "region"),
    ("europe/iceland/westmanislands", "region"),
    ("northamerica/unitedstates/california/ventura_county_ca", "region"),
    ("northamerica/unitedstates/california/losangeles/marinadelrey", "neighbourhood"),
    ("northamerica/unitedstates/florida/marcoisland", "feature"),
    ("africa/southafrica/transkei", "region"),
    ("northamerica/unitedstates/newyorkstate/newyork/queens", "neighbourhood"),
    ("australiaandpacific/tonga/vavau_group", "region"),
    # --- Chunk 04 ---
    ("asia/china/huang_shan", "feature"),
    ("europe/spain/galicia/ribeira_sacra_vall", "region"),
    ("europe/croatia/trogirska_riviera", "region"),
    ("northamerica/mexico/coppercanyon", "feature"),
    ("asia/turkey/pamukale", "feature"),
    ("northamerica/unitedstates/utah/canyonlands", "feature"),
    # --- Chunk 05 ---
    ("africa/zimbabwe/lakekariba", "feature"),
    ("asia/china/xinjiangprovince/hanaslake", "feature"),
    ("europe/greece/meteora", "feature"),
    ("northamerica/unitedstates/texas/houston/galvestonisland", "feature"),
    ("australiaandpacific/newzealand/milfordsound", "feature"),
    # --- Chunk 06 ---
    ("northamerica/unitedstates/apalachiantrail", "feature"),
    ("northamerica/unitedstates/washington/mtrainiernp", "feature"),
    ("asia/nepal/royal_bardia_national_park", "feature"),
    ("africa/djibouti/lakeassal", "feature"),
    ("southamerica/venezuela/maracaibo/maracaibolake", "feature"),
    ("europe/italy/liguria/varatellavalley", "region"),
    ("europe/france/midi/pyrenees/picdumidi", "feature"),
    ("northamerica/unitedstates/pennsylvania/delawarecounty", "region"),
    ("europe/armenia/lori_marz", "region"),
    ("asia/indonesia/flores", "region"),
    # --- Chunk 07 ---
    ("africa/ivorycoast/tainationalpark", "feature"),
    ("asia/vietnam/cucphuong", "feature"),
    ("southamerica/paraguay/granchaco", "region"),
    ("northamerica/unitedstates/newjersey/longbeachisland", "feature"),
    ("europe/norway/geirangerfjord", "feature"),
    ("asia/thailand/khao_takiab_beach", "feature"),
    ("europe/italy/campania/parcodelcilento", "feature"),
    ("australiaandpacific/marshallislands/enewetokatoll", "feature"),
    ("africa/djibouti/lakeabbe", "feature"),
    # --- Chunk 08 ---
    ("northamerica/canada/alberta/lake_louise", "feature"),
    ("northamerica/unitedstates/maine/katahdin", "feature"),
    ("northamerica/unitedstates/wyoming/windrivercanyon", "feature"),
    ("europe/unitedkingdom/channel_islands_crown_dependencies", "region"),
    # --- Chunk 09 ---
    ("africa/tanzania/olduvaigorge", "feature"),
    ("northamerica/belize/turneffeislands", "feature"),
    ("asia/indonesia/krakatoa", "feature"),
    ("asia/iran/persepolis", "feature"),
    ("europe/italy/liguria/finalevalley", "region"),
    ("northamerica/unitedstates/michigan/picturedrock", "feature"),
    ("northamerica/unitedstates/oregon/craterlake", "feature"),
    ("europe/italy/lazio/pontineislands", "feature"),
    ("northamerica/unitedstates/newyorkstate/lakegeorge", "feature"),
    # --- Chunk 10 ---
    ("asia/mongolia/lakekhovsgol", "feature"),
    ("northamerica/unitedstates/california/deserts/joshuatree", "feature"),
    ("northamerica/unitedstates/california/highsierra/monolake", "feature"),
    ("asia/kyrgyzstan/alaarchagorge", "feature"),
    ("northamerica/costarica/poas", "feature"),
    ("europe/spain/catalonia/montserrat", "feature"),
    ("southamerica/brazil/chapada_dos_veadeiros", "feature"),
    ("australiaandpacific/newzealand/north_island/taranaki", "region"),
    ("asia/malaysia/sabah", "region"),
    ("northamerica/unitedstates/hawaii/molokai", "region"),
    ("northamerica/unitedstates/california/deserts/palmspringsarea", "region"),
    # --- Chunk 11 ---
    ("southamerica/peru/tambopata", "feature"),
    ("asia/china/sichuanprovince/jiuzhaigou", "feature"),
    ("africa/egypt/karnak", "feature"),
    ("southamerica/brazil/abrolhos", "feature"),
    ("europe/croatia/kornati_national_park", "feature"),
    ("africa/malawi/mulanje_mountains", "feature"),
    ("southamerica/bolivia/laketiticaca", "feature"),
    ("africa/malawi/lakemalawi", "feature"),
    ("africa/tanzania/laketanganyika", "feature"),
    ("northamerica/unitedstates/colorado/colorado_national_monument", "feature"),
    ("europe/unitedkingdom/england/south_east/ridgeway", "feature"),
    ("europe/finland/lapland", "region"),
    ("northamerica/unitedstates/washington/yakima_valley", "region"),
    ("asia/malaysia/kelantan", "region"),
    ("asia/saudiarabia/asir", "region"),
    ("australiaandpacific/newzealand/south_island/marlborough", "region"),
    ("northamerica/unitedstates/ohio/cuyahogavalley", "region"),
    ("northamerica/unitedstates/newyorkstate/statenisland", "neighbourhood"),
    ("australiaandpacific/australia/newsouthwales/nationalparks", "feature"),
    # --- Chunk 12 ---
    ("asia/thailand/koh_talu_island/koh_talu", "feature"),
    ("europe/unitedkingdom/england/birmingham_and_west_midlands/malvern_hills", "feature"),
    ("europe/poland/zakopane/morskieoko", "feature"),
    ("northamerica/canada/ontario/point_pelee_and_pelee_island", "feature"),
    ("australiaandpacific/australia/newsouthwales/surry_hills", "neighbourhood"),
    ("europe/unitedkingdom/england/leeds_sheffield_and_yorkshire/calderdale", "region"),
    ("northamerica/thecaribbean/dominica/caribterritory", "region"),
    ("northamerica/unitedstates/california/orangecounty/trabucocanyon", "region"),
    # --- Chunk 13 ---
    ("europe/france/midi/pyrenees/lac_des_bouillouses", "feature"),
    ("asia/india/kerala/periyar", "feature"),
    ("europe/unitedkingdom/england/gloucestershire/severn_bore", "feature"),
    ("asia/myanmar/kyaiktiyo", "feature"),
    ("africa/namibia/sossusvlei", "feature"),
    ("europe/italy/campania/parco_nazionale_del_cilento_e_del_vallo_di_diano", "feature"),
    ("europe/lithuania/hill_of_crosses", "feature"),
    ("northamerica/honduras/lakeyojoa", "feature"),
    ("europe/armenia/kotayk_marz/hrazdan/tsaghkadzor_ski_resort", "feature"),
    ("africa/mauritius/casela", "feature"),
    ("europe/greece/delos", "feature"),
    ("northamerica/unitedstates/wisconsin/milwaukee/bayview", "neighbourhood"),
    ("europe/croatia/losinjisland", "region"),
    ("europe/croatia/lopud_island", "region"),
    ("europe/norway/hallingdal", "region"),
    ("europe/belgium/hainaut", "region"),
    ("northamerica/canada/newbrunswick/campobello_island", "region"),
    ("africa/kenya/thecoast/northofmombasa", "region"),
    ("northamerica/thecaribbean/puertorico/elyunque", "feature"),
    ("europe/croatia/korcula/palagruza_island", "region"),
    # --- Chunk 14 ---
    ("africa/cameroon/benouepark", "feature"),
    ("africa/kenya/nationalparksandreserves/lakebogorianp", "feature"),
    ("northamerica/unitedstates/alabama/lake_martin", "feature"),
    # --- Chunk 15 ---
    ("europe/france/midi/cevennes/cirque_des_navacelles", "feature"),
    ("northamerica/unitedstates/california/big_sur", "feature"),
    ("northamerica/costarica/chirripo", "feature"),
    ("africa/tanzania/tarangire_np", "feature"),
    ("asia/india/uttaranchal/hemkunt", "feature"),
    ("australiaandpacific/marshallislands/arnoatoll", "region"),
    # --- Chunk 16 ---
    ("africa/seychelles/fregateisland", "feature"),
    ("northamerica/unitedstates/kentucky/redrivergorge", "feature"),
    ("northamerica/unitedstates/texas/houston/montrose", "neighbourhood"),
    ("africa/uganda/murchison_falls_national_park", "feature"),
    ("europe/france/alpes/chartreuse", "region"),
    ("europe/germany/lowersaxony/frisianislands", "region"),
    ("europe/netherlands/waddenislands/ameland", "region"),
    # --- Chunk 17 ---
    ("asia/china/jiangxi", "region"),
    ("northamerica/unitedstates/utah/capitolreef", "feature"),
    ("northamerica/unitedstates/nevada/redrockcanyon", "feature"),
    ("europe/france/midi/cevennes/mont_aigoual", "feature"),
    ("europe/faroeislands/kalsoy", "region"),
    ("europe/spain/galicia/las_medulas", "feature"),
    ("europe/norway/golsfjellet", "feature"),
    ("africa/algeria/mzab", "region"),
    ("asia/singapore/islands/sisterislands", "feature"),
    # --- Chunk 18 ---
    ("northamerica/unitedstates/alaska/harvard_glacier", "feature"),
    ("northamerica/unitedstates/texas/big_bend_national_park", "feature"),
    ("europe/unitedkingdom/wales/wye_valley", "region"),
    ("europe/france/east/burgundy/morvan", "region"),
    ("africa/niger/teneredesert", "feature"),
    ("asia/philippines/sombrero_island", "feature"),
    ("europe/croatia/bacina_lakes", "feature"),
    ("australiaandpacific/guam/talofofofalls", "feature"),
    ("europe/unitedkingdom/england/london/foresthill", "neighbourhood"),
    # --- Chunk 19 ---
    ("asia/kazakhstan/khan_tengri", "feature"),
    ("europe/italy/sicily/piazza_armerina/morgantina", "feature"),
    ("africa/uganda/rakai_district/murchison_falls", "feature"),
    ("europe/italy/liguria/torseropark", "feature"),
    ("asia/singapore/islands/kusuisland", "feature"),
    ("europe/unitedkingdom/england/manchester_liverpool_and_north_west/gawthorpe_hall", "feature"),
]


def patch_loc_type(md: Path, target: str) -> str | None:
    text = md.read_text(encoding="utf-8")
    fm = FRONTMATTER_RE.match(text)
    if not fm:
        return "no frontmatter"
    body = fm.group(1)
    m = LOC_TYPE_RE.search(body)
    if not m:
        return "no loc_type set"
    current = m.group(1)
    if current == target:
        return "already"
    new_body = LOC_TYPE_RE.sub(f"loc_type: {target}", body)
    new_text = f"---\n{new_body}---\n" + text[fm.end():]
    md.write_text(new_text, encoding="utf-8")
    return current


def main():
    counts = {"updated": 0, "already": 0, "missing": 0, "no_loc_type": 0}
    for path, target in CHANGES:
        md = CONTENT_DIR / f"{path}.md"
        if not md.exists():
            print(f"MISSING {path}", file=sys.stderr)
            counts["missing"] += 1
            continue
        result = patch_loc_type(md, target)
        if result == "already":
            counts["already"] += 1
        elif result in ("no frontmatter", "no loc_type set"):
            print(f"SKIP    {path}  ({result})", file=sys.stderr)
            counts["no_loc_type"] += 1
        else:
            counts["updated"] += 1
            print(f"  {path}: {result} -> {target}")

    print()
    print(f"Updated:    {counts['updated']}")
    print(f"Already:    {counts['already']}")
    print(f"Missing:    {counts['missing']}")
    print(f"No loc_type field: {counts['no_loc_type']}")


if __name__ == "__main__":
    sys.exit(main() or 0)
