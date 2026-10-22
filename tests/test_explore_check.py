from scripts.explore.check import parse_console

STDERR = """\
[1:1:1022/092719.755111:INFO:CONSOLE:1] "hello-log", source: file:///x/t.html (1)
[1:1:1022/092719.755164:INFO:CONSOLE:1] "Uncaught ReferenceError: undefinedFn is not defined", source: file:///x/t.html (12)
[1:1:1022/092719.800000:INFO:CONSOLE(40)] "TypeError: x is null", source: file:///x/t.html (40)
[1:1:1022/092719.900000:WARNING:gpu_init.cc(12)] not a console line
"""


def test_uncaught_and_error_messages_are_errors():
    errors, _ = parse_console(STDERR)
    assert errors == [
        "Uncaught ReferenceError: undefinedFn is not defined (line 12)",
        "TypeError: x is null (line 40)",
    ]


def test_plain_logs_are_reported_but_not_errors():
    _, other = parse_console(STDERR)
    assert other == ["hello-log (line 1)"]


def test_non_console_lines_are_ignored():
    assert parse_console("[1:1:x:WARNING:foo.cc(3)] something\n") == ([], [])
