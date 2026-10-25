
GLOSSARY = {
    "agent": (
        "An AI agent is a system that pursues a goal, "
        "chooses actions, observes results, and "
        "may adapt its next steps."
    ),
    "tool calling": (
        "A model proposes a structured function call. "
        "Application code validates and executes it."
    ),
    "rag": (
        "Retrieval-Augmented Generation retrieves "
        "external information and supplies relevant "
        "evidence to a language model."
    ),
    "mcp": (
        "Model Context Protocol standardizes how "
        "AI applications access tools and data."
    ),
    "memory": (
        "Agent memory is stored information that "
        "can be retrieved for future tasks."
    ),
}


def lookup_concept(concept: str) -> dict:
    key = concept.strip().lower()

    return {
        "concept": key,
        "definition": GLOSSARY.get(key),
        "found": key in GLOSSARY,
    }
