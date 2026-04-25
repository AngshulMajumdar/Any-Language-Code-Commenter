"""Professional repository version of the multi-language dual-LLM code commenter."""

from .commenter import comment_repository, zip_output, clone_repo
from .languages import LANGUAGE_SPECS, detect_language, register_all_languages

__all__ = ["comment_repository", "zip_output", "clone_repo", "LANGUAGE_SPECS", "detect_language", "register_all_languages"]
