"""WorkforceOS API layer.

Exposes whitelisted endpoints and acts as the interface between Frappe HTTP
requests and the application service layer.
"""

from workforceos.api.allocation import allocate

__all__ = ["allocate"]
