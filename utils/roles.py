### Core modules ###


### Type hints ###
from typing import Any


### Internal modules ###
from ..cores.globals import (
    USER_ROLE,
    LLM_ROLE
)



def validate_role_name(
    chat_history_data:  list[dict[str, Any]],
    verbose:            bool = False
) -> bool:
    """
    Validate User and SLM role name in chat history data against agreed constant
    values.

    Args:
        chat_history_data:
            List of chat history dictionaries containing 'user_role' and
            'llm_role' keys.
        verbose: Enable debug output of validation failures/successes.
            When True, prints formatted validation debug message.

    Returns:
        True if all role names are valid, False otherwise.
    """
    if verbose:
        for chat_history in chat_history_data:
            user_chat_history_role: str = chat_history["user_role"]
            llm_chat_history_role:  str = chat_history["llm_role"]

            if user_chat_history_role != USER_ROLE:
                # Invalid user role in chat history
                print(
                    "{head_sep:s}\n{body_msg:s}\n{foot_sep:s}".format(
                        head_sep=f"{'=' * 80}",
                        body_msg="[DEBUG]   ROLES DATA ('NAME' ONLY)   [DEBUG]",
                        foot_sep=f"{'=' * 80}"
                    )
                )
                print(
                    "{debug_msg:s}\n{foot_sep:s}".format(
                        debug_msg="{trig:s}: {cond:s}".format(
                            trig="Chatbox update forbidden",
                            cond=f"User role value must be 'user' only (lowercase convention). Received: '{user_chat_history_role}'"
                        ),
                        foot_sep=f"{'=' * 80}"
                    )
                )
                return False

            if llm_chat_history_role != LLM_ROLE:
                # Invalid LLM role in chat history
                print(
                    "{head_sep:s}\n{body_msg:s}\n{foot_sep:s}".format(
                        head_sep=f"{'=' * 80}",
                        body_msg="[DEBUG]   ROLES DATA ('NAME' ONLY)   [DEBUG]",
                        foot_sep=f"{'=' * 80}"
                    )
                )
                print(
                    "{debug_msg:s}\n{foot_sep:s}".format(
                        debug_msg="{trig:s}: {cond:s}".format(
                            trig="Chatbox update forbidden",
                            cond=f"LLM role value must be 'assistant' only (lowercase convention). Received: '{llm_chat_history_role}'"
                        ),
                        foot_sep=f"{'=' * 80}"
                    )
                )
                return False

        # Valid roles in chat history
        return True

    else:
        for chat_history in chat_history_data:
            user_chat_history_role: str = chat_history["user_role"]
            llm_chat_history_role:  str = chat_history["llm_role"]

            if user_chat_history_role != USER_ROLE:
                # Invalid user role in chat history
                return False

            if llm_chat_history_role != LLM_ROLE:
                # Invalid LLM role in chat history
                return False

        # Valid roles in chat history
        return True
