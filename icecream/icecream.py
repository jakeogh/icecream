#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# IceCream - A little library for sweet and creamy print debugging.
#
# Ansgar Grunseid
# grunseid.com
# grunseid@gmail.com
#
# License: MIT
#


# pylint: disable=C0111     # docstrings are always outdated and wrong
# pylint: disable=W0511     # todo is encouraged
# pylint: disable=C0301     # line too long
# pylint: disable=R0902     # too many instance attributes
# pylint: disable=C0302     # too many lines in module
# pylint: disable=C0103     # single letter var names, func name too descriptive
# pylint: disable=R0911     # too many return statements
# pylint: disable=R0912     # too many branches
# pylint: disable=R0915     # too many statements
# pylint: disable=R0913     # too many arguments
# pylint: disable=R1702     # too many nested blocks
# pylint: disable=R0914     # too many local variables
# pylint: disable=R0903     # too few public methods
# pylint: disable=E1101     # no member for base
# pylint: disable=W0201     # attribute defined outside __init__
# pylint: disable=W0201     # attribute defined outside __init__


#import ast
import inspect
#import pprint
import sys
from contextlib import contextmanager
from datetime import datetime
from os.path import basename
from textwrap import dedent

import colorama
import executing
from pygments import highlight
# See https://gist.github.com/XVilka/8346728 for color support in various
# terminals and thus whether to use Terminal256Formatter or
# TerminalTrueColorFormatter.
from pygments.formatters import Terminal256Formatter
from pygments.lexers import Python3Lexer

from .coloring import SolarizedDark


_absent = object()


def eprint(*args, **kwargs):
    if 'file' in kwargs.keys():
        kwargs.pop('file')
    print(*args, file=sys.stderr, **kwargs)


def format_time():
    now = datetime.utcnow()
    formatted = now.strftime('%H:%M:%S.%f')[:-3]
    return ' at %s' % formatted


def get_context(callFrame, callNode):
    lineNumber = callNode.lineno
    frameInfo = inspect.getframeinfo(callFrame)
    parentFunction = frameInfo.function
    filename = basename(frameInfo.filename)
    return filename, lineNumber, parentFunction


def format_context(callFrame, callNode):
    filename, lineNumber, parentFunction = get_context(callFrame, callNode)

    if parentFunction != '<module>':
        parentFunction = '%s()' % parentFunction

    context = '%s:%s in %s' % (filename, lineNumber, parentFunction)
    return context


def bind_static_variable(name, value):
    def decorator(fn):
        setattr(fn, name, value)
        return fn
    return decorator


@bind_static_variable('formatter', Terminal256Formatter(style=SolarizedDark))
@bind_static_variable('lexer', Python3Lexer(ensurenl=False))
def colorize(s):
    self = colorize
    return highlight(s, self.lexer, self.formatter)


@contextmanager
def supportTerminalColorsInWindows():
    # Filter and replace ANSI escape sequences on Windows with equivalent Win32
    # API calls. This code does nothing on non-Windows systems.
    colorama.init()
    yield
    colorama.deinit()


def colorized_stderr_print(s):
    colored = colorize(s)
    with supportTerminalColorsInWindows():
        eprint(colored)


DEFAULT_PREFIX = 'ic| '
DEFAULT_CONTEXT_DELIMITER = '- '
#DEFAULT_ARG_TO_STRING_FUNCTION = pprint.pformat
DEFAULT_ARG_TO_STRING_FUNCTION = repr


class NoSourceAvailableError(OSError):
    """
    Raised when icecream fails to find or access required source code
    to parse and analyze. This can happen, for example, when

      - ic() is invoked inside an interactive shell, e.g. python -i

      - The source code is mangled and/or packaged, like with a project
        freezer like PyInstaller.

      - The underlying source code changed during execution. See
        https://stackoverflow.com/a/33175832.
    """
    infoMessage = (
        'Failed to access the underlying source code for analysis. Was ic() '
        'invoked in an interpreter (e.g. python -i), a frozen application '
        '(e.g. packaged with PyInstaller), or did the underlying source code '
        'change during execution?')


def callOrValue(obj):
    return obj() if callable(obj) else obj


class Source(executing.Source):
    def get_text_with_indentation(self, node):
        result = self.asttokens().get_text(node)
        if '\n' in result:
            result = ' ' * node.first_token.start[1] + result
            result = dedent(result)
        result = result.strip()
        return result


def prefixLinesAfterFirst(prefix, s):
    lines = s.splitlines(True)

    for i in range(1, len(lines)):
        lines[i] = prefix + lines[i]

    return ''.join(lines)


def indented_lines(prefix, string):
    lines = string.splitlines()
    return [prefix + lines[0]] + [
        ' ' * len(prefix) + line
        for line in lines[1:]
    ]


def format_pair(prefix, arg, value):
    arg_lines = indented_lines(prefix, arg)
    value_prefix = arg_lines[-1] + ': '

    looksLikeAString = value[0] + value[-1] in ["''", '""']
    if looksLikeAString:  # Align the start of multiline strings.
        value = prefixLinesAfterFirst(' ', value)

    value_lines = indented_lines(value_prefix, value)
    lines = arg_lines[:-1] + value_lines
    return '\n'.join(lines)


def argumentToString(obj):
    s = DEFAULT_ARG_TO_STRING_FUNCTION(obj)
    s = s.replace('\\n', '\n')  # Preserve string newlines in output.
    return s


class IceCreamDebugger:
    _pairDelimiter = ', '  # Used by the tests in tests/.
    contextDelimiter = DEFAULT_CONTEXT_DELIMITER

    def __init__(self, prefix=DEFAULT_PREFIX,
                 argToStringFunction=argumentToString, includeContext=True):
        self.prefix = prefix
        self.includeContext = includeContext
        self.argToStringFunction = argToStringFunction

    def __call__(self, *args):
        callFrame = inspect.currentframe().f_back
        try:
            out = self._format(callFrame, *args)
        except NoSourceAvailableError as err:
            prefix = callOrValue(self.prefix)
            out = prefix + 'Error: ' + err.infoMessage
        colorized_stderr_print(out)

        if not args:            # E.g. ic().
            passthrough = None
        elif len(args) == 1:    # E.g. ic(1).
            passthrough = args[0]
        else:                   # E.g. ic(1, 2, 3).
            passthrough = args

        return passthrough

    def format(self, *args):
        callFrame = inspect.currentframe().f_back
        out = self._format(callFrame, *args)
        #eprint(out)
        return out

    def _format(self, callFrame, *args):
        eprint("args:", args)
        prefix = callOrValue(self.prefix)
        #eprint("prefix:", prefix)  # ic|

        callNode = Source.executing(callFrame).node
        if callNode is None:
            raise NoSourceAvailableError()

        context = format_context(callFrame, callNode)
        eprint("context:", context)
        if not args:
            time = format_time()
            out = prefix + context + time
        else:
            if not self.includeContext:
                context = ''
            out = self._formatArgs(callFrame, callNode, prefix, context, args)

        #eprint(out)
        return out

    def _formatArgs(self, callFrame, callNode, prefix, context, args):
        source = Source.for_frame(callFrame)
        sanitizedArgStrs = [
            source.get_text_with_indentation(arg)
            for arg in callNode.args]

        pairs = list(zip(sanitizedArgStrs, args))

        out = self._constructArgumentOutput(prefix, context, pairs)
        return out

    def _constructArgumentOutput(self, prefix, context, pairs):
        def argPrefix(arg):
            return '%s: ' % arg

        pairs = [(arg, self.argToStringFunction(val)) for arg, val in pairs]

        allArgsOnOneLine = self._pairDelimiter.join(
            val if arg == val else argPrefix(arg) + val for arg, val in pairs)

        contextDelimiter = self.contextDelimiter if context else ''
        lines = [prefix + context + contextDelimiter + allArgsOnOneLine]

        return '\n'.join(lines)

    def configureOutput(self,
                        prefix=_absent,
                        argToStringFunction=_absent,
                        includeContext=_absent):
        if prefix is not _absent:
            self.prefix = prefix

        if argToStringFunction is not _absent:
            self.argToStringFunction = argToStringFunction

        if includeContext is not _absent:
            self.includeContext = includeContext


ic = IceCreamDebugger()
