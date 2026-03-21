import pytest
from django.test import Client
from django.urls import reverse

from shared.models.linkage import CVEDerivationClusterProposal


@pytest.fixture
def staff_client(client: Client, user) -> Client:
    """An authenticated staff client, sufficient for read-only list/detail views."""
    client.force_login(user)
    return client


def test_uncached_suggestion_excluded_from_list(
    staff_client: Client,
    suggestion: CVEDerivationClusterProposal,
) -> None:
    """A suggestion without a cached value must not appear in the list view."""
    response = staff_client.get(reverse("webview:suggestion:untriaged_suggestions"))

    assert response.status_code == 200
    suggestion_ids = [s.suggestion.pk for s in response.context["suggestions"]]
    assert suggestion.pk not in suggestion_ids


def test_cached_suggestion_included_in_list(
    staff_client: Client,
    cached_suggestion: CVEDerivationClusterProposal,
) -> None:
    """A suggestion with a cached value must appear in the list view."""
    response = staff_client.get(reverse("webview:suggestion:untriaged_suggestions"))

    assert response.status_code == 200
    suggestion_ids = [s.suggestion.pk for s in response.context["suggestions"]]
    assert cached_suggestion.pk in suggestion_ids


def test_uncached_suggestion_detail_returns_404(
    staff_client: Client,
    suggestion: CVEDerivationClusterProposal,
) -> None:
    """Accessing the detail page of a suggestion without a cached value must return 404."""
    response = staff_client.get(
        reverse("webview:suggestion:detail", kwargs={"suggestion_id": suggestion.pk})
    )

    assert response.status_code == 404


def test_cached_suggestion_detail_returns_200(
    staff_client: Client,
    cached_suggestion: CVEDerivationClusterProposal,
) -> None:
    """Accessing the detail page of a suggestion with a cached value must return 200."""
    response = staff_client.get(
        reverse(
            "webview:suggestion:detail", kwargs={"suggestion_id": cached_suggestion.pk}
        )
    )

    assert response.status_code == 200
