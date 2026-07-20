from .canonical_rules import CANONICAL_RULES
from .axe_aliases import AXE_ALIASES
from .ibm_aliases import IBM_ALIASES
from .htmlcs_aliases import HTMLCS_ALIASES
from .alfa_aliases import ALFA_ALIASES
from .uuv_aliases import UUV_ALIASES
from .speca11y_aliases import SPECA11Y_ALIASES
from .oobee_aliases import OOBEE_ALIASES
from .nu_html_aliases import NU_HTML_ALIASES
from .canonical_problem_types import PROBLEM_TYPE_MAP
from .canonical_rules import CANONICAL_RULES, is_canonical_rule

RULE_ALIAS_MAP = {}
RULE_ALIAS_MAP.update(AXE_ALIASES)
RULE_ALIAS_MAP.update(IBM_ALIASES)
RULE_ALIAS_MAP.update(HTMLCS_ALIASES)
RULE_ALIAS_MAP.update(ALFA_ALIASES)
RULE_ALIAS_MAP.update(SPECA11Y_ALIASES)
RULE_ALIAS_MAP.update(UUV_ALIASES)
RULE_ALIAS_MAP.update(OOBEE_ALIASES)
RULE_ALIAS_MAP.update(NU_HTML_ALIASES)

__all__ = [
    "RULE_ALIAS_MAP",
    "PROBLEM_TYPE_MAP",
    "CANONICAL_RULES",
    "is_canonical_rule",
]