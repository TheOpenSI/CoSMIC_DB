### Core modules ###


### Type hints ###
from typing import Any


### Internal modules ###



def get_io_token(
    payload: dict[str, Any],
    verbose: bool = False
) -> tuple[int, int]:
    input_token: int = payload.get(
        "input_token",
        0
    )
    output_token: int = payload.get(
        "output_token",
        0
    )

    if verbose:
        print(
            "{head_sep:s}\n{body_msg:s}\n{foot_sep:s}".format(
                head_sep=f"{'=' * 80}",
                body_msg="[DEBUG]   I/O TOKENS  [DEBUG]",
                foot_sep=f"{'=' * 80}"
            )
        )
        print(
            "{debug_msg:s}\n{foot_sep:s}".format(
                debug_msg="{0:s}\n{1:s}".format(
                    f"Received input token: {input_token}",
                    f"Received output token: {output_token}"
                ),
                foot_sep=f"{'=' * 80}"
            )
        )

        return (
            input_token,
            output_token
        )

    else:
        return (
           input_token,
           output_token
        )
