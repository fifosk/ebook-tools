from argparse import Namespace

from modules.cli import args


def test_parse_cli_args_defaults_to_run_without_command():
    parsed = args.parse_cli_args(["input.epub", "English", "Arabic"])
    assert isinstance(parsed, Namespace)
    assert getattr(parsed, "command", "run") == "run"
    assert parsed.input_file == "input.epub"


def test_parse_cli_args_interactive_subcommand():
    parsed = args.parse_cli_args(["interactive", "--config", "conf/config.local.json"])
    assert parsed.command == "interactive"
    assert parsed.config == "conf/config.local.json"
    assert parsed.interactive is True


def test_parse_cli_args_user_add_subcommand():
    parsed = args.parse_cli_args([
        "user",
        "--store",
        "users.json",
        "add",
        "alice",
        "--password",
        "secret",
        "--role",
        "admin",
    ])
    assert parsed.command == "user"
    assert parsed.user_command == "add"
    assert parsed.username == "alice"
    assert parsed.password == "secret"
    assert parsed.user_store == "users.json"


def test_parse_legacy_args_matches_positional_layout():
    parsed = args.parse_legacy_args([
        "input.epub",
        "English",
        "Arabic",
        "10",
        "output.html",
        "5",
        "+10",
    ])
    assert parsed.input_file == "input.epub"
    assert parsed.sentences_per_output_file == 10
    assert parsed.end_sentence == "+10"
