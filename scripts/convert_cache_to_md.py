#!/usr/bin/env python3
"""
Convert cached/dblp.yaml into a structured Markdown file.

NOTE ON DOMAIN SWITCHING ──────────────────────────────────────────────
The mappings below (VENUE_MAP, CATEGORY_MAP, CATEGORY_ORDER, VENUE_ORDER)
are tailored to the current research domain (Federated Learning) and the
venue list in config.yaml. If you change the ``keyword`` in config.yaml
to track a different domain (e.g. diffusion, LLM), you MUST review and
update these mappings to match the new venue set and desired categories.

Quick checklist when switching domains:
1. Update ``keyword`` and ``queries`` in config.yaml.
2. Update VENUE_MAP to map DBLP raw venue names → your display names.
3. Update CATEGORY_MAP to assign each display name → a category.
4. Update CATEGORY_ORDER and VENUE_ORDER to control output ordering.
5. Delete or rename cached/dblp.yaml to force a fresh crawl.
───────────────────────────────────────────────────────────────────────
"""

import yaml
from pathlib import Path
from collections import defaultdict


def main():
    repo_root = Path(__file__).resolve().parent.parent
    cache_path = repo_root / "cached" / "dblp.yaml"
    output_path = repo_root / "FL-Papers.md"

    # Load cache
    with open(cache_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # Venue raw name -> display name
    VENUE_MAP = {
        # Journals
        "Artif. Intell.": "AI",
        "Mach. Learn.": "Machine Learning",
        "J. Mach. Learn. Res.": "JMLR",
        "IEEE Trans. Pattern Anal. Mach. Intell.": "TPAMI",
        "Int. J. Comput. Vis.": "IJCV",
        "Proc. VLDB Endow.": "VLDB",
        "IEEE Trans. Parallel Distrib. Syst.": "TPDS",
        "ACM Trans. Comput. Syst.": "TOCS",
        "ACM Trans. Storage": "TOS",
        "IEEE Trans. Comput. Aided Des. Integr. Circuits Syst.": "TCAD",
        "IEEE Trans. Comput.": "TC",
        "IEEE Trans. Computers": "TC",
        "IEEE Trans. Parallel Distributed Syst.": "TPDS",
        # Conferences with special names
        "IEEE Symposium on Security and Privacy": "S&P",
        "IEEE Symposium on Security and Privacy Workshops": "S&P",
        "USENIX Security Symposium": "USENIX Security",
        "SIGMOD Conference": "SIGMOD",
        "Proc. ACM Manag. Data": "SIGMOD",
        "BiDEDE@SIGMOD": "SIGMOD",
        "DEEM@SIGMOD": "SIGMOD",
        "DanaC@SIGMOD": "SIGMOD",
        "aiDM@SIGMOD": "SIGMOD",
        "NAACL-HLT": "NAACL",
        "MobiCom": "MOBICOM",
        "ACM Multimedia": "MM",
        "CSET @ USENIX Security Symposium": "USENIX Security",
        "CrossCloud@EuroSys": "EuroSys",
        "EdgeSys@EuroSys": "EuroSys",
        "EuroMLSys@EuroSys": "EuroSys",
        "ICSE Companion": "ICSE",
        "S-Cube@ICSE": "ICSE",
        "SEAMS@ICSE": "ICSE",
        "SEiGS@ICSE": "ICSE",
        "SVM@ICSE": "ICSE",
        "SP": "S&P",
        "SP Workshops": "S&P",
    }

    # Display name -> category
    CATEGORY_MAP = {
        "IJCAI": "Artificial Intelligence",
        "AAAI": "Artificial Intelligence",
        "AISTATS": "Artificial Intelligence",
        "ALT": "Artificial Intelligence",
        "AI": "Artificial Intelligence",
        "NeurIPS": "Machine Learning",
        "ICML": "Machine Learning",
        "ICLR": "Machine Learning",
        "COLT": "Machine Learning",
        "UAI": "Machine Learning",
        "Machine Learning": "Machine Learning",
        "JMLR": "Machine Learning",
        "TPAMI": "Machine Learning",
        "KDD": "Data Mining",
        "WSDM": "Data Mining",
        "S&P": "Secure",
        "CCS": "Secure",
        "USENIX Security": "Secure",
        "NDSS": "Secure",
        "ICCV": "Computer Vision",
        "CVPR": "Computer Vision",
        "ECCV": "Computer Vision",
        "MM": "Computer Vision",
        "IJCV": "Computer Vision",
        "ACL": "Natural Language Processing",
        "EMNLP": "Natural Language Processing",
        "NAACL": "Natural Language Processing",
        "COLING": "Natural Language Processing",
        "SIGIR": "Information Retrieval",
        "SIGMOD": "Database",
        "ICDE": "Database",
        "VLDB": "Database",
        "SIGCOMM": "Network",
        "INFOCOM": "Network",
        "MOBICOM": "Network",
        "NSDI": "Network",
        "WWW": "Network",
        "OSDI": "System",
        "SOSP": "System",
        "ISCA": "System",
        "MLSys": "System",
        "EuroSys": "System",
        "TPDS": "System",
        "DAC": "System",
        "TOCS": "System",
        "TOS": "System",
        "TCAD": "System",
        "TC": "System",
        "ICSE": "Others",
        "FOCS": "Others",
        "STOC": "Others",
    }

    CATEGORY_ORDER = [
        "Artificial Intelligence",
        "Machine Learning",
        "Data Mining",
        "Secure",
        "Computer Vision",
        "Natural Language Processing",
        "Information Retrieval",
        "Database",
        "Network",
        "System",
        "Others",
    ]

    # Venue display order within each category (as specified by user)
    VENUE_ORDER = {
        "Artificial Intelligence": ["IJCAI", "AAAI", "AISTATS", "ALT", "AI"],
        "Machine Learning": ["NeurIPS", "ICML", "ICLR", "COLT", "UAI", "Machine Learning", "JMLR", "TPAMI"],
        "Data Mining": ["KDD", "WSDM"],
        "Secure": ["S&P", "CCS", "USENIX Security", "NDSS"],
        "Computer Vision": ["ICCV", "CVPR", "ECCV", "MM", "IJCV"],
        "Natural Language Processing": ["ACL", "EMNLP", "NAACL", "COLING"],
        "Information Retrieval": ["SIGIR"],
        "Database": ["SIGMOD", "ICDE", "VLDB"],
        "Network": ["SIGCOMM", "INFOCOM", "MOBICOM", "NSDI", "WWW"],
        "System": ["OSDI", "SOSP", "ISCA", "MLSys", "EuroSys", "TPDS", "DAC", "TOCS", "TOS", "TCAD", "TC"],
        "Others": ["ICSE", "FOCS", "STOC"],
    }

    # Aggregate: category -> year -> venue -> [papers]
    aggregated = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    unknown_venues = set()

    for topic, papers in data.items():
        if not isinstance(papers, list):
            continue
        for paper in papers:
            raw_venue = paper.get("venue", "").strip()
            if not raw_venue:
                continue

            venue = VENUE_MAP.get(raw_venue, raw_venue)
            category = CATEGORY_MAP.get(venue)

            if category is None:
                unknown_venues.add(raw_venue)
                continue

            year_str = paper.get("year", "")
            try:
                year = int(year_str)
            except (ValueError, TypeError):
                continue

            aggregated[category][year][venue].append(paper)

    if unknown_venues:
        print("[WARN] Unknown venues (skipped):")
        for v in sorted(unknown_venues):
            print(f"  - {v}")

    def is_low_priority(title: str) -> bool:
        """Return True if title contains brackets or keywords like Abstract/Poster."""
        t = title.strip()
        if not t:
            return False
        has_brackets = any(c in t for c in ['(', ')', '（', '）'])
        has_keywords = any(kw in t.lower() for kw in ['abstract', 'poster'])
        return has_brackets or has_keywords

    # Build Markdown
    lines = []
    lines.append("# FL Papers\n")

    for category in CATEGORY_ORDER:
        if category not in aggregated:
            continue
        lines.append(f"## {category}\n")
        years = sorted(aggregated[category].keys(), reverse=True)
        for year in years:
            lines.append(f"### {year}\n")
            venue_order_map = {v: i for i, v in enumerate(VENUE_ORDER.get(category, []))}
            venues = sorted(
                aggregated[category][year].keys(),
                key=lambda v: (venue_order_map.get(v, 999), v)
            )
            for venue in venues:
                lines.append(f"#### {venue}\n")
                papers = aggregated[category][year][venue]
                papers_sorted = sorted(
                    papers,
                    key=lambda p: (1 if is_low_priority(p.get("title", "")) else 0, p.get("title", "").lower())
                )
                for paper in papers_sorted:
                    title = paper.get("title", "").strip()
                    ee = paper.get("ee", "").strip()
                    # Avoid double periods if title already ends with a dot
                    suffix = "" if title.endswith(".") else "."
                    if ee:
                        lines.append(f"- {title}{suffix} [[PUB]({ee})]")
                    else:
                        lines.append(f"- {title}{suffix}")
                lines.append("")

    # Write output
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Done! Written to {output_path}")


if __name__ == "__main__":
    main()
