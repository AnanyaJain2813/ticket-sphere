"""
accounts/permissions.py — Custom DRF permission classes based on user.role.

These are thin wrappers over BasePermission that read the `role` field from
our custom User model (accounts.models.User). Using dedicated permission classes
instead of inline `if request.user.role != 'organiser'` checks gives:

  - A single place to update role logic if roles ever change
  - Composable permission stacks via [IsOrganiser | IsAdmin]
  - Descriptive 403 messages that tell the caller exactly what role is needed
"""

from rest_framework.permissions import BasePermission


class IsCustomer(BasePermission):
    """
    Grants access to users with role='customer'.
    Use on booking/hold/waitlist endpoints where only customers take actions.

    Note: In practice most of these endpoints use IsAuthenticated (any logged-in
    user can browse and book). IsCustomer is available for strict gating, e.g.
    if you need to prevent organisers from booking tickets in their own shows.
    """

    message = "Access restricted to customers."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "role", None) == "customer"
        )


class IsOrganiser(BasePermission):
    """
    Grants access to users with role='organiser'.
    Use on event-creation and revenue endpoints.
    """

    message = "Access restricted to organisers."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "role", None) == "organiser"
        )


class IsAdmin(BasePermission):
    """
    Grants access to users with role='admin'.
    Use on venue-management endpoints and other platform-level operations.

    This is distinct from Django's is_staff / is_superuser: role='admin' is an
    application-level concept, not a Django admin site concept.
    """

    message = "Access restricted to administrators."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "role", None) == "admin"
        )


class IsOrganiserOrAdmin(BasePermission):
    """
    Grants access to organisers OR admins.
    Use where admins need visibility into all organiser data (e.g. platform reporting).
    """

    message = "Access restricted to organisers and administrators."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "role", None) in ("organiser", "admin")
        )
