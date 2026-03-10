# app/retrieval/context_expander.py
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

            # Hierarchical sibling expansion
            clause_num = r.get("clause_number", "")
            if clause_num and "." in clause_num:
                # e.g. 7.1.1 -> 7.1.%
                parent_prefix = ".".join(clause_num.split(".")[:-1]) + ".%"
                cursor.execute("""
                    SELECT * FROM standard_index
                    WHERE standard_code = %s AND year = %s
                    AND (section_number = %s OR clause_number LIKE %s)
                    ORDER BY clause_number ASC
                    LIMIT 4
                """, (r["standard_code"], r["year"], r["section_number"], parent_prefix))
            else:
                cursor.execute("""
                    SELECT *
                    FROM standard_index
                    WHERE standard_code = %s
                    AND year = %s
                    AND section_number = %s
                    ORDER BY clause_number ASC
                    LIMIT 4
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

