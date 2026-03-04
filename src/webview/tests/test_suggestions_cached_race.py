from collections.abc import Callable

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from shared.models.linkage import CVEDerivationClusterProposal


@pytest.mark.django_db
class TestSuggestionListViewCachedFilter:
    """Verify that the list view filters out suggestions without a cached value."""

    def test_uncached_suggestion_excluded_from_list(
        self,
        client: Client,
        user: User,
        make_suggestion: Callable[..., CVEDerivationClusterProposal],
    ) -> None:
        """A suggestion WITHOUT a cached value should not appear in the list view."""
        suggestion = make_suggestion()
        client.force_login(user)
        response = client.get(
            reverse("webview:suggestion:untriaged_suggestions"),
        )
        assert response.status_code == 200
        suggestions = response.context["suggestions"]
        suggestion_ids = [s.suggestion.pk for s in suggestions]
        assert suggestion.pk not in suggestion_ids

    def test_cached_suggestion_included_in_list(
        self,
        client: Client,
        user: User,
        make_cached_suggestion: Callable[..., CVEDerivationClusterProposal],
    ) -> None:
        """A suggestion WITH a cached value should appear in the list view."""
        suggestion = make_cached_suggestion()
        client.force_login(user)
        response = client.get(
            reverse("webview:suggestion:untriaged_suggestions"),
        )
        assert response.status_code == 200
        suggestions = response.context["suggestions"]
        suggestion_ids = [s.suggestion.pk for s in suggestions]
        assert suggestion.pk in suggestion_ids


@pytest.mark.django_db
class TestSuggestionDetailViewCachedGuard:
    """Verify that the detail view returns 404 for uncached suggestions."""

    def test_uncached_suggestion_returns_404(
        self,
        client: Client,
        user: User,
        make_suggestion: Callable[..., CVEDerivationClusterProposal],
    ) -> None:
        """Accessing a suggestion WITHOUT a cached value should return 404, not 500."""
        suggestion = make_suggestion()
        client.force_login(user)
        response = client.get(
            reverse(
                "webview:suggestion:detail",
                kwargs={"suggestion_id": suggestion.pk},
            ),
        )
        assert response.status_code == 404

    def test_cached_suggestion_returns_200(
        self,
        client: Client,
        user: User,
        make_cached_suggestion: Callable[..., CVEDerivationClusterProposal],
    ) -> None:
        """Accessing a suggestion WITH a cached value should return 200."""
        suggestion = make_cached_suggestion()
        client.force_login(user)
        response = client.get(
            reverse(
                "webview:suggestion:detail",
                kwargs={"suggestion_id": suggestion.pk},
            ),
        )
        assert response.status_code == 200
