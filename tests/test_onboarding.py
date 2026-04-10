from dailyai.ui.components.onboarding import onboarding_dialog


def test_onboarding():
    d = onboarding_dialog("en", "123-456")
    assert d is not None

