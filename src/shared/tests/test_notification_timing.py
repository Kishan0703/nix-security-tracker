"""
Tests for the notification timing fix (issue #829).

Verifies that:
1. Notifications ARE created for subscribed users when cache_new_suggestions()
   is called for the first time on a suggestion.
2. NO duplicate notifications are created when cache_new_suggestions() is called
   again on the same suggestion (cache update, not creation).
"""

from collections.abc import Callable
from unittest.mock import patch

import pytest
from django.contrib.auth.models import User

from shared.listeners.cache_suggestions import cache_new_suggestions
from shared.models.cached import CachedSuggestions
from shared.models.linkage import CVEDerivationClusterProposal, ProvenanceFlags
from shared.models.nix_evaluation import NixMaintainer
from webview.models import SuggestionNotification as Notification


def test_notifications_created_on_first_cache(
    make_suggestion: Callable[..., CVEDerivationClusterProposal],
    make_user: Callable[..., User],
) -> None:
    """
    When cache_new_suggestions() creates a CachedSuggestions record for the
    first time, notifications should be created for subscribed users.
    """
    suggestion = make_suggestion()

    first_drv = suggestion.derivations.first()
    assert first_drv is not None
    assert first_drv.metadata is not None
    maintainer = first_drv.metadata.maintainers.first()
    assert maintainer is not None

    # Create a user whose username matches the maintainer's github handle,
    # with auto_subscribe_to_maintained_packages=True (the default).
    user = make_user(
        username=maintainer.github,
        uid=str(maintainer.github_id),
        is_staff=False,
        is_committer=False,
    )

    # Precondition: no cached suggestion and no notifications yet
    assert not CachedSuggestions.objects.filter(proposal=suggestion).exists()
    assert Notification.objects.filter(user=user).count() == 0

    # Act: cache the suggestion for the first time
    cache_new_suggestions(suggestion)

    # Postcondition: cache exists AND notification was created
    assert CachedSuggestions.objects.filter(proposal=suggestion).exists()
    assert Notification.objects.filter(user=user).count() == 1

def test_no_duplicate_notifications_on_cache_update(
    make_suggestion: Callable[..., CVEDerivationClusterProposal],
    make_user: Callable[..., User],
) -> None:
    """
    When cache_new_suggestions() is called a second time on the same
    suggestion (cache update), NO additional notifications should be created.
    """
    suggestion = make_suggestion()

    first_drv = suggestion.derivations.first()
    assert first_drv is not None
    assert first_drv.metadata is not None
    maintainer = first_drv.metadata.maintainers.first()
    assert maintainer is not None

    user = make_user(
        username=maintainer.github,
        uid=str(maintainer.github_id),
        is_staff=False,
        is_committer=False,
    )

    # First call: creates cache + notification
    cache_new_suggestions(suggestion)
    assert Notification.objects.filter(user=user).count() == 1

    # Second call: updates cache, should NOT create another notification
    cache_new_suggestions(suggestion)
    assert Notification.objects.filter(user=user).count() == 1

def test_cache_exists_before_notification(
    make_suggestion: Callable[..., CVEDerivationClusterProposal],
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

def test_notification_failure_propagates(
    make_suggestion: Callable[..., CVEDerivationClusterProposal],
) -> None:
    """
    If create_package_subscription_notifications() crashes, the exception
    must propagate out of cache_new_suggestions() so the pgpubsub worker
    can retry. Notifications must never be silently dropped.
    """
    suggestion = make_suggestion()

    with patch(
        "shared.listeners.cache_suggestions.create_package_subscription_notifications",
        side_effect=RuntimeError("notification service unavailable"),
    ):
        with pytest.raises(RuntimeError, match="notification service unavailable"):
            cache_new_suggestions(suggestion)

    assert CachedSuggestions.objects.filter(proposal=suggestion).exists()

def test_notifications_fallback_on_cache_failure(
    make_suggestion: Callable[..., CVEDerivationClusterProposal],
    make_user: Callable[..., User],
) -> None:
    """
    If cache generation fails on the first attempt, notifications must STILL
    be created as a fallback to prevent them from being lost.
    """
    suggestion = make_suggestion()

    first_drv = suggestion.derivations.first()
    assert first_drv is not None
    assert first_drv.metadata is not None
    maintainer = first_drv.metadata.maintainers.first()
    assert maintainer is not None

    user = make_user(
        username=maintainer.github,
        uid=str(maintainer.github_id),
        is_staff=False,
        is_committer=False,
    )

    # Simulate a crash inside the cache generation logic
    with patch(
        "shared.listeners.cache_suggestions._generate_and_save_cache",
        side_effect=RuntimeError("simulate cache generation crash"),
    ):
        with pytest.raises(RuntimeError, match="simulate cache generation crash"):
            cache_new_suggestions(suggestion)

    # Cache should NOT exist because it crashed before saving
    assert not CachedSuggestions.objects.filter(proposal=suggestion).exists()
    
    # But notifications MUST exist as a fallback!
    assert Notification.objects.filter(user=user).count() == 1

    # Now simulate a retry by pgpubsub worker that crashes AGAIN
    with patch(
        "shared.listeners.cache_suggestions._generate_and_save_cache",
        side_effect=RuntimeError("simulate cache generation crash 2"),
    ):
        with pytest.raises(RuntimeError, match="simulate cache generation crash 2"):
            cache_new_suggestions(suggestion)

    # Notifications should STILL be exactly 1 (no duplicates!)
    assert Notification.objects.filter(user=user).count() == 1

    # Now simulate a successful retry by pgpubsub worker
    cache_new_suggestions(suggestion)

    # Cache should NOW exist
    assert CachedSuggestions.objects.filter(proposal=suggestion).exists()

    # Notifications should STILL be exactly 1 (no duplicates!)
    assert Notification.objects.filter(user=user).count() == 1
