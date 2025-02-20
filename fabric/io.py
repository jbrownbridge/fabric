import sys

from select import select

from fabric.auth import get_password, set_password
from fabric.network import prompt_for_password
from fabric.state import env, output, win32, io_sleep

if win32:
    import msvcrt


def _flush(pipe, text):
    pipe.write(text)
    pipe.flush()


def _endswith(char_list, substring):
    tail = char_list[-1*len(substring):]
    substring = list(substring)
    return tail == substring


def output_loop(chan, which, capture):
    # Obtain stdout or stderr related values
    func = getattr(chan, which)
    if which == 'recv':
        prefix = "out"
        pipe = sys.stdout
    else:
        prefix = "err"
        pipe = sys.stderr
    host_prefix = "[%s]" % env.host_string
    if env.colors:
        host_prefix = env.color_settings['host_prefix'](host_prefix)
    printing = getattr(output, 'stdout' if (which == 'recv') else 'stderr')
    # Initialize loop variables
    reprompt = False
    initial_prefix_printed = False
    while True:
        # Handle actual read/write
        byte = func(1)
        if byte == '':
            break
        # A None capture variable implies that we're in open_shell()
        if capture is None:
            # Just print directly -- no prefixes, no capturing, nada
            # And since we know we're using a pty in this mode, just go
            # straight to stdout.
            _flush(sys.stdout, byte)
        # Otherwise, we're in run/sudo and need to handle capturing and
        # prompts.
        else:
            _prefix = "[%s] %s: " % (env.host_string, prefix)
            # Print to user
            if printing:
                # Initial prefix
                if not initial_prefix_printed:
                    _flush(pipe, _prefix)
                    initial_prefix_printed = True
                # Byte itself
                _flush(pipe, byte)
                # Trailing prefix to start off next line
                if byte in ("\n", "\r"):
                    _flush(pipe, _prefix)
            # Store in capture buffer
            capture += byte
            # Handle prompts
            prompt = _endswith(capture, env.sudo_prompt)
            try_again = (_endswith(capture, env.again_prompt + '\n')
                or _endswith(capture, env.again_prompt + '\r\n'))
            if prompt:
                # Obtain cached password, if any
                password = get_password()
                # Remove the prompt itself from the capture buffer. This is
                # backwards compatible with Fabric 0.9.x behavior; the user
                # will still see the prompt on their screen (no way to avoid
                # this) but at least it won't clutter up the captured text.
                del capture[-1*len(env.sudo_prompt):]
                # If the password we just tried was bad, prompt the user again.
                if (not password) or reprompt:
                    # Print the prompt and/or the "try again" notice if
                    # output is being hidden. In other words, since we need
                    # the user's input, they need to see why we're
                    # prompting them.
                    if not printing:
                        _flush(pipe, _prefix)
                        if reprompt:
                            _flush(pipe, env.again_prompt + '\n' + _prefix)
                        _flush(pipe, env.sudo_prompt)
                    # Prompt for, and store, password. Give empty prompt so the
                    # initial display "hides" just after the actually-displayed
                    # prompt from the remote end.
                    password = prompt_for_password(
                        prompt=" ", no_colon=True, stream=pipe
                    )
                    # Update env.password, env.passwords if necessary
                    set_password(password)
                    # Reset reprompt flag
                    reprompt = False
                # Send current password down the pipe
                chan.sendall(password + '\n')
            elif try_again:
                # Remove text from capture buffer
                capture = capture[:len(env.again_prompt)]
                # Set state so we re-prompt the user at the next prompt.
                reprompt = True


def input_loop(chan, using_pty):
    while not chan.exit_status_ready():
        if win32:
            have_char = msvcrt.kbhit()
        else:
            r, w, x = select([sys.stdin], [], [], io_sleep)
            have_char = (r and r[0] == sys.stdin)
        if have_char:
            # Send all local stdin to remote end's stdin
            byte = msvcrt.getch() if win32 else sys.stdin.read(1)
            chan.sendall(byte)
            # Optionally echo locally, if needed.
            if not using_pty and env.echo_stdin:
                # Not using fastprint() here -- it prints as 'user'
                # output level, don't want it to be accidentally hidden
                sys.stdout.write(byte)
                sys.stdout.flush()
