"""Tests for TierService."""

import pytest

from src.domain.services.tier_service import TierService


def test_tier_service_boundary_0() -> None:
    """Test tier at boundary 0 (Dummies)."""
    service = TierService()
    assert service.get_tier(0) == TierService.DUMMIES


def test_tier_service_boundary_400() -> None:
    """Test tier at boundary 400 (Dummies)."""
    service = TierService()
    assert service.get_tier(400) == TierService.DUMMIES


def test_tier_service_boundary_401() -> None:
    """Test tier at boundary 401 (Enthusiast)."""
    service = TierService()
    assert service.get_tier(401) == TierService.ENTHUSIAST


def test_tier_service_boundary_700() -> None:
    """Test tier at boundary 700 (Enthusiast)."""
    service = TierService()
    assert service.get_tier(700) == TierService.ENTHUSIAST


def test_tier_service_boundary_701() -> None:
    """Test tier at boundary 701 (Amateur)."""
    service = TierService()
    assert service.get_tier(701) == TierService.AMATEUR


def test_tier_service_boundary_900() -> None:
    """Test tier at boundary 900 (Amateur)."""
    service = TierService()
    assert service.get_tier(900) == TierService.AMATEUR


def test_tier_service_boundary_901() -> None:
    """Test tier at boundary 901 (Savvy)."""
    service = TierService()
    assert service.get_tier(901) == TierService.SAVVY


def test_tier_service_boundary_1200() -> None:
    """Test tier at boundary 1200 (Savvy)."""
    service = TierService()
    assert service.get_tier(1200) == TierService.SAVVY


def test_tier_service_boundary_1201() -> None:
    """Test tier at boundary 1201 (Savvy - capped)."""
    service = TierService()
    assert service.get_tier(1201) == TierService.SAVVY


def test_tier_service_negative_exp() -> None:
    """Test that negative exp raises ValueError."""
    service = TierService()
    with pytest.raises(ValueError, match="exp must be >= 0"):
        service.get_tier(-1)


def test_tier_service_mid_range_dummies() -> None:
    """Test tier in middle of Dummies range."""
    service = TierService()
    assert service.get_tier(200) == TierService.DUMMIES


def test_tier_service_mid_range_enthusiast() -> None:
    """Test tier in middle of Enthusiast range."""
    service = TierService()
    assert service.get_tier(550) == TierService.ENTHUSIAST


def test_tier_service_mid_range_amateur() -> None:
    """Test tier in middle of Amateur range."""
    service = TierService()
    assert service.get_tier(800) == TierService.AMATEUR


def test_tier_service_high_savvy() -> None:
    """Test tier well above Savvy threshold."""
    service = TierService()
    assert service.get_tier(10000) == TierService.SAVVY
