from automation_hub.utils.sms_utils import split_sms


def test_split_sms_single():
    assert split_sms("hello", max_len=10, split_len=5) == ["hello"]


def test_split_sms_multi():
    message = "abcdefghij" * 4
    parts = split_sms(message, max_len=10, split_len=8)
    assert len(parts) == 5
    assert parts[0].startswith("1/5 ")
