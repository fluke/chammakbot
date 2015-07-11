# Copyright 2015 Google Inc. All Rights Reserved.

"""A library to load and validate test arguments from a YAML argument file.

  The optional, positional ARG_SPEC argument on the command line is used to
  specify an ARG_FILE:ARG_GROUP_NAME pair, where ARG_FILE is the path to the
  YAML-format argument file, and ARG_GROUP_NAME is the name of the arg group
  to load and parse.

  The basic format of a YAML argument file is:

  arg-group-1:
    arg1: value1
    arg2: value2

  arg-group-2:
    arg3: value3
    ...

  A special 'include: [<group-list>]' syntax allows composition/merging of
  arg-groups (see example below). Included groups can include: other groups as
  well, with unlimited nesting within one YAML file.

  Precedence of arguments:
    Args appearing on the command line will override any arg specified within
    an argument file.
    Args which are merged into a group using the 'include:' keyword have lower
    precedence than an arg already defined in that group.

  Example of a YAML argument file for use with 'gcloud test run ...' commands:

  memegen-robo-args:
    type: robo
    app: path/to/memegen.apk
    max-depth: 30
    max-steps: 2000
    include: [common-args, matrix-quick]
    timeout: 5m

  notepad-instr-args:
    type: instrumentation
    app: path/to/notepad.apk
    test: path/to/notepad-test.apk
    include: [common-args, matrix-large]

  common-args:
    results-bucket: gs://my-results-bucket
    timeout: 600

  matrix-quick:
    device-ids: [Nexus5, Nexus6]
    os-version-ids: 21
    locales: en
    orientation: landscape

  matrix-large:
    device-ids: [Nexus5, Nexus6, Nexus7, Nexus9, Nexus10]
    os-version-ids: [18, 19, 21]
    include: all-supported-locales

  all-supported-locales:
    locales: [de, en_US, en_GB, es, fr, it, ru, zh]
"""

import yaml

from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.test.lib import arg_validate


INCLUDE = 'include'


def GetArgsFromArgFile(argspec, all_test_args_set):
  """Loads a group of test args from an optional user-supplied arg file.

  Args:
    argspec: string containing an ARG_FILE:ARG_GROUP_NAME pair, where ARG_FILE
      is the path to a file containing groups of test arguments in yaml format,
      and ARG_GROUP_NAME is a yaml object name of a group of arg:value pairs.
    all_test_args_set: a set of strings for every gcloud-test argument. Used
      for validation.

  Returns:
    A dictionary created from the file which maps arg names to arg values.

  Raises:
    ToolException: If the argument name is not a gcloud test arg.
    InvalidArgException: If an argument has an invalid value or no value.
  """
  if argspec is None:
    return {}

  arg_file, group_name = _SplitArgFileAndGroup(argspec)
  try:
    all_arg_groups = _ReadArgGroupsFromFile(arg_file)
  except IOError as err:
    raise exceptions.BadFileException(
        'Error reading argument file [{f}]: {e}'.format(f=arg_file, e=err))

  args_from_file = {}
  _MergeArgGroupIntoArgs(args_from_file, group_name, all_arg_groups,
                         all_test_args_set)
  log.info('Args loaded from file: ' + str(args_from_file))
  return args_from_file


def _SplitArgFileAndGroup(file_and_group_str):
  """Parse and return the arg filename and arg group name."""
  index = file_and_group_str.rfind(':')
  if index < 0 or (index == 2 and file_and_group_str.startswith('gs://')):
    raise arg_validate.InvalidArgException(
        'arg-spec', 'Format must be ARG_FILE:ARG_GROUP_NAME')
  return file_and_group_str[:index], file_and_group_str[index+1:]


def _ReadArgGroupsFromFile(arg_file):
  """Collect all the arg groups defined in the yaml file into a dictionary."""
  # TODO(user): add support for reading arg files in GCS.
  # TODO(user): add support for reading from stdin.
  with open(arg_file, 'r') as data:
    yaml_generator = yaml.safe_load_all(data)
    all_groups = {}
    try:
      for d in yaml_generator:
        if d is None:
          log.warning('Ignoring empty yaml document.')
        elif isinstance(d, dict):
          all_groups.update(d)
        else:
          raise yaml.scanner.ScannerError(
              '[{0}] is not a valid argument group.'.format(str(d)))
    except yaml.scanner.ScannerError as error:
      raise exceptions.BadFileException(
          'Error parsing YAML file [{0}]: {1}'.format(arg_file, str(error)))
  return all_groups


def _MergeArgGroupIntoArgs(
    args_from_file, group_name, all_arg_groups, all_test_args_set):
  """Merge args from an arg group into the given args_from_file dictionary."""
  if group_name not in all_arg_groups:
    raise exceptions.BadFileException(
        'Could not find argument group [{g}] in argument file.'
        .format(g=group_name))

  arg_group = all_arg_groups[group_name]
  if not arg_group:
    log.warning('Argument group [{0}] is empty.'.format(group_name))
    return
  if '__already_included__' in arg_group:
    raise arg_validate.InvalidArgException(
        INCLUDE,
        'Detected cyclic reference to arg group [{g}]'.format(g=group_name))

  for arg_name in arg_group:
    arg = arg_validate.InternalArgNameFrom(arg_name)
    # Must process include: groups last in order to follow precedence rules.
    if arg == INCLUDE:
      continue

    if arg not in all_test_args_set:
      raise exceptions.ToolException(
          '[{0}] is not a valid argument name for: gcloud test run.'
          .format(arg_name))
    if arg in args_from_file:
      log.info(
          'Skipping include: of arg [{0}] because it already had value [{1}].'
          .format(arg_name, args_from_file[arg]))
    else:
      args_from_file[arg] = arg_validate.ValidateArgFromFile(
          arg, arg_group[arg_name])

  arg_group['__already_included__'] = True  # Prevent "include:" cycles

  if INCLUDE in arg_group:
    included_groups = arg_validate.ValidateStringList(INCLUDE,
                                                      arg_group[INCLUDE])
    for included_group in included_groups:
      _MergeArgGroupIntoArgs(
          args_from_file, included_group, all_arg_groups, all_test_args_set)
  return
