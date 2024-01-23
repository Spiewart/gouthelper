from django.urls import resolve, reverse


def test_home():
    assert reverse("contents:home") == "/"
    assert resolve("/").view_name == "contents:home"


def test_about():
    assert reverse("contents:about") == "/about/"
    assert resolve("/about/").view_name == "contents:about"


def test_decision_aids():
    assert reverse("contents:decision-aids") == "/decision-aids/"
    assert resolve("/decision-aids/").view_name == "contents:decision-aids"


def test_treatment_aids():
    assert reverse("contents:treatment-aids") == "/treatment-aids/"
    assert resolve("/treatment-aids/").view_name == "contents:treatment-aids"
