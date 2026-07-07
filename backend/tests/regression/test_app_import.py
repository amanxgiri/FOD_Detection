def test_application_imports() -> None:
    from app.main import app

    assert app.title == "FOD Detection Prototype API"
