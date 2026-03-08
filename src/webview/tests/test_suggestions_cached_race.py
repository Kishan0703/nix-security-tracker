from collections.abc import Callable

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from shared.models.linkage import CVEDerivationClusterProposal


def test_uncached_suggestion_excluded_from_list(
    client: Client,
    make_suggestion: Callable[..., CVEDerivationClusterProposal],
    make_user: Callable[..., User],
) -> None:
    """A suggestion WITHOUT a cached value should not appear in the list view."""
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
    client.force_login(user)
    response = client.get(
        reverse("webview:suggestion:untriaged_suggestions"),
    )
    assert response.status_code == 200
    suggestions = response.context["suggestions"]
    suggestion_ids = [s.suggestion.pk for s in suggestions]
    assert suggestion.pk not in suggestion_ids

def test_cached_suggestion_included_in_list(
    client: Client,
    make_cached_suggestion: Callable[..., CVEDerivationClusterProposal],
    make_user: Callable[..., User],
) -> None:
    """A suggestion WITH a cached value should appear in the list view."""
    suggestion = make_cached_suggestion()
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
    client.force_login(user)
    response = client.get(
        reverse("webview:suggestion:untriaged_suggestions"),
    )
    assert response.status_code == 200
    suggestions = response.context["suggestions"]
    suggestion_ids = [s.suggestion.pk for s in suggestions]
    assert suggestion.pk in suggestion_ids


def test_uncached_suggestion_returns_404(
    client: Client,
    make_suggestion: Callable[..., CVEDerivationClusterProposal],
    make_user: Callable[..., User],
) -> None:
    """Accessing a suggestion WITHOUT a cached value should return 404."""
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
    client.force_login(user)
    response = client.get(
        reverse(
            "webview:suggestion:detail",
            kwargs={"suggestion_id": suggestion.pk},
        ),
    )
    assert response.status_code == 404

def test_cached_suggestion_returns_200(
    client: Client,
    make_cached_suggestion: Callable[..., CVEDerivationClusterProposal],
    make_user: Callable[..., User],
) -> None:
    """Accessing a suggestion WITH a cached value should return 200."""
    suggestion = make_cached_suggestion()
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
    client.force_login(user)
    response = client.get(
        reverse(
            "webview:suggestion:detail",
            kwargs={"suggestion_id": suggestion.pk},
        ),
    )
    assert response.status_code == 200
