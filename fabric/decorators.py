"""
Convenience decorators for use in fabfiles.
"""

from functools import wraps
from fabric.utils import warn
from fabric.context_managers import settings


def task(*args, **kwargs):
    """Decorate an object as being a fabric command task."""
    task.used = 1
    display = kwargs.get('display', 1)
    if args:
        if callable(args[0]):
            func = args[0]
            func.__fabtask__ = 1
            if not display:
                func.__hide__ = 1
            return func
        ctx = args
        if len(ctx) == 1 and not isinstance(ctx[0], basestring):
            ctx = tuple(args[0])
    else:
        ctx = ()
    def __task(__func):
        # set the context
        def dec(*args, **kwargs):
            if len(ctx) > 0:
                with settings(ctx=ctx):
                    return __func(*args, **kwargs)
            else:
                return __func(*args, **kwargs)

        dec.__ctx__ = ctx
        dec.__fabtask__ = 1
        dec.__doc__ = __func.__doc__
        dec.__name__ = __func.__name__
        dec._decorated = __func
        if not display:
            dec.__hide__ = 1
        return dec
    return __task

task.used = None


def hosts(*host_list):
    """
    Decorator defining which host or hosts to execute the wrapped function on.

    For example, the following will ensure that, barring an override on the
    command line, ``my_func`` will be run on ``host1``, ``host2`` and
    ``host3``, and with specific users on ``host1`` and ``host3``::

        @hosts('user1@host1', 'host2', 'user2@host3')
        def my_func():
            pass

    `~fabric.decorators.hosts` may be invoked with either an argument list
    (``@hosts('host1')``, ``@hosts('host1', 'host2')``) or a single, iterable
    argument (``@hosts(['host1', 'host2'])``).

    Note that this decorator actually just sets the function's ``.hosts``
    attribute, which is then read prior to executing the function.

    .. versionchanged:: 0.9.2
        Allow a single, iterable argument (``@hosts(iterable)``) to be used
        instead of requiring ``@hosts(*iterable)``.
    """
    def attach_hosts(func):
        _hosts = host_list
        # Allow for single iterable argument as well as *args
        if len(_hosts) == 1 and not isinstance(_hosts[0], basestring):
            _hosts = _hosts[0]
        func.hosts = list(_hosts)
        return func
    return attach_hosts


def roles(*role_list):
    """
    Decorator defining a list of role names, used to look up host lists.

    A role is simply defined as a key in `env` whose value is a list of one or
    more host connection strings. For example, the following will ensure that,
    barring an override on the command line, ``my_func`` will be executed
    against the hosts listed in the ``webserver`` and ``dbserver`` roles::

        env.roledefs.update({
            'webserver': ['www1', 'www2'],
            'dbserver': ['db1']
        })

        @roles('webserver', 'dbserver')
        def my_func():
            pass

    As with `~fabric.decorators.hosts`, `~fabric.decorators.roles` may be
    invoked with either an argument list or a single, iterable argument.
    Similarly, this decorator uses the same mechanism as
    `~fabric.decorators.hosts` and simply sets ``<function>.roles``.

    .. versionchanged:: 0.9.2
        Allow a single, iterable argument to be used (same as
        `~fabric.decorators.hosts`).
    """
    def attach_roles(func):
        _roles = role_list
        # Allow for single iterable argument as well as *args
        if len(_roles) == 1 and not isinstance(_roles[0], basestring):
            _roles = _roles[0]
        func.roles = list(_roles)
        return func
    return attach_roles


def runs_once(func):
    warn("The runs_once spelling is deprecated, use run_once instead.")
    return run_once(func)

def run_once(func):
    """
    Decorator preventing wrapped function from running more than once.

    By keeping internal state, this decorator allows you to mark a function
    such that it will only run once per Python interpreter session, which in
    typical use means "once per invocation of the ``fab`` program".

    Any function wrapped with this decorator will silently fail to execute the
    2nd, 3rd, ..., Nth time it is called, and will return the value of the
    original run.
    """
    @wraps(func)
    def decorated(*args, **kwargs):
        if not hasattr(decorated, 'return_value'):
            decorated.return_value = func(*args, **kwargs)
        return decorated.return_value
    decorated._decorated = func
    return decorated
