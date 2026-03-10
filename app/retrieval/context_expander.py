# app/retrieval/context_expander.py
from collections import defaultdict
from psycopg2.extras import RealDictCursor

def expand_standard_context(results, conn):
    """
    Hierarchical expansion:
    1. Retrieve full SECTION
    2. Include all clauses in that section
    """

    if not results:
        return []

    expanded = []
    seen_sections = set()

    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        for r in results:
            section_key = (
                r["standard_code"],
                r["year"],
                r["section_number"]
            )

            if section_key in seen_sections:
                continue

            seen_sections.add(section_key)

            cursor.execute("""
                SELECT *
                FROM standard_index
                WHERE standard_code = %s
                AND year = %s
                AND section_number = %s
                ORDER BY clause_number ASC
            """, (
                r["standard_code"],
                r["year"],
                r["section_number"]
            ))

            rows = cursor.fetchall()

            for row in rows:
                d = dict(row)
                # Keep UUID and embedding conversions for API safety
                if "id" in d: d["id"] = str(d["id"])
                if "tsv" in d: d["tsv"] = str(d["tsv"])
                if "embedding" in d and hasattr(d["embedding"], "tolist"):
                    d["embedding"] = d["embedding"].tolist()
                expanded.append(d)

    return expanded


def aggregate_standard_sections(results):
    """
    Aggregates individual clauses into section-level blocks for the LLM prompt.
    """
    grouped = defaultdict(list)
    for r in results:
        key = (
            r.get("standard_code"),
            r.get("year"),
            r.get("section_number")
        )
        grouped[key].append(r)

    aggregated = []
    for key, clauses in grouped.items():
        first = clauses[0]
        aggregated.append({
            "standard_code": first.get("standard_code"),
            "year": first.get("year"),
            "section_number": first.get("section_number"),
            "section_title": first.get("parent_clause_title"),
            "clauses": [c.get("clause_number") for c in clauses],
            "content": "\n".join(c.get("content", "") for c in clauses)
        })
    return aggregated

