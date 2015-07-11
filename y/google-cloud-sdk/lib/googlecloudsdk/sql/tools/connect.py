# Copyright 2013 Google Inc. All Rights Reserved.

"""Connects to a Cloud SQL instance."""

import datetime
import protorpc.util
from googlecloudapis.apitools.base import py as apitools_base
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import remote_completion
from googlecloudsdk.core.util import execution_utils
from googlecloudsdk.core.util import files
from googlecloudsdk.core.util import retry
from googlecloudsdk.sql import util


def _WhitelistClientIP(instance_ref, sql_client, sql_messages, resources):
  """Add CLIENT_IP to the authorized networks list.

  Makes an API call to add CLIENT_IP to the authorized networks list.
  The server knows to interpret the string CLIENT_IP as the address with which
  the client reaches the server. This IP will be whitelisted for 1 minute.

  Args:
    instance_ref: resources.Resource, The instance we're connecting to.
    sql_client: apitools.BaseApiClient, A working client for the sql version
        to be used.
    sql_messages: module, The module that defines the messages for the sql
        version to be used.
    resources: resources.Registry, The registry that can create resource refs
        for the sql version to be used.

  Returns:
    string, The name of the authorized network rule. Callers can use this name
    to find out the IP the client reached the server with.
  """
  datetime_now = datetime.datetime.now(
      protorpc.util.TimeZoneOffset(datetime.timedelta(0)))

  acl_name = 'sql connect at time {0}'.format(datetime_now)
  user_acl = sql_messages.AclEntry(
      name=acl_name,
      expirationTime=datetime_now + datetime.timedelta(minutes=1),
      value='CLIENT_IP')

  try:
    original = sql_client.instances.Get(instance_ref.Request())
  except apitools_base.HttpError as error:
    raise exceptions.HttpException(util.GetErrorMessage(error))

  original.settings.ipConfiguration.authorizedNetworks.append(user_acl)
  patch_request = sql_messages.SqlInstancesPatchRequest(
      databaseInstance=original,
      project=instance_ref.project,
      instance=instance_ref.instance)
  result = sql_client.instances.Patch(patch_request)

  operation_ref = resources.Create(
      'sql.operations',
      operation=result.name,
      project=instance_ref.project,
      instance=instance_ref.instance)
  message = 'Whitelisting your IP for incoming connection for 1 minute'

  # Due to eventual consistency, the server might not know of the operation we
  # just issued above, and throw an exception.
  # This retry is not a pooling of the operation itself, but a retry until
  # the server knows the operation actually exists.
  try:
    retryer = retry.Retryer(max_retrials=2, exponential_sleep_multiplier=2)
    retryer.RetryOnException(
        util.WaitForOperationV1Beta4,
        [sql_client, operation_ref, message],
        sleep_ms=500)
  except retry.RetryException:
    raise exceptions.ToolException('Could not whitelist client IP.')

  return acl_name


def _GetClientIP(instance_ref, sql_client, acl_name):
  instance_info = sql_client.instances.Get(instance_ref.Request())
  networks = instance_info.settings.ipConfiguration.authorizedNetworks
  client_ip = None
  for network in networks:
    if network.name == acl_name:
      client_ip = network.value
      break
  return instance_info, client_ip


@base.ReleaseTracks(base.ReleaseTrack.BETA)
class Connect(base.Command):
  """Connects to a Cloud SQL instance."""

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use it to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    instance = parser.add_argument(
        'instance',
        help='Cloud SQL instance ID.')
    cli = Connect.GetCLIGenerator()
    instance.completer = (remote_completion.RemoteCompletion.
                          GetCompleterForResource('sql.instances', cli))

    parser.add_argument(
        '--user', '-u',
        required=False,
        help='Cloud SQL instance user to connect as.')

  @util.ReraiseHttpException
  def Run(self, args):
    """Connects to a Cloud SQL instance.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      A dict object representing the instance resource if fetching the instance
      was successful.
    Raises:
      HttpException: A http error response was received while executing api
          request.
      ToolException: An error other than http error occured while executing the
          command.
    """
    sql_client = self.context['sql_client']
    sql_messages = self.context['sql_messages']
    resources = self.context['registry']

    # Do the mysql executable check first. This way we can return an error
    # faster and not wait for whitelisting IP and other operations.
    mysql_executable = files.FindExecutableOnPath('mysql')
    if not mysql_executable:
      raise exceptions.ToolException(
          'Mysql client not found. Please install a mysql client and make sure '
          'it is in PATH to be able to connect to the database instance.')

    util.ValidateInstanceName(args.instance)
    instance_ref = resources.Parse(args.instance, collection='sql.instances')

    acl_name = _WhitelistClientIP(instance_ref, sql_client, sql_messages,
                                  resources)

    # Get the client IP that the server sees. Sadly we can only do this by
    # checking the name of the authorized network rule.
    retryer = retry.Retryer(max_retrials=2, exponential_sleep_multiplier=2)
    try:
      instance_info, client_ip = retryer.RetryOnResult(
          _GetClientIP,
          [instance_ref, sql_client, acl_name],
          should_retry_if=None,
          sleep_ms=500)
    except retry.RetryException:
      raise exceptions.ToolException('Could not whitelist client IP.')

    # Check the version of IP and decide if we need to add ipv4 support.
    ip_type = util.GetIpVersion(client_ip)
    if ip_type == 4:
      if instance_info.settings.ipConfiguration.ipv4Enabled:
        ip_address = instance_info.ipAddresses[0].ipAddress
      else:
        # TODO(user): ask user if we should enable ipv4 addressing
        message = ('It seems your client does not have ipv6 connectivity and '
                   'the database instance does not have an ipv4 address. '
                   'Please request an ipv4 address for this database instance')
        raise exceptions.ToolException(message)
    elif ip_type == 6:
      ip_address = instance_info.ipv6Address

    # We have everything we need, time to party!
    mysql_args = [mysql_executable, '-h', ip_address]
    if args.user:
      mysql_args.append('-u')
      mysql_args.append(args.user)
    mysql_args.append('-p')
    execution_utils.Exec(mysql_args)
