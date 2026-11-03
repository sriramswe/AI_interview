TEMPLATE_FAMILIES = (
    ("classic", "Classic", "traditional"),
    ("modern", "Modern", "modern"),
    ("executive", "Executive", "executive"),
    ("creative", "Creative", "creative"),
    ("minimal", "Minimal", "minimal"),
)

TEMPLATE_PALETTES = (
    ("navy", "Navy", "#1e3a5f"),
    ("emerald", "Emerald", "#087f5b"),
    ("burgundy", "Burgundy", "#8b2635"),
    ("slate", "Slate", "#475569"),
    ("teal", "Teal", "#0f766e"),
    ("indigo", "Indigo", "#4338ca"),
)

RESUME_TEMPLATES = tuple(
    {
        "id": f"{family_id}-{palette_id}",
        "name": f"{family_name} {palette_name}",
        "family": family_id,
        "layout": layout,
        "accent": accent,
    }
    for family_id, family_name, layout in TEMPLATE_FAMILIES
    for palette_id, palette_name, accent in TEMPLATE_PALETTES
)

RESUME_TEMPLATE_BY_ID = {
    template["id"]: template for template in RESUME_TEMPLATES
}

FREE_RESUME_BUILD_LIMIT = 3
MAX_RESUME_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024
