import mock
import sys
from cron_sentry.runner import CommandReporter, MAX_MESSAGE_SIZE, run, parser


@mock.patch('cron_sentry.runner.Client')
def test_command_reporter_accepts_parameters(ClientMock):
    reporter = CommandReporter(['date', '--invalid-option'], 'http://testdsn')

    reporter.run()

    client = ClientMock()
    assert client.captureMessage.called


@mock.patch('cron_sentry.runner.Client')
def test_command_reporter_works_with_no_params_commands(ClientMock):
    reporter = CommandReporter(['date'], 'http://testdsn')

    reporter.run()

    client = ClientMock()
    assert not client.captureMessage.called


@mock.patch('cron_sentry.runner.sys')
@mock.patch('cron_sentry.runner.Client')
def test_command_reporter_keeps_stdout_and_stderr(ClientMock, sys_mock):
    command = [sys.executable, '-c', """
import sys
sys.stdout.write("test-out")
sys.stderr.write("test-err")
sys.exit(2)
"""]
    reporter = CommandReporter(command, 'http://testdsn')
    client = ClientMock()

    reporter.run()

    sys_mock.stdout.write.assert_called_with('test-out')
    sys_mock.stderr.write.assert_called_with('test-err')
    client.captureMessage.assert_called_with(
        mock.ANY,
        time_spent=mock.ANY,
        data=mock.ANY,
        extra={
            'command': command,
            'exit_status': 2,
            "last_lines_stdout": "test-out",
            "last_lines_stderr": "test-err",
    })


@mock.patch('cron_sentry.runner.sys')
@mock.patch('cron_sentry.runner.Client')
def test_reports_correctly_to_with_long_messages_but_trims_stdout_and_stderr(ClientMock, sys_mock):
    command = [sys.executable, '-c', """
import sys
sys.stdout.write("a" * 2000)
sys.stderr.write("b" * 2000)
sys.exit(2)
"""]
    reporter = CommandReporter(command, 'http://testdsn')
    client = ClientMock()

    reporter.run()
    expected_stdout = u'...{}'.format('a' * (MAX_MESSAGE_SIZE - 3))
    expected_stderr = u'...{}'.format('b' * (MAX_MESSAGE_SIZE - 3))

    sys_mock.stdout.write.assert_called_with(expected_stdout)
    sys_mock.stderr.write.assert_called_with(expected_stderr)
    client.captureMessage.assert_called_with(
        mock.ANY,
        time_spent=mock.ANY,
        data=mock.ANY,
        extra={
            'command': command,
            'exit_status': 2,
            "last_lines_stdout": expected_stdout,
            "last_lines_stderr": expected_stderr,
    })


@mock.patch('cron_sentry.runner.CommandReporter')
def test_command_line_should_support_command_args_without_double_dashes(CommandReporterMock):
    command = ['--dsn', 'http://testdsn', 'command', '--arg1', 'value1', '--arg2', 'value2']

    run(command)

    CommandReporterMock.assert_called_with(
        cmd=command[2:],
        dsn='http://testdsn')


@mock.patch('cron_sentry.runner.CommandReporter')
def test_command_line_should_support_command_with_double_dashes(CommandReporterMock):
    command = ['--dsn', 'http://testdsn', '--', 'command', '--arg1', 'value1', '--arg2', 'value2']

    run(command)

    CommandReporterMock.assert_called_with(
        cmd=command[3:],
        dsn='http://testdsn')


@mock.patch('cron_sentry.runner.sys')
@mock.patch('argparse._sys')
@mock.patch('cron_sentry.runner.CommandReporter')
def test_should_display_help_text_and_exit_with_1_if_no_command_is_specified(CommandReporterMock, argparse_sys, cron_sentry_sys):
    command = []

    run(command)

    cron_sentry_sys.stderr.write("ERROR: Missing command parameter!\n")
    argparse_sys.stdout.write.assert_called_with(parser.format_usage())
    cron_sentry_sys.exit.assert_called_with(1)
    assert not CommandReporterMock.called
