"""ShopSmart test framework: configuration, device discovery, and page objects.

Importing this package must never start a browser, contact the network, or
read a credential. Collection integrity in CI depends on that being true.
"""

__all__ = ["config", "ios", "pages"]
