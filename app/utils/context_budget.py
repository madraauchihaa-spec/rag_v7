# app/utils/context_budget.py

def limit_context(items, max_items):
    """
    Budget manager to limit the number of items (Act sections, Standard clauses, or SAR clusters)
    passed to the LLM context to prevent token overflow.
    """
    if not items:
        return []
    return items[:max_items]
