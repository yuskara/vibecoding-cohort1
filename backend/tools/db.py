# ============================================================
# HEALING PLATFORM — Database Connection for Agent Tools
# File: db.py
# ============================================================
# Install dependencies first:
#   pip install supabase
# ============================================================
import os
from dotenv import load_dotenv
from supabase import create_client, Client
load_dotenv()


# Create the client — reuse this across your agent
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)




# ============================================================
# CONDITIONS
# ============================================================

def get_all_conditions():
    """Get all conditions with their linked conflict theme and organ system."""
    return supabase.table("conditions").select(
        "*, conflict_themes(*), organ_systems(*)"
    ).execute()

def get_condition_by_id(condition_id: str):
    """Get a single condition with all related data."""
    return supabase.table("conditions").select(
        "*, conflict_themes(*), organ_systems(*), symptom_patterns(*), healing_markers(*)"
    ).eq("id", condition_id).single().execute()

def search_conditions_by_tag(tag: str):
    """Find conditions by tag."""
    return supabase.table("conditions").select("*").contains("tags", [tag]).execute()

def add_condition(data: dict):
    """Add a new condition entry."""
    return supabase.table("conditions").insert(data).execute()

def update_condition(condition_id: str, data: dict):
    """Update an existing condition."""
    return supabase.table("conditions").update(data).eq("id", condition_id).execute()

def delete_condition(condition_id: str):
    """Delete a condition and all its related symptom/healing data (cascade)."""
    return supabase.table("conditions").delete().eq("id", condition_id).execute()


# ============================================================
# CONFLICT THEMES
# ============================================================

def get_all_conflict_themes():
    """Get all conflict themes."""
    return supabase.table("conflict_themes").select("*").execute()

def add_conflict_theme(data: dict):
    """Add a new conflict theme."""
    return supabase.table("conflict_themes").insert(data).execute()


# ============================================================
# ORGAN SYSTEMS
# ============================================================

def get_all_organ_systems():
    """Get all organ systems."""
    return supabase.table("organ_systems").select("*").execute()

def get_organs_by_germ_layer(germ_layer: str):
    """Filter organs by germ layer: endoderm, mesoderm, ectoderm, new_mesoderm."""
    return supabase.table("organ_systems").select("*").eq("germ_layer", germ_layer).execute()


# ============================================================
# SYMPTOM PATTERNS
# ============================================================

def get_symptoms_for_condition(condition_id: str, phase: str = None):
    """Get symptoms for a condition. Optionally filter by phase."""
    query = supabase.table("symptom_patterns").select("*").eq("condition_id", condition_id)
    if phase:
        query = query.eq("phase", phase)
    return query.execute()

def add_symptom(data: dict):
    """Add a symptom pattern to a condition."""
    return supabase.table("symptom_patterns").insert(data).execute()


# ============================================================
# HEALING MARKERS
# ============================================================

def get_healing_markers(condition_id: str):
    """Get all healing/vagotonic markers for a condition."""
    return supabase.table("healing_markers").select("*").eq("condition_id", condition_id).execute()

def add_healing_marker(data: dict):
    """Add a healing marker to a condition."""
    return supabase.table("healing_markers").insert(data).execute()


# ============================================================
# SEMANTIC SEARCH (requires embeddings to be stored)
# ============================================================

def semantic_search_conditions(embedding: list, limit: int = 5):
    """
    Find conditions by semantic similarity.
    Pass in a 768-dim embedding vector from Ollama nomic-embed-text.
    """
    return supabase.rpc("match_conditions", {
        "query_embedding": embedding,
        "match_threshold": 0.7,
        "match_count": limit
    }).execute()


# ============================================================
# USER PROGRESS
# ============================================================

def add_progress_record(data: dict):
    """Log a client session or progress note."""
    return supabase.table("user_progress").insert(data).execute()

def get_progress_for_condition(condition_id: str):
    """Get all progress records for a condition."""
    return supabase.table("user_progress").select("*").eq(
        "condition_id", condition_id
    ).order("session_date", desc=True).execute()


# ============================================================
# QUICK TEST — run this file directly to verify connection
# ============================================================
if __name__ == "__main__":
    print("Testing connection to Supabase...")
    result = get_all_conflict_themes()
    themes = result.data
    if themes:
        print(f"Connected! Found {len(themes)} conflict themes:")
        for t in themes:
            print(f"  - {t['theme_name']}")
    else:
        print("Connected but no data yet — run the schema SQL first.")