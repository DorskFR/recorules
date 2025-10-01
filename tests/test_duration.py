"""Tests for Duration class."""

from recorules.duration import Duration


def test_parse():
    """Test parsing duration strings."""
    assert Duration.parse("09:30").minutes == 9 * 60 + 30
    assert Duration.parse("00:00").minutes == 0
    assert Duration.parse("23:59").minutes == 23 * 60 + 59
    assert Duration.parse("").minutes == 0


def test_str():
    """Test string representation."""
    assert str(Duration(90)) == "01:30"
    assert str(Duration(0)) == "00:00"
    assert str(Duration(-30)) == "-00:30"
    assert str(Duration(8 * 60)) == "08:00"


def test_addition():
    """Test duration addition."""
    d1 = Duration(60)  # 1 hour
    d2 = Duration(30)  # 30 minutes
    result = d1 + d2
    assert result.minutes == 90


def test_subtraction():
    """Test duration subtraction."""
    d1 = Duration(90)  # 1.5 hours
    d2 = Duration(30)  # 30 minutes
    result = d1 - d2
    assert result.minutes == 60


def test_multiplication():
    """Test duration multiplication."""
    d = Duration(60)  # 1 hour
    result = d * 3
    assert result.minutes == 180


def test_negation():
    """Test duration negation."""
    d = Duration(60)
    result = -d
    assert result.minutes == -60


def test_comparison():
    """Test duration comparisons."""
    d1 = Duration(60)
    d2 = Duration(90)

    assert d1 < d2
    assert d2 > d1
    assert d1 <= d2
    assert d2 >= d1
    assert d1 == Duration(60)
    assert d1 != d2


def test_abs():
    """Test absolute value."""
    assert abs(Duration(-60)).minutes == 60
    assert abs(Duration(60)).minutes == 60


def test_bool():
    """Test boolean conversion."""
    assert bool(Duration(1)) is True
    assert bool(Duration(0)) is False
    assert bool(Duration(-1)) is False
