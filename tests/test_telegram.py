from src.delivery import telegram


def _no_sleep(monkeypatch):
    monkeypatch.setattr(telegram.time, "sleep", lambda *_a, **_k: None)


def test_send_all_success_records_ids_per_chat(monkeypatch):
    _no_sleep(monkeypatch)
    monkeypatch.setattr(telegram, "send_telegram", lambda *a, **k: True)
    messages = [("m1", ["a", "b"]), ("m2", ["c"])]
    delivered, failures, per_chat = telegram.send_all("tok", ["1", "2"], messages)
    assert delivered == ["a", "b", "c"]
    assert failures == 0
    assert per_chat == {"1": 2, "2": 2}


def test_send_all_id_kept_if_at_least_one_chat_succeeds(monkeypatch):
    _no_sleep(monkeypatch)
    # chat "1" always succeeds, chat "2" always fails
    monkeypatch.setattr(telegram, "send_telegram",
                        lambda token, chat_id, text: chat_id == "1")
    messages = [("m1", ["a"])]
    delivered, failures, per_chat = telegram.send_all("tok", ["1", "2"], messages)
    assert delivered == ["a"]      # reached at least one chat
    assert failures == 1           # the failed chat is counted
    assert per_chat == {"1": 1, "2": 0}


def test_send_all_id_dropped_if_all_chats_fail(monkeypatch):
    _no_sleep(monkeypatch)
    monkeypatch.setattr(telegram, "send_telegram", lambda *a, **k: False)
    messages = [("m1", ["a", "b"])]
    delivered, failures, per_chat = telegram.send_all("tok", ["1"], messages)
    assert delivered == []
    assert failures == 1
