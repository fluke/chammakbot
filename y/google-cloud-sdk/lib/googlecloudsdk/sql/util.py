# Copyright 2013 Google Inc. All Rights Reserved.

"""Common utility functions for sql tool."""
import json
import sys
import time

from googlecloudapis.apitools.base import py as apitools_base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.util import retry


class OperationError(exceptions.ToolException):
  pass


def GetCertRefFromName(
    sql_client, sql_messages, resources, instance_ref, common_name):
  """Get a cert reference for a particular instance, given its common name.

  Args:
    sql_client: apitools.BaseApiClient, A working client for the sql version to
        be used.
    sql_messages: module, The module that defines the messages for the sql
        version to be used.
    resources: resources.Registry, The registry that can create resource refs
        for the sql version to be used.
    instance_ref: resources.Resource, The instance whos ssl cert is being
        fetched.
    common_name: str, The common name of the ssl cert to be fetched.

  Returns:
    resources.Resource, A ref for the ssl cert being fetched. Or None if it
    could not be found.
  """
  cert = GetCertFromName(sql_client, sql_messages, instance_ref, common_name)

  if not cert:
    return None

  return resources.Create(
      collection='sql.sslCerts',
      project=instance_ref.project,
      instance=instance_ref.instance,
      sha1Fingerprint=cert.sha1Fingerprint)


def GetCertFromName(
    sql_client, sql_messages, instance_ref, common_name):
  """Get a cert for a particular instance, given its common name.

  In versions of the SQL API up to at least v1beta3, the last parameter of the
  URL is the sha1fingerprint, which is not something writeable or readable by
  humans. Instead, the CLI will ask for the common name. To allow this, we first
  query all the ssl certs for the instance, and iterate through them to find the
  one with the correct common name.

  Args:
    sql_client: apitools.BaseApiClient, A working client for the sql version to
        be used.
    sql_messages: module, The module that defines the messages for the sql
        version to be used.
    instance_ref: resources.Resource, The instance whos ssl cert is being
        fetched.
    common_name: str, The common name of the ssl cert to be fetched.

  Returns:
    resources.Resource, A ref for the ssl cert being fetched. Or None if it
    could not be found.
  """
  certs = sql_client.sslCerts.List(
      sql_messages.SqlSslCertsListRequest(
          project=instance_ref.project,
          instance=instance_ref.instance))
  for cert in certs.items:
    if cert.commonName == common_name:
      return cert

  return None


def GetOperationStatus(sql_client, operation_ref, progress_tracker=None):
  """Helper function for getting the status of an operation.

  Args:
    sql_client: apitools.BaseApiClient, The client used to make requests.
    operation_ref: resources.Resource, A reference for the operation to poll.
    progress_tracker: console_io.ProgressTracker, A reference for the progress
        tracker to tick, in case this function is used in a Retryer.

  Returns:
    True if the operation succeeded without error.
    False if the operation is not yet done.

  Raises:
    OperationError: If the operation has an error code or is in UNKNOWN state.
  """

  if progress_tracker:
    progress_tracker.Tick()
  op = sql_client.operations.Get(operation_ref.Request())
  if op.error:
    raise OperationError(op.error[0].code)
  if op.state == 'UNKNOWN':
    raise OperationError(op.state)
  if op.state == 'DONE':
    return True
  return False


def WaitForOperation(sql_client, operation_ref, message):
  """Wait for a Cloud SQL operation to complete.

  No operation is done instantly. Wait for it to finish following this logic:
  First wait 1s, then query, then retry waiting exponentially more from 2s.
  We want to limit to 10s between retries to maintain some responsiveness.
  Finally, we want to limit the whole process to a conservative 120s. If we get
  to that point it means something is wrong and we can throw an exception.

  Args:
    sql_client: apitools.BaseApiClient, The client used to make requests.
    operation_ref: resources.Resource, A reference for the operation to poll.
    message: str, The string to print while polling.

  Returns:
    True if the operation succeeded without error.

  Raises:
    OperationError: If the operation has an error code, is in UNKNOWN state, or
        if the operation takes more than 120s.
  """

  with console_io.ProgressTracker(message, autotick=False) as pt:
    time.sleep(1)
    retryer = retry.Retryer(exponential_sleep_multiplier=2,
                            max_wait_ms=120000,
                            wait_ceiling_ms=10000)
    try:
      retryer.RetryOnResult(GetOperationStatus,
                            [sql_client, operation_ref],
                            {'progress_tracker': pt},
                            should_retry_if=False,
                            sleep_ms=2000)
    except retry.WaitException:
      raise OperationError(
          'Operation {0} is taking too long'.format(operation_ref))


def GetOperationStatusV1Beta4(sql_client, operation_ref, progress_tracker=None):
  """Helper function for getting the status of an operation.

  Args:
    sql_client: apitools.BaseApiClient, The client used to make requests.
    operation_ref: resources.Resource, A reference for the operation to poll.
    progress_tracker: console_io.ProgressTracker, A reference for the progress
        tracker to tick, in case this function is used in a Retryer.

  Returns:
    True if the operation succeeded without error.
    False if the operation is not yet done.

  Raises:
    OperationError: If the operation has an error code or is in UNKNOWN state.
  """

  if progress_tracker:
    progress_tracker.Tick()
  op = sql_client.operations.Get(operation_ref.Request())
  if op.error:
    raise OperationError(op.error[0].code)
  if op.status == 'UNKNOWN':
    raise OperationError(op.status)
  if op.status == 'DONE':
    return True
  return False


def WaitForOperationV1Beta4(sql_client, operation_ref, message):
  """Wait for a Cloud SQL operation to complete.

  No operation is done instantly. Wait for it to finish following this logic:
  First wait 1s, then query, then retry waiting exponentially more from 2s.
  We want to limit to 10s between retries to maintain some responsiveness.
  Finally, we want to limit the whole process to a conservative 120s. If we get
  to that point it means something is wrong and we can throw an exception.

  Args:
    sql_client: apitools.BaseApiClient, The client used to make requests.
    operation_ref: resources.Resource, A reference for the operation to poll.
    message: str, The string to print while polling.

  Returns:
    True if the operation succeeded without error.

  Raises:
    OperationError: If the operation has an error code, is in UNKNOWN state, or
        if the operation takes more than 120s.
  """

  with console_io.ProgressTracker(message, autotick=False) as pt:
    time.sleep(1)
    retryer = retry.Retryer(exponential_sleep_multiplier=2,
                            max_wait_ms=120000,
                            wait_ceiling_ms=10000)
    try:
      retryer.RetryOnResult(GetOperationStatusV1Beta4,
                            [sql_client, operation_ref],
                            {'progress_tracker': pt},
                            should_retry_if=False,
                            sleep_ms=2000)
    except retry.WaitException:
      raise OperationError(
          'Operation {0} is taking too long'.format(operation_ref))


def GetErrorMessage(error):
  error_obj = json.loads(error.content).get('error', {})
  errors = error_obj.get('errors', [])
  debug_info = errors[0].get('debugInfo', '') if len(errors) else ''
  return (error_obj.get('message', '') +
          ('\n' + debug_info if debug_info is not '' else ''))


def ReraiseHttpException(foo):
  def Func(*args, **kwargs):
    try:
      return foo(*args, **kwargs)
    except apitools_base.HttpError as error:
      msg = GetErrorMessage(error)
      unused_type, unused_value, traceback = sys.exc_info()
      raise exceptions.HttpException, msg, traceback
  return Func


def _ConstructSettingsFromArgs(sql_messages, args):
  """Constructs instance settings from the command line arguments.

  Args:
    sql_messages: module, The messages module that should be used.
    args: argparse.Namespace, The arguments that this command was invoked
        with.

  Returns:
    A settings object representing the instance settings.

  Raises:
    ToolException: An error other than http error occured while executing the
        command.
  """
  settings = sql_messages.Settings(
      tier=args.tier,
      pricingPlan=args.pricing_plan,
      replicationType=args.replication,
      activationPolicy=args.activation_policy)

  # these args are only present for the patch command
  no_assign_ip = getattr(args, 'no_assign_ip', False)
  no_require_ssl = getattr(args, 'no_require_ssl', False)
  clear_authorized_networks = getattr(args, 'clear_authorized_networks', False)
  clear_gae_apps = getattr(args, 'clear_gae_apps', False)

  if args.authorized_gae_apps:
    settings.authorizedGaeApplications = args.authorized_gae_apps
  elif clear_gae_apps:
    settings.authorizedGaeApplications = []

  if any([args.assign_ip, args.require_ssl, args.authorized_networks,
          no_assign_ip, no_require_ssl, clear_authorized_networks]):
    settings.ipConfiguration = sql_messages.IpConfiguration()
    if args.assign_ip:
      settings.ipConfiguration.enabled = True
    elif no_assign_ip:
      settings.ipConfiguration.enabled = False

    if args.authorized_networks:
      settings.ipConfiguration.authorizedNetworks = args.authorized_networks
    if clear_authorized_networks:
      # For patch requests, this field needs to be labeled explicitly cleared.
      settings.ipConfiguration.authorizedNetworks = []

    if args.require_ssl:
      settings.ipConfiguration.requireSsl = True
    if no_require_ssl:
      settings.ipConfiguration.requireSsl = False

  if any([args.follow_gae_app, args.gce_zone]):
    settings.locationPreference = sql_messages.LocationPreference(
        followGaeApplication=args.follow_gae_app,
        zone=args.gce_zone)

  enable_database_replication = getattr(
      args, 'enable_database_replication', False)
  no_enable_database_replication = getattr(
      args, 'no_enable_database_replication', False)
  if enable_database_replication:
    settings.databaseReplicationEnabled = True
  if no_enable_database_replication:
    settings.databaseReplicationEnabled = False

  return settings


def _SetDatabaseFlags(sql_messages, settings, args):
  if args.database_flags:
    settings.databaseFlags = []
    for (name, value) in args.database_flags.items():
      settings.databaseFlags.append(sql_messages.DatabaseFlags(
          name=name,
          value=value))
  elif getattr(args, 'clear_database_flags', False):
    settings.databaseFlags = []


def _SetBackupConfiguration(sql_messages, settings, args, original):
  """Sets the backup configuration for the instance."""
  # these args are only present for the patch command
  no_backup = getattr(args, 'no_backup', False)
  no_enable_bin_log = getattr(args, 'no_enable_bin_log', False)

  if original and (
      any([args.backup_start_time, args.enable_bin_log,
           no_backup, no_enable_bin_log])):
    if original.settings.backupConfiguration:
      backup_config = original.settings.backupConfiguration[0]
    else:
      backup_config = sql_messages.BackupConfiguration(
          startTime='00:00',
          enabled=False),
  elif not any([args.backup_start_time, args.enable_bin_log,
                no_backup, no_enable_bin_log]):
    return

  if not original:
    backup_config = sql_messages.BackupConfiguration(
        startTime='00:00',
        enabled=False)

  if args.backup_start_time:
    backup_config.startTime = args.backup_start_time
    backup_config.enabled = True
  if no_backup:
    if args.backup_start_time or args.enable_bin_log:
      raise exceptions.ToolException(
          ('Argument --no-backup not allowed with'
           ' --backup-start-time or --enable_bin_log'))
    backup_config.enabled = False

  if args.enable_bin_log:
    backup_config.binaryLogEnabled = True
  if no_enable_bin_log:
    backup_config.binaryLogEnabled = False

  settings.backupConfiguration = [backup_config]


def ConstructInstanceFromArgs(sql_messages, args, original=None):
  """Construct a Cloud SQL instance from command line args.

  Args:
    sql_messages: module, The messages module that should be used.
    args: argparse.Namespace, The CLI arg namespace.
    original: sql_messages.DatabaseInstance, The original instance, if some of
        it might be used to fill fields in the new one.

  Returns:
    sql_messages.DatabaseInstance, The constructed (and possibly partial)
    database instance.

  Raises:
    ToolException: An error other than http error occured while executing the
        command.
  """
  settings = _ConstructSettingsFromArgs(sql_messages, args)
  _SetBackupConfiguration(sql_messages, settings, args, original)
  _SetDatabaseFlags(sql_messages, settings, args)


  # these flags are only present for the create command
  region = getattr(args, 'region', None)
  database_version = getattr(args, 'database_version', None)

  instance_resource = sql_messages.DatabaseInstance(
      region=region,
      databaseVersion=database_version,
      masterInstanceName=getattr(args, 'master_instance_name', None),
      settings=settings)

  return instance_resource


def ValidateInstanceName(instance_name):
  if ':' in instance_name:
    possible_project = instance_name[:instance_name.rindex(':')]
    possible_instance = instance_name[instance_name.rindex(':')+1:]
    raise exceptions.ToolException("""\
Instance names cannot contain the ':' character. If you meant to indicate the
project for [{instance}], use only '{instance}' for the argument, and either add
'--project {project}' to the command line or first run
  $ gcloud config set project {project}
""".format(project=possible_project, instance=possible_instance))


def GetIpVersion(ip_address):
  """Given an ip address, try to open a socket and determine IP version."""
  # pylint:disable=g-import-not-at-top, Import when needed for performance.
  import socket
  try:
    socket.inet_aton(ip_address)
    return 4
  except socket.error:
    pass

  try:
    socket.inet_pton(socket.AF_INET6, ip_address)
    return 6
  except socket.error:
    pass

  return 0
