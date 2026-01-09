from automation_hub.processors.command_parser import parse_command


def test_parse_help():
    command = parse_command("  help ")
    assert command is not None
    assert command.name == "HELP"


def test_parse_news_topic():
    command = parse_command("NEWS  space  exploration")
    assert command is not None
    assert command.name == "NEWS"
    assert command.topic == "SPACE EXPLORATION"


def test_parse_shortcuts():
    assert parse_command("!").name == "NEWS"
    assert parse_command(" n ").name == "NEWS"
