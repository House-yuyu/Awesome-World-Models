#!/usr/bin/env python3
"""Generate the README catalog, navigation and badges; use --check to verify.

Only the marked paper/navigation blocks and metadata badges are generated.
Unknown categories and duplicate papers fail validation instead of being omitted.
"""
import argparse
import re
import sys
from datetime import date
from html import escape
from pathlib import Path
from urllib.parse import urlsplit

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required. Install with: pip install -r requirements.txt")

ROOT = Path(__file__).resolve().parent.parent
START_MARKER = "<!-- PAPERS_START -->"
END_MARKER = "<!-- PAPERS_END -->"
NAV_START_MARKER = "<!-- NAVIGATION_START -->"
NAV_END_MARKER = "<!-- NAVIGATION_END -->"
CODE_STATUSES = {"released", "partial", "unreleased", "unverified", "repository-only", "data-only"}
PUBLICATION_STATUSES = {"published", "accepted", "preprint"}
SECTIONS = [
    ("survey", "Surveys & Perspectives", 1,
     "Cross-domain world-model reviews.",
     ["Work","Paper","Focus","Venue","Resources"]),
    ("foundations", "Foundations & General World Models", 1,
     "Latent dynamics and general predictive world representation learning.",
     ["Model","Paper","Key Idea","Venue","Resources"]),
    ("interactive", "Interactive Worlds & Games", 1,
     "Controllable generated interactive environments and playable simulations.",
     ["Model","Paper","Key Idea","Venue","Resources"]),
    ("robotics", "Robotics & Embodied World Models", 1,
     "Robot-action-conditioned video, imagined state and model-based policies.",
     ["Model","Paper","Key Idea","Venue","Resources"]),
    ("medical", "Medical & Biological World Models", 1,
     "Patient, cell and molecular dynamics, with related biomedical predictive representation models.",
     ["Model","Paper","Key Idea","Venue","Resources"]),
    ("social", "Social & Multi-Agent World Models", 1,
     "Social-state transitions and related agent simulation systems.",
     ["Model","Paper","Key Idea","Venue","Resources"]),
    ("physics", "Physics, Weather & Scientific World Models", 1,
     "Physical and Earth-system dynamics, with related scientific predictive representation models.",
     ["Model","Paper","Key Idea","Venue","Resources"]),
    ("eo-forecast", "EO: Future Forecasting & Scenario Simulation", 2,
     "Future multispectral scenes, vegetation states and cloud-dependent observability, conditioned on weather or language.",
     ["Model","Paper","Key Idea","Venue","Resources"]),
    ("eo-spatial", "EO: Spatial Extrapolation", 2,
     "Directional continuation into unobserved neighboring image tiles; spatial rather than temporal transitions.",
     ["Model","Paper","Key Idea","Venue","Resources"]),
    ("eo-representation", "EO: Predictive Representations (Related)", 2,
     "Related JEPA and multimodal generative representations for downstream perception, without explicit future-state simulation.",
     ["Model","Paper","Key Idea","Venue","Resources"]),
    ("video-spatial", "Video & Spatial World Models", 1,
     "Predictive and controllable representations of visual worlds.",
     ["Model","Paper","Key Idea","Venue","Resources"]),
    ("bench-general", "General World-Model Benchmarks", 1,
     "Evaluation across action fidelity, physical consistency and geometry.",
     ["Benchmark","Paper","Evaluation Focus","Venue","Resources"]),
    ("generative", "Driving: Generative & Explicit-State Models", 2,
     "RGB, LiDAR, occupancy and future-geometry driving worlds.",
     ["Model","Paper","Key Idea","Venue","Resources"]),
    ("latent", "Driving: Latent & Planning-Oriented Models", 2,
     "Future latent states and world-model-based driving plans.",
     ["Model","Paper","Key Idea","Venue","Resources"]),
    ("world-action", "Driving: World-Action & Action-Aligned Models", 2,
     "Driving models that couple predictive states to actions.",
     ["Model","Paper","Key Idea","Venue","Resources"]),
    ("jepa", "Driving: JEPA & Predictive Representations", 2,
     "Driving predictive representation and joint-embedding methods.",
     ["Model","Paper","Key Idea","Venue","Resources"]),
    ("vla-world", "Driving: World-Model-Enhanced VLA", 2,
     "Driving VLA using future world states or features.",
     ["Model","Paper","Key Idea","Venue","Resources"]),
    ("vla-general", "Driving: Selected General VLA (Context)", 2,
     "Related driving VLA references, not necessarily world models.",
     ["Model","Paper","Key Idea","Venue","Resources"]),
    ("benchmark", "Driving: Benchmarks & Simulation", 2,
     "Driving simulation and evaluation protocols.",
     ["Benchmark","Paper","Evaluation Focus","Venue","Resources"]),
]
CATEGORIES = {section[0] for section in SECTIONS}
PARENTS = {
    "eo-forecast": ("Remote Sensing & Earth Observation", "Forecasting, directional spatial extrapolation and related predictive representations for Earth observation. Resource status is based on verification on 2026-11-03: Not verified means no accessible official implementation was confirmed; the RS-WorldModel repository linked in its paper returned 404."),
    "generative": ("Autonomous Driving World Models", "Autonomous driving is one application of world models, including generation, latent prediction, world-action, JEPA, VLA and benchmarks."),
}


def valid_url(value):
    parsed = urlsplit(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def load_catalog(path):
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("papers"), list) or not data["papers"]:
        raise ValueError("Catalog must contain a non-empty papers list")
    if data.get("schema_version") != 2:
        raise ValueError("Expected schema_version: 2")
    date.fromisoformat(str(data["updated_date"]))
    seen_models, seen_titles, seen_links, seen_ids = set(), set(), set(), set()
    for paper in data["papers"]:
        for key in ("model", "title", "paper_url", "year", "venue", "category", "focus"):
            if not paper.get(key):
                raise ValueError(f"Missing {key}: {paper.get('model', '<unnamed>')}")
        if paper["category"] not in CATEGORIES:
            raise ValueError(f"Unknown category {paper['category']}: {paper['model']}")
        if type(paper["year"]) is not int or not 1900 <= paper["year"] <= 2100:
            raise ValueError(f"Invalid year: {paper['model']}")
        if paper.get("publication_status", "published") not in PUBLICATION_STATUSES:
            raise ValueError(f"Invalid publication_status: {paper['model']}")
        if paper.get("code_status", "released") not in CODE_STATUSES:
            raise ValueError(f"Invalid code_status: {paper['model']}")
        for key in ("published_date", "verified_date", "added_date"):
            if paper.get(key):
                date.fromisoformat(str(paper[key]))
        for key in ("paper_url", "code_url", "project_url", "publication_url"):
            if paper.get(key) and not valid_url(paper[key]):
                raise ValueError(f"Invalid {key}: {paper['model']}")
        for resource in paper.get("resources", []):
            if not resource.get("label") or not valid_url(resource.get("url", "")):
                raise ValueError(f"Invalid resource: {paper['model']}")
        for source in paper.get("sources", []):
            if not valid_url(source):
                raise ValueError(f"Invalid source: {paper['model']}")
        model = paper["model"].casefold()
        title = re.sub(r"\W+", "", paper["title"].casefold())
        link = paper["paper_url"].rstrip("/")
        arxiv_id = paper.get("arxiv_id", "")
        if arxiv_id and not re.fullmatch(r"\d{4}\.\d{4,5}", arxiv_id):
            raise ValueError(f"Invalid arxiv_id: {paper['model']}")
        if (model in seen_models or title in seen_titles or link in seen_links
                or (arxiv_id and arxiv_id in seen_ids)):
            raise ValueError(f"Duplicate paper: {paper['model']}")
        if "arxiv.org/abs/" in link and arxiv_id and not re.search(rf"/{re.escape(arxiv_id)}(?:v\d+)?$", link):
            raise ValueError(f"arxiv_id does not match paper_url: {paper['model']}")
        seen_models.add(model)
        seen_titles.add(title)
        seen_links.add(link)
        if arxiv_id:
            seen_ids.add(arxiv_id)
    return data


def cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


def venue_cell(paper):
    text = f"{paper['venue']} {paper['year']}"
    if paper.get("publication_status") == "accepted":
        text += " (accepted)"
    if paper.get("publication_url"):
        return f"[{cell(text)}]({paper['publication_url']})"
    return cell(text)


def resource_cell(paper):
    links, seen_urls = [], set()

    def add(label, url, note=""):
        if url and url not in seen_urls:
            links.append(f"[{cell(label)}]({url}){note}")
            seen_urls.add(url)

    status = paper.get("code_status", "released")
    label = ("Data" if status == "data-only" else
             "Repository" if status in {"unreleased", "unverified", "repository-only"} else "Code")
    note = (" (code pending)" if status == "unreleased" else
            " (availability unverified)" if status == "unverified" else
            " (partial)" if status == "partial" else "")
    add(label, paper.get("code_url"), note)
    add("Project", paper.get("project_url"))
    for resource in paper.get("resources", []):
        add(resource["label"], resource["url"])
    return " · ".join(links) or ("Not verified" if status == "unverified" else "—")


def build_table(papers, headers):
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for paper in papers:
        row = [f"**{cell(paper['model'])}**", f"[{cell(paper['title'])}]({paper['paper_url']})",
               cell(paper["focus"]), venue_cell(paper), resource_cell(paper)]
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def heading_anchor(heading):
    return re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-")


def paper_count(count):
    return f"{count} {'paper' if count == 1 else 'papers'}"


def child_sections(parent_category):
    children, active = [], False
    for section in SECTIONS:
        category, _, level, _, _ = section
        if category == parent_category:
            active = True
        elif active and (level == 1 or category in PARENTS):
            break
        if active:
            children.append(section)
    return children


def collections(papers):
    """Derive top-level collections from the same hierarchy as the paper tables."""
    groups = []
    for category, heading, level, description, _ in SECTIONS:
        members = [paper for paper in papers if paper["category"] == category]
        if category in PARENTS:
            parent, intro = PARENTS[category]
            groups.append({"heading": parent, "description": intro, "count": 0})
        elif level == 1:
            groups.append({"heading": heading, "description": description, "count": 0})
        groups[-1]["count"] += len(members)
    return [group for group in groups if group["count"]]


def generate_navigation(catalog):
    navigation = {
        "Surveys & Perspectives": ("Surveys & Perspectives", "Find a starting point and the bigger picture."),
        "Foundations & General World Models": ("Foundations", "Latent dynamics, imagination and predictive learning."),
        "Interactive Worlds & Games": ("Interactive Worlds & Games", "Playable environments and controllable generation."),
        "Robotics & Embodied World Models": ("Robotics & Embodied AI", "Robot imagination, world-action models and policies."),
        "Medical & Biological World Models": ("Medicine & Biology", "Clinical trajectories, cells and molecular dynamics."),
        "Social & Multi-Agent World Models": ("Social & Multi-Agent", "Agent interactions and social simulation."),
        "Physics, Weather & Scientific World Models": ("Physics & Weather", "Physical processes, weather and scientific discovery."),
        "Remote Sensing & Earth Observation": ("Remote Sensing & Earth Observation", "Satellite futures, vegetation and spatial extrapolation."),
        "Video & Spatial World Models": ("Video & Spatial Worlds", "Visual prediction, geometry and spatial memory."),
        "General World-Model Benchmarks": ("Benchmarks & Evaluation", "Action fidelity, physical consistency and geometry."),
        "Autonomous Driving World Models": ("Autonomous Driving", "Generation, planning, world-action, JEPA and VLA."),
    }
    groups = collections(catalog["papers"])
    cards = []
    for group in groups:
        heading = group["heading"]
        label, description = navigation[heading]
        cards.append(
            f'<a href="#{heading_anchor(heading)}"><strong>{escape(label)}</strong></a>'
            f'<br><sub>{paper_count(group["count"])} · {escape(description)}</sub>'
        )
    cards.append('<a href="#datasets--toolkits"><strong>Datasets &amp; Toolkits</strong></a>'
                 '<br><sub>Training data, evaluation suites and research systems.</sub>')
    lines = [NAV_START_MARKER, "", '<table width="100%">']
    for i in range(0, len(cards), 2):
        lines.append("  <tr>")
        for card in cards[i:i + 2]:
            lines.append(f'    <td width="50%" valign="top">{card}</td>')
        lines.append("  </tr>")
    lines.extend(["</table>", "", NAV_END_MARKER])
    return "\n".join(lines)


def generate_papers_section(papers):
    lines = [START_MARKER, ""]
    emitted = 0
    for category, heading, level, description, headers in SECTIONS:
        group = [p for p in papers if p["category"] == category]
        # Stable sorting retains YAML order when year and first-posted date tie.
        group.sort(key=lambda p: (p["year"], str(p.get("published_date", ""))), reverse=True)
        if category in PARENTS:
            parent, intro = PARENTS[category]
            children = [(h, heading_anchor(h)) for c, h, _, _, _ in child_sections(category)
                        if any(p["category"] == c for p in papers)]
            if children:
                lines.extend([f"## {parent}", "", intro, "",
                              " · ".join(f"[{h.split(': ', 1)[-1]}](#{anchor})"
                                         for h, anchor in children), ""])
        if not group:
            continue
        lines.extend([f"{'#' * (level + 1)} {heading}", "",
                      f"**{paper_count(len(group))}** · {description}", "",
                      build_table(group, headers), "",
                      '<sub><a href="#explore">↑ Back to collections</a></sub>', ""])
        emitted += len(group)
    if emitted != len(papers):
        raise ValueError("Not all catalog papers were rendered")
    lines.extend([END_MARKER, ""])
    return "\n".join(lines)


def replace_block(content, start, end, replacement):
    starts = list(re.finditer(rf"(?m)^{re.escape(start)}$", content))
    ends = list(re.finditer(rf"(?m)^{re.escape(end)}$", content))
    if len(starts) != 1 or len(ends) != 1 or starts[0].end() >= ends[0].start():
        raise ValueError(f"README must contain exactly one ordered pair of {start}/{end}")
    prefix = content[:starts[0].start()]
    suffix = content[ends[0].end():]
    return prefix + replacement.rstrip("\n") + "\n\n" + suffix.lstrip("\n")


def render_readme(content, catalog):
    result = replace_block(content, START_MARKER, END_MARKER,
                           generate_papers_section(catalog["papers"]))
    result = replace_block(result, NAV_START_MARKER, NAV_END_MARKER,
                           generate_navigation(catalog))
    result, count = re.subn(r"https://img\.shields\.io/badge/papers-\d+-blue",
                           f"https://img.shields.io/badge/papers-{len(catalog['papers'])}-blue", result)
    if count != 1:
        raise ValueError("README must contain exactly one papers badge")
    result, count = re.subn(r"https://img\.shields\.io/badge/collections-\d+-teal",
                           f"https://img.shields.io/badge/collections-{len(collections(catalog['papers']))}-teal", result)
    if count != 1:
        raise ValueError("README must contain exactly one collections badge")
    updated = str(catalog["updated_date"]).replace("-", "--")
    result, count = re.subn(r"https://img\.shields\.io/badge/last%20updated-[\d-]+-brightgreen",
                           f"https://img.shields.io/badge/last%20updated-{updated}-brightgreen", result)
    if count != 1:
        raise ValueError("README must contain exactly one last-updated badge")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Validate metadata and fail if README needs regeneration")
    args = parser.parse_args(argv)
    try:
        catalog = load_catalog(ROOT / "data/papers.yaml")
        path = ROOT / "README.md"
        current = path.read_text(encoding="utf-8")
        expected = render_readme(current, catalog)
        if args.check:
            if current != expected:
                sys.exit("README.md is out of date. Run python scripts/generate_readme.py")
            print(f"Validated {len(catalog['papers'])} unique papers; README.md is up to date.")
        else:
            path.write_text(expected, encoding="utf-8")
            print(f"Generated {len(catalog['papers'])} papers across {len(CATEGORIES)} categories.")
    except (KeyError, TypeError, ValueError, OSError, yaml.YAMLError) as error:
        sys.exit(f"Error: {error}")


if __name__ == "__main__":
    main()

