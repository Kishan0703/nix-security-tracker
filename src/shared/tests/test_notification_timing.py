"""
Tests for the notification timing fix (issue #829).

Verifies that:
1. Notifications ARE created for subscribed users when cache_new_suggestions()
   is called for the first time on a suggestion.
2. NO duplicate notifications are created when cache_new_suggestions() is called
   again on the same suggestion (cache update, not creation).
"""

from collections.abc import Callable

import pytest
from allauth.socialaccount.models import SocialAccount
from django.contrib.auth.models import User

from shared.listeners.cache_suggestions import cache_new_suggestions
from shared.models.cached import CachedSuggestions
from shared.models.linkage import CVEDerivationClusterProposal, ProvenanceFlags
from shared.models.nix_evaluation import NixDerivation, NixMaintainer
from webview.models import SuggestionNotification as Notification


@pytest.mark.django_db
class TestCacheCreatesNotifications:
    """Verify that cache_new_suggestions() triggers notifications on first cache creation."""

    def test_notifications_created_on_first_cache(
        self,
        make_suggestion: Callable[..., CVEDerivationClusterProposal],
        make_drv: Callable[..., NixDerivation],
        make_maintainer: Callable[..., NixMaintainer],
        make_user: Callable[..., User],
        maintainer: NixMaintainer,
    ) -> None:
        """
        When cache_new_suggestions() creates a CachedSuggestions record for the
        first time, notifications should be created for subscribed users.
        """
        # Create a user whose username matches the maintainer's github handle,
        # with auto_subscribe_to_maintained_packages=True (the default).
        user = make_user(
            username=maintainer.github,
            uid=str(maintainer.github_id),
            is_staff=False,
            is_committer=False,
        )

        suggestion = make_suggestion()

        # Precondition: no cached suggestion and no notifications yet
        assert not CachedSuggestions.objects.filter(proposal=suggestion).exists()
        assert Notification.objects.filter(user=user).count() == 0

        # Act: cache the suggestion for the first time
        cache_new_suggestions(suggestion)

        # Postcondition: cache exists AND notification was created
        assert CachedSuggestions.objects.filter(proposal=suggestion).exists()
        assert Notification.objects.filter(user=user).count() == 1

    def test_no_duplicate_notifications_on_cache_update(
        self,
        make_suggestion: Callable[..., CVEDerivationClusterProposal],
        make_drv: Callable[..., NixDerivation],
        make_maintainer: Callable[..., NixMaintainer],
        make_user: Callable[..., User],
        maintainer: NixMaintainer,
    ) -> None:
        """
        When cache_new_suggestions() is called a second time on the same
        suggestion (cache update), NO additional notifications should be created.
        """
        user = make_user(
            username=maintainer.github,
            uid=str(maintainer.github_id),
            is_staff=False,
            is_committer=False,
        )

        suggestion = make_suggestion()

        # First call: creates cache + notification
        cache_new_suggestions(suggestion)
        assert Notification.objects.filter(user=user).count() == 1

        # Second call: updates cache, should NOT create another notification
        cache_new_suggestions(suggestion)
        assert Notification.objects.filter(user=user).count() == 1

    def test_cache_exists_before_notification(
        self,
        make_suggestion: Callable[..., CVEDerivationClusterProposal],
        make_drv: Callable[..., NixDerivation],
    ) -> None:
        """
        After cache_new_suggestions() returns, the CachedSuggestions record
        must exist. This is the core invariant that fixes the race condition.
        """
        suggestion = make_suggestion()

        cache_new_suggestions(suggestion)

        cached = CachedSuggestions.objects.filter(proposal=suggestion).first()
        assert cached is not None
        assert cached.payload is not None
