#!/usr/bin/env python3

import datetime
import inspect
import sys
from datetime import datetime
from os.path import basename
from os.path import dirname

from eprint import eprint

# old example:
# ic| 1731198725.327 1941 edittool:12<click>→ ''/edittool.py:862＠ edit_file():684→ "comitting": 'comitting'


def format_time():
    now = (
        datetime.utcnow()
    )  # ● The method "utcnow" in class "datetime" is deprecated    Use timezone-aware objects to represent datetimes in UTC; e.g. by calling .now(datetime.timezone.utc)
    formatted = now.strftime("%H:%M:%S.%f")[:-3]
    return " at %s" % formatted


def reduce_path(path, *, root_program):
    # eprint(f"{path=}", f"{root_program=}")
    python_version = sys.version_info
    python_version_folder = (
        "python" + str(python_version.major) + "." + str(python_version.minor)
    )
    path_basename = basename(path)
    path_dirname = dirname(path)
    if path_basename.split(".")[0] == path_dirname:
        # return root_program, "''/" + path_basename
        return root_program, "/" + path_basename

    if dirname(path) == python_version_folder:
        return (
            root_program,
            "{}.{}/".format(python_version.major, python_version.minor) + path_basename,
        )
    path = path.replace("attrs generated init", "attrs")
    if path.startswith("/"):
        path = path[1:]
    # eprint(path)
    # eprint(path.startswith(root_program + "/"))
    if path.startswith(root_program + "/"):
        # eprint("replacing")
        path = path.replace(root_program, "", 1)
        new_root = root_program
    else:
        new_root = path.split("/")[0]
    return new_root, path


def build_call_path(call_frame):
    outer_frames = inspect.getouterframes(call_frame)
    call_list = []
    for index, frame in enumerate(outer_frames):
        # eprint("outer_frame:", outer_frame)
        external_frame_file = frame.filename
        external_frame_file_name = basename(external_frame_file)
        external_frame_line_number = frame.lineno
        external_frame_file_dir = basename(dirname(external_frame_file))
        external_frame_file_name_and_dir = (
            external_frame_file_dir + "/" + external_frame_file_name
        )
        # eprint(index, external_frame_file, external_frame_file_dir, external_frame_file_name, external_frame_file_name_and_dir, external_frame_line_number, frame.function)
        call_list.append(
            {
                "path": external_frame_file_name_and_dir,
                "line": external_frame_line_number,
                "function": frame.function,
            }
        )
        # if external_frame_file_name != call_frame_file_name:
        #    break
    call_path = []
    call_list_reversed = list(reversed(call_list))
    previous_item = call_list_reversed[0]
    root_program = basename(previous_item["path"])
    call_path.append((root_program + ":" + str(previous_item["line"])))
    call_list_length = len(call_list_reversed)
    click_section = False
    retry_on_exception_section = False
    asserttool_section = False
    frozen_section = False
    frozen_section_external = False
    item = None
    for index, item in enumerate(call_list_reversed):
        # eprint(index, item)
        if index > 0:
            if item["path"].startswith("click/"):
                if not click_section:
                    call_path.append(("<click>"))
                click_section = True
                continue
            if item["path"].startswith("retry_on_exception/"):
                if not retry_on_exception_section:
                    call_path.append(("<RTOE>"))
                retry_on_exception_section = True
                continue
            if item["path"].startswith("asserttool/"):
                if not asserttool_section:
                    call_path.append(("<AT>"))
                asserttool_section = True
                continue
            if item["path"].startswith("/<frozen importlib._bootstrap>"):
                if not frozen_section:
                    call_path.append(("<ICE>"))
                frozen_section = True
                continue
            if item["path"].startswith("/<frozen importlib._bootstrap_external>"):
                if not frozen_section_external:
                    call_path.append(("<ICE>"))
                frozen_section_external = True
                continue
            # eprint(item["path"])

            click_section = False
            retry_on_exception_section = False
            asserttool_section = False
            frozen_section = False
            frozen_section_external = False
            if item["path"] != previous_item["path"]:
                call_path.append(("→ "))
                root_program, path = reduce_path(
                    item["path"], root_program=root_program
                )
                if index + 1 == call_list_length:
                    call_path.append((path))
                else:
                    call_path.append((path + ":" + str(item["line"])))
            else:
                if index + 1 < call_list_length:
                    call_path.append("," + (str(item["line"])))
            previous_item = item

    # call_path.append(("＠ "))
    call_path.append(("@ "))
    function = item["function"]
    if function != "<module>":
        function = "%s():%s" % (function, str(item["line"]))
    call_path.append((function))
    call_path_str = "".join([item for item in call_path])
    # eprint(call_path_str)
    return call_path_str
