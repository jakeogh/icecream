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
import os
import sys
import time
from contextlib import contextmanager
from datetime import datetime
from os.path import basename
from os.path import dirname
from textwrap import dedent

import colorama
import executing
from pygments import highlight
# See https://gist.github.com/XVilka/8346728 for color support in various
# terminals and thus whether to use Terminal256Formatter or
# TerminalTrueColorFormatter.
from pygments.formatters import \
    Terminal256Formatter  # pylint: disable=no-name-in-module
from pygments.lexers import Python3Lexer  # pylint: disable=no-name-in-module

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


def reduce_path(path, *, root_program):
    python_version = sys.version_info
    python_version_folder = 'python' + str(python_version.major) + '.' + str(python_version.minor)
    path_basename = basename(path)
    path_dirname = dirname(path)
    if path_basename.split('.')[0] == path_dirname:
        return "''/" + path_basename

    if dirname(path) == python_version_folder:
        return "{}.{}/".format(python_version.major, python_version.minor) + path_basename
    path = path.replace('attrs generated init', 'attrs')
    if path.startswith('/'):
        path = path[1:]
    if path.startswith(root_program + '/'):
        path = path.replace(root_program, '')
    return path


def build_call_path(outer_frames):
    call_list = []
    for index, frame in enumerate(outer_frames):
        #eprint("outer_frame:", outer_frame)
        external_frame_file = frame.filename
        external_frame_file_name = basename(external_frame_file)
        external_frame_line_number = frame.lineno
        external_frame_file_dir = basename(dirname(external_frame_file))
        external_frame_file_name_and_dir = external_frame_file_dir + '/' + external_frame_file_name
        #eprint(index, external_frame_file, external_frame_file_dir, external_frame_file_name, external_frame_file_name_and_dir, external_frame_line_number, frame.function)
        call_list.append({'path': external_frame_file_name_and_dir, 'line': external_frame_line_number, 'function': frame.function})
        #if external_frame_file_name != call_frame_file_name:
        #    break
    call_path = []
    call_list_reversed = list(reversed(call_list))
    previous_item = call_list_reversed[0]
    root_program = basename(previous_item['path'])
    call_path.append((root_program + ':' + str(previous_item['line'])))
    call_list_length = len(call_list_reversed)
    click_section = False
    retry_on_exception_section = False
    asserttool_section = False
    item = None
    for index, item in enumerate(call_list_reversed):
        #eprint(index, item)
        if index > 0:
            if item['path'].startswith('click/'):
                if not click_section:
                    call_path.append(('<click>'))
                click_section = True
                continue
            if item['path'].startswith('retry_on_exception/'):
                if not retry_on_exception_section:
                    call_path.append(('<RTE>'))
                retry_on_exception_section = True
                continue
            if item['path'].startswith('asserttool/'):
                if not asserttool_section:
                    call_path.append(('<AT>'))
                asserttool_section = True
                continue

            click_section = False
            retry_on_exception_section = False
            asserttool_section = False
            if item['path'] != previous_item['path']:
                call_path.append(('→ '))
                path = reduce_path(item['path'], root_program=root_program)
                if index + 1 == call_list_length:
                    call_path.append((path))
                else:
                    call_path.append((path + ':' + str(item['line'])))
            else:
                if index + 1 < call_list_length:
                    call_path.append("," + (str(item['line'])))
            previous_item = item

    call_path.append(('＠ '))
    function = item['function']
    if function != '<module>':
        function = '%s():%s' % (function, str(item['line']))
    call_path.append((function))

    #eprint(call_list)

    #eprint(" ")
    #for index, item in enumerate(call_path):
    #    eprint(index, item)

    call_path_str = ''.join([item for item in call_path])
    #eprint(call_path_str)
    return call_path_str

def get_context(call_frame, call_node):
    #line_number = call_node.lineno
    try:
        frame_info = inspect.getframeinfo(call_frame)
    except IndexError as e:
        eprint("e:", e)
        eprint("call_frame:", call_frame)
        raise e
    #parent_function = frame_info.function
    #call_frame_file = frame_info.filename
    #call_frame_file_name = basename(call_frame_file)
    #eprint("file_name:", file_name)
    #caller = sys._getframe(1).f_code.co_name
    #caller = call_frame.f_code.co_name
    #eprint(call_frame)
    #eprint(dir(call_frame))
    outer_frames = inspect.getouterframes(call_frame)
    #eprint("outer_frames:", outer_frames)
    #first_frame = outer_frames[::-1][0]
    #print("type(first_frame)", type(first_frame))
    #first_frame_file = first_frame.filename
    #first_frame_file_name = basename(first_frame_file)
    #first_frame_line_number = first_frame.lineno

    #second_frame = outer_frames[::-1][1]  # named wrong, [1] is the frame before parent_function
    ##print("type(second_frame)", type(second_frame))
    #second_frame_file = second_frame.filename
    #second_frame_file_name = basename(second_frame_file)
    #second_frame_file_dir = basename(dirname(second_frame_file))
    #second_frame_file_name_and_dir = second_frame_file_dir + '/' + second_frame_file_name
    #second_frame_line_number = second_frame.lineno
    call_path_string = build_call_path(outer_frames)
    #for index, outer_frame in enumerate(outer_frames):
    #    #eprint("outer_frame:", outer_frame)
    #    external_frame_file = outer_frame.filename
    #    external_frame_file_name = basename(external_frame_file)
    #    external_frame_line_number = outer_frame.lineno
    #    eprint(index, external_frame_file, external_frame_file_name, external_frame_line_number, outer_frame.function)
    #    #if external_frame_file_name != call_frame_file_name:
    #    #    break
    #return \
    #    first_frame_file_name, first_frame_line_number, second_frame_file_name_and_dir, second_frame_line_number, call_frame_file_name, line_number, parent_function
    return call_path_string


def format_context(call_frame, call_node):
    #caller_file_name, caller_line_number, second_frame_file_name, second_frame_line_number, file_name, line_number, parent_function = get_context(call_frame, call_node)
    #call_path_string, parent_function = get_context(call_frame, call_node)
    call_path_string = get_context(call_frame, call_node)

    #if parent_function != '<module>':
    #    parent_function = '%s()' % parent_function

    timestamp = str("%.3f" % time.time())
    #if caller_file_name != file_name:
    #    context = '%s %s %s:%s→%s:%s→ %s:%s＠ %s' % (timestamp, os.getpid(), caller_file_name, caller_line_number, second_frame_file_name, second_frame_line_number, file_name, line_number, parent_function)
    #else:
    #    context = '%s %s %s:%s＠ %s' % (timestamp, os.getpid(), file_name, line_number, parent_function)
    #if caller_file_name != file_name:
    context = '%s %s %s' % (timestamp, os.getpid(), call_path_string)
    #else:
    #    context = '%s %s %s:%s＠ %s' % (timestamp, os.getpid(), file_name, line_number, parent_function)
    #eprint("context:", context)
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
        #print(colored)
        eprint(colored)


DEFAULT_PREFIX = 'ic| '
#DEFAULT_CONTEXT_DELIMITER = '- '
DEFAULT_CONTEXT_DELIMITER = '→ '
##DEFAULT_ARG_TO_STRING_FUNCTION = pprint.pformat
#DEFAULT_ARG_TO_STRING_FUNCTION = repr


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


def call_or_value(obj):
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


class IceCreamDebugger:
    _pairDelimiter = ', '  # Used by the tests in tests/.
    contextDelimiter = DEFAULT_CONTEXT_DELIMITER

    def __init__(self, prefix=DEFAULT_PREFIX,
                 arg_to_string_function=repr, includeContext=True):
        self.prefix = prefix
        self.includeContext = includeContext
        self.arg_to_string_function = arg_to_string_function

    def __call__(self, *args):
        call_frame = inspect.currentframe().f_back
        try:
            out = self._format(call_frame, *args)
        except NoSourceAvailableError as err:
            prefix = call_or_value(self.prefix)
            out = prefix + 'Error: ' + err.infoMessage
        #print(out)
        colorized_stderr_print(out)

        if not args:            # E.g. ic().
            passthrough = None
        elif len(args) == 1:    # E.g. ic(1).
            passthrough = args[0]
        else:                   # E.g. ic(1, 2, 3).
            passthrough = args

        return passthrough

    def format(self, *args):
        call_frame = inspect.currentframe().f_back
        out = self._format(call_frame, *args)
        #eprint(out)
        return out

    def _format(self, call_frame, *args):
        #eprint("args:", args)
        prefix = call_or_value(self.prefix)
        #eprint("prefix:", prefix)  # ic|

        call_node = Source.executing(call_frame).node
        if call_node is None:
            raise NoSourceAvailableError()

        context = ''
        if self.includeContext:
            context = format_context(call_frame, call_node)
            #eprint("context:", context)  # file.py:13 in <module>

        if not args:
            time = format_time()
            out = prefix + context + time
        else:
            #if not self.includeContext:
            #    context = ''
            out = self._format_args(call_frame, call_node, prefix, context, args)

        #eprint(out)
        return out

    def _format_args(self, call_frame, call_node, prefix, context, args):
        source = Source.for_frame(call_frame)
        sanitized_arg_strings = [
            source.get_text_with_indentation(arg)
            for arg in call_node.args]

        pairs = list(zip(sanitized_arg_strings, args))
        #eprint("pairs:", pairs)
        out = self._construct_argument_output(prefix, context, pairs)
        #print(out)
        return out

    def _construct_argument_output(self, prefix, context, pairs):
        def argPrefix(arg):
            return '%s: ' % arg

        pairs = [(arg, self.arg_to_string_function(val)) for arg, val in pairs]
        #eprint("pairs:", pairs)

        allArgsOnOneLine = self._pairDelimiter.join(
            val if arg == val else argPrefix(arg) + val for arg, val in pairs)

        contextDelimiter = self.contextDelimiter if context else ''
        #print(allArgsOnOneLine)
        lines = [prefix + context + contextDelimiter + allArgsOnOneLine]
        #print(lines)

        return '\n'.join(lines)

    def configureOutput(self,
                        prefix=_absent,
                        arg_to_string_function=_absent,
                        includeContext=_absent):
        if prefix is not _absent:
            self.prefix = prefix

        if arg_to_string_function is not _absent:
            self.arg_to_string_function = arg_to_string_function

        if includeContext is not _absent:
            self.includeContext = includeContext


ic = IceCreamDebugger()
icr = IceCreamDebugger(includeContext=False)
