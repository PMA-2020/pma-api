"""App management utilities"""
import os
import platform
import subprocess
from datetime import datetime
from typing import List, Dict, Union
from uuid import uuid4 as random_uuid

from flask_sqlalchemy import DefaultMeta
# noinspection PyProtectedMember
from sqlalchemy.ext.declarative.clsregistry import _ModuleMarker

from pma_api.error import PmaApiDbInteractionError, PmaApiException
from pma_api.config import ERROR_LOG_PATH, LOGS_DIR, REFERENCES, BINARY_DIR, \
    FILE_LIST_IGNORES


def log_process_stderr(stderr_obj, err_msg: str = None) -> str:
    """Log stderr output from process

    Side effects:
        - Makes directory (if doesn't exist)
        - Writes to logfile (if error message)

    Args:
        stderr_obj: Stderr object
        err_msg (str): Custom error message

    Returns:
        str: errors
    """
    err = ''
    err_base: str = \
        err_msg + '\n\nFor more information, search for error details by ' \
                  'id "{}" in logfile "{}".\n'
    log_msg = ''

    try:
        for line in iter(stderr_obj.readline, ''):
            try:
                log_msg += line.encode('utf-8')
            except TypeError:
                log_msg += str(line)
    except AttributeError:
        log_msg: str = stderr_obj

    if log_msg:
        uuid = str(random_uuid())
        log_msg_open: str = '<error id="{}" datetime="{}">' \
            .format(uuid, str(datetime.now()))
        log_msg_close: str = '</' + log_msg_open[1:]
        log_msg: str = '\n\n' + \
                       log_msg_open + '\n' + \
                       log_msg + '\n' + \
                       log_msg_close
        if not os.path.exists(LOGS_DIR):
            os.mkdir(LOGS_DIR)
        with open(ERROR_LOG_PATH, 'a') as log:
            log.writelines(log_msg)
        err: str = err_base.format(uuid, ERROR_LOG_PATH)

    return err


def run_proc_and_log_errs(cmd: List):
    """Run process and log errors, if any

    Args:
        cmd (list): Command to be executed to run process
    """
    proc = subprocess.Popen(cmd, stderr=subprocess.PIPE,
                            universal_newlines=True)

    if proc.stderr:
        log_process_stderr(proc.stderr)

    proc.stderr.close()
    proc.wait()


def run_proc_simple(cmd, shell: bool = False) -> Dict[str, str]:
    """Run a process

    Helper function to run a process, for boilerplate reduction.

    Args:
        cmd (str | list): Command to run
        shell (bool): Shell argument to pass to subprocess.Popen

    Returns:
        dict: {
            'stdout': Popen.stdout.read(),
            'stderr': Popen.stderr.read()
        }
    """
    cmd_line: List[str] = \
        cmd.split(' ') if isinstance(cmd, str) \
        else cmd

    proc = subprocess.Popen(
        cmd_line,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        shell=shell)

    outs: str = proc.stdout.read()
    errs: str = proc.stderr.read()

    proc.stderr.close()
    proc.stdout.close()
    proc.wait()

    output = {
        'stdout': outs,
        'stderr': errs}

    return output


def _get_bin_path_from_ref_config(
        bin_name: str, system: bool = False, project: bool = False) -> str:
    """Get binary from 'REFERENCES' dictionary in pma_api.config

    If 'project', gets the first binary discovered.

    TODO: Implement handling based on OS.
    TODO: Default for the latest version in binary dir.
    TODO: Allow for a 'version' arg to request a specific version.

    Args:
        bin_name (str): Name of binary
        system (bool): Get the path to system binary?
        project (bool): Get the path to project binary?

    Raises:
        PmaApiException: If both 'system' and 'project' are True or False.
        PmaApiException: If binary was not found in config.

    Returns:
        str: Path to binary if project, or callable binary name if system
    """
    binary_found: str = ''
    os_dirnames: tuple = ('MacOS', 'Windows', 'Linux')
    this_os: str = platform.system()
    this_os: str = 'MacOS' if this_os == 'Darwin' else this_os
    err = 'Error occurred while trying to run command. Must designate ' \
          'whether to use the designated system binary or project binary. ' \
          'Args used: ' + \
          '\nBinary: ' + bin_name + \
          '\nUse system binary?: ' + str(system) + \
          '\nUse project binary?: ' + str(project)

    if system == project:
        raise PmaApiException(err)

    try:
        binary_refs: {str: str} = REFERENCES['binaries'][bin_name]
    except KeyError:
        raise PmaApiException('Binary "{}" was not found in REFERENCES config.'
                              .format(bin_name))

    if system:
        found: str = binary_refs['system']
        return found

    current_path, branch_root = '', ''
    binary_dir_root: {str: str} = os.path.join(BINARY_DIR, bin_name)

    for (current_dir, dirs, files) in os.walk(binary_dir_root, topdown=True):
        current_path: str = os.path.join(current_path, current_dir) if \
            current_path else current_dir
        os_dirs_present: bool = any([x in os_dirnames for x in dirs])
        if os_dirs_present:
            this_os_dir_present: bool = any([x == this_os for x in dirs])
            if not this_os_dir_present:
                break

        # TODO: Need some logic here if there are multiple versions
        # branch_root: str = current_dir if not branch_root else branch_root

        binaries: List[str] = [x for x in files if x not in FILE_LIST_IGNORES]
        if binaries:
            first_bin_found: str = binaries[0]
            binary_found: str = os.path.join(current_path, first_bin_found)
            break

    return binary_found


def run_proc(cmd, shell: bool = False, raises: bool = True,
             prints: bool = False) -> Dict[str, str]:
    """Run a process

    Wrapper for run_proc_simple. Only adds exception handling.

    Args:
        cmd (str | list): Command to run
        shell (bool): Shell argument to pass to subprocess.Popen
        raises (bool): Raise exceptions?
        prints (bool): Print captured stderr and stdout? Prints both to stdout.

    Raises:
        PmaApiDbInteractionError: If output['stderr']

    Returns:
        dict: {
            'stdout': Popen.stdout.read(),
            'stderr': Popen.stderr.read()
        }
    """
    cmd_line: List[str] = \
        cmd.split(' ') if isinstance(cmd, str) \
        else cmd
    this_bin: str = cmd_line[0]

    # Maybe try project binary first?
    try:  # Try command passed literally
        output: {str: str} = run_proc_simple(cmd_line, shell)
    except FileNotFoundError:
        try:  # Try designated system binary
            system_binary: str = _get_bin_path_from_ref_config(
                bin_name=this_bin, system=True)
            cmd_line[0] = system_binary
            output: {str: str} = run_proc_simple(cmd_line, shell)
        except FileNotFoundError:  # Try designated project binary
            project_binary: str = _get_bin_path_from_ref_config(
                bin_name=this_bin, project=True)
            cmd_line[0] = project_binary
            output: {str: str} = run_proc_simple(cmd_line, shell)

    stdout: str = output['stdout']
    stderr: str = output['stderr']

    if stdout and prints:
        print(stdout)

    if stderr and raises:
        msg = '\n' + stderr + \
              'Offending command: ' + str(cmd)
        raise PmaApiDbInteractionError(msg)
    if stderr and prints:
        print(stderr)

    return output


def get_table_models() -> tuple:
    """Get list of all db tables

    Returns:
        tuple: All db tables
    """
    from pma_api.models import db

    # noinspection PyProtectedMember
    registered_classes: List[Union[DefaultMeta, _ModuleMarker]] = \
        [x for x in db.Model._decl_class_registry.values()]
    registered_models: List[DefaultMeta] = \
        [x for x in registered_classes if isinstance(x, DefaultMeta)]
    tables: List[DefaultMeta] = \
        [x for x in registered_models if hasattr(x, '__tablename__')]

    return tuple(tables)
