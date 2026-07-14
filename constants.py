from enum import Enum


class CommunicationType(str, Enum):
    STRATEGIC = "strategic"
    UNDERSTANDING_ORIENTED = "understanding_oriented"


class SocialRole(str, Enum):
    STRONGER = "stronger"
    EQUAL = "equal"
    WEAKER = "weaker"


class ConversationIntention(str, Enum):
    CONTENT_GOAL = "content_goal"
    RELATIONSHIP_GOAL = "relationship_goal"


class Language(str, Enum):
    GERMAN = "de"
    ENGLISH = "en"


class ExperimentalCondition(str, Enum):
    C1_PROMPT_ONLY = "C1_prompt_only"
    C2_STRUCTURED_PROMPT = "C2_structured_prompt"
    C3_ONTOLOGY_GROUNDED = "C3_ontology_grounded"
    C4_ONTOLOGY_REASONING = "C4_ontology_reasoning"
