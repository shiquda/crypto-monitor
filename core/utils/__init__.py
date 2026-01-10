"""
Utility functions for Crypto Monitor.
"""

import os
from contextlib import contextmanager


@contextmanager
def suppress_output():
    """Context manager to suppress stdout and stderr."""
    try:
        null_fds = [os.open(os.devnull, os.O_RDWR) for x in range(2)]
        save_fds = [os.dup(1), os.dup(2)]

        os.dup2(null_fds[0], 1)
        os.dup2(null_fds[1], 2)

        yield
    finally:
        os.dup2(save_fds[0], 1)
        os.dup2(save_fds[1], 2)

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
            price = float(price.replace(",", ""))

        val = float(price)
    except (ValueError, TypeError):
        return "0.00"

    if precision is not None and precision >= 0:
        return f"{val:.{precision}f}"

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


def get_display_name(pair: str, display_name: str | None = None, short: bool = False) -> str:
    """
    Get a user-friendly display name for a trading pair.

    Format rules:
    - CEX:
        - short=True: "BTC"
        - short=False: "BTC-USDT"
    - DEX:
        - short=True: "Symbol" (e.g. "V2EX")
        - short=False: "Symbol (Network)" (e.g. "V2EX (Solana)")

    Args:
        pair: The raw pair string (e.g., "BTC-USDT" or "chain:solana:...")
        display_name: Optional explicit display name from TickerData (usually Symbol).
        short: Whether to return the shortest possible name.

    Returns:
        Formatted display name.
    """
    if pair.lower().startswith("chain:"):
        parts = pair.split(":")
        network = parts[1].title() if len(parts) >= 2 else "Unknown"

        symbol = None
        if display_name:
            symbol = display_name
        elif len(parts) >= 4 and parts[3]:
            symbol = parts[3]

        if symbol:
            return symbol if short else f"{symbol} ({network})"
        elif len(parts) >= 3:
            addr = parts[2]
            snippet = f"{addr[:4]}...{addr[-4:]}"
            return snippet if short else f"{snippet} ({network})"
        return "Unknown"

    if "-" in pair:
        return pair.split("-")[0] if short else pair

    return pair
