"""
Utility functions for Crypto Monitor.
"""

import os
from contextlib import contextmanager


@contextmanager
def suppress_output():
    """Context manager to suppress stdout and stderr."""
    try:
        # Open a pair of null files
        null_fds = [os.open(os.devnull, os.O_RDWR) for x in range(2)]
        # Save the actual stdout (1) and stderr (2) file descriptors.
        save_fds = [os.dup(1), os.dup(2)]

        # Assign the null pointers to stdout and stderr.
        os.dup2(null_fds[0], 1)
        os.dup2(null_fds[1], 2)

        yield
    finally:
        # Re-assign the real stdout/stderr back to (1) and (2)
        os.dup2(save_fds[0], 1)
        os.dup2(save_fds[1], 2)

        # Close the null files
        for fd in null_fds + save_fds:
            os.close(fd)


def format_price(price: float | str, precision: int | None = None) -> str:
    """
    Format price string with smart precision based on magnitude.

    Args:
        price: The price to format (float or string).
        precision: Optional explicit precision to use.

    Returns:
        Formatted price string.
    """
    try:
        if isinstance(price, str):
            # Clean up string first
            price = float(price.replace(",", ""))

        val = float(price)
    except (ValueError, TypeError):
        return "0.00"

    # If explicit precision is provided, use it
    if precision is not None and precision >= 0:
        return f"{val:.{precision}f}"

    # Smart precision based on magnitude
    if val == 0:
        return "0.00"

    abs_val = abs(val)

    if abs_val < 0.0001:
        return f"{val:.8f}"
    elif abs_val < 0.01:
        return f"{val:.6f}"
    elif abs_val < 1:
        return f"{val:.4f}"
    elif abs_val < 10:
        return f"{val:.4f}"
    elif abs_val < 1000:
        return f"{val:.2f}"
    else:
        return f"{val:.2f}"
