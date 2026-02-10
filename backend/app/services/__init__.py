from app.services.relationship_state import (
    create_initial_relationship_state,
    register_interaction,
    apply_inactivity_decay,
    get_jealousy_reaction,
    check_for_milestone_event,
    append_milestone_reached,
)
from app.services.relationship_regions import (
    MAX_RELATIONSHIP_LEVEL,
    clamp_level,
    get_region_for_level,
)
from app.services.initiation_engine import should_initiate_conversation, get_initiation_message
from app.services.habits import infer_preferred_hours, infer_typical_gap_hours, build_habit_profile
from app.services.time_utils import hours_since, now_iso
