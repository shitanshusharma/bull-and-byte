from src import config


def test_get_chat_ids_merges_and_dedupes(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "111")
    monkeypatch.setenv("TELEGRAM_CHAT_IDS", "111, 222 333")
    assert config.get_chat_ids() == ["111", "222", "333"]


def test_get_chat_ids_empty(monkeypatch):
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_IDS", raising=False)
    assert config.get_chat_ids() == []


def test_ai_summaries_disabled_without_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    assert config.ai_summaries_enabled() is False


def test_ai_summaries_killswitch(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "secret")
    monkeypatch.setenv("AI_SUMMARIES", "0")
    assert config.ai_summaries_enabled() is False
    monkeypatch.setenv("AI_SUMMARIES", "1")
    assert config.ai_summaries_enabled() is True


def test_positive_int_env_validation(monkeypatch):
    monkeypatch.setenv("X", "abc")
    assert config.positive_int_env("X", 26) == 26
    monkeypatch.setenv("X", "-5")
    assert config.positive_int_env("X", 26) == 26
    monkeypatch.setenv("X", "10")
    assert config.positive_int_env("X", 26) == 10


def test_load_dotenv_refreshes_window_hours(tmp_path, monkeypatch):
    # WINDOW_HOURS is computed at import (before .env is read); load_dotenv()
    # must refresh it so a value set only in .env is honored, not ignored.
    monkeypatch.setattr(config, "BASE_DIR", tmp_path)
    monkeypatch.delenv("WINDOW_HOURS", raising=False)
    (tmp_path / ".env").write_text("WINDOW_HOURS=7\n", encoding="utf-8")
    original = config.WINDOW_HOURS
    try:
        config.load_dotenv()
        assert config.WINDOW_HOURS == 7
    finally:
        config.WINDOW_HOURS = original
        monkeypatch.delenv("WINDOW_HOURS", raising=False)
