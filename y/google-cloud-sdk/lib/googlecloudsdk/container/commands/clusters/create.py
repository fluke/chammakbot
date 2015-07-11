# Copyright 2014 Google Inc. All Rights Reserved.

"""Create cluster command."""
import argparse
import random
import string

from googlecloudapis.apitools.base import py as apitools_base
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.compute.lib import constants
from googlecloudsdk.container.lib import api_adapter
from googlecloudsdk.container.lib import kubeconfig as kconfig
from googlecloudsdk.container.lib import util
from googlecloudsdk.core import log


def _Args(parser):
  """Register flags for this command.

  Args:
    parser: An argparse.ArgumentParser-like object. It is mocked out in order
        to capture some information, but behaves like an ArgumentParser.
  """
  parser.add_argument('name', help='The name of this cluster.')
  parser.add_argument(
      '--no-wait',
      dest='wait',
      action='store_false',
      help='Return after issuing create request without polling the operation'
      ' for completion.')
  parser.add_argument(
      '--num-nodes',
      type=int,
      help='The number of nodes in the cluster.',
      default=3)
  parser.add_argument(
      '--machine-type', '-m',
      help='The type of machine to use for workers. Defaults to '
      'server-specified')
  parser.add_argument(
      '--network',
      help='The Compute Engine Network that the cluster will connect to. '
      'Google Container Engine will use this network when creating routes '
      'and firewalls for the clusters. Defaults to the \'default\' network.')
  parser.add_argument(
      '--container-ipv4-cidr',
      help='The IP addresses of the container pods in this cluster in CIDR '
      'notation (e.g. 10.0.0.0/14). Defaults to server-specified')
  parser.add_argument(
      '--password',
      help='The password to use for cluster auth. Defaults to a '
      'randomly-generated string.')
  parser.add_argument(
      '--scopes',
      type=arg_parsers.ArgList(min_length=1),
      metavar='SCOPE',
      action=arg_parsers.FloatingListValuesCatcher(),
      help="""\
Specifies scopes for the node instances. The project's default
service account is used. Examples:

  $ {{command}} example-cluster --scopes https://www.googleapis.com/auth/devstorage.read_only

  $ {{command}} example-cluster --scopes bigquery,storage-rw,compute-ro

Multiple SCOPEs can specified, separated by commas. The scopes
necessary for the cluster to function properly (compute-rw, storage-ro),
are always added, even if not explicitly specified.

SCOPE can be either the full URI of the scope or an alias.
Available aliases are:

Alias,URI
{aliases}
""".format(
    aliases='\n        '.join(
        ','.join(value) for value in
        sorted(constants.SCOPES.iteritems()))))


NO_CERTS_ERROR_MESSAGE = '''\
Failed to get certificate data for cluster; the kubernetes
api may not be accessible. You can retry later by running

$ gcloud alpha container get-credentials'''


@base.ReleaseTracks(base.ReleaseTrack.BETA)
class CreateBeta(base.Command):
  """Create a cluster for running containers."""

  @staticmethod
  def Args(parser):
    _Args(parser)
    parser.add_argument(
        '--username', '-u',
        help='The user name to use for cluster auth.',
        default='admin')
    parser.add_argument(
        '--cluster-version',
        help=argparse.SUPPRESS)
    parser.add_argument(
        '--no-enable-cloud-logging',
        help='Don\'t automatically send logs from the cluster to the '
        'Google Cloud Logging API.',
        dest='enable_cloud_logging',
        action='store_false')
    parser.set_defaults(enable_cloud_logging=True)
    parser.add_argument(
        '--no-enable-cloud-monitoring',
        help='Don\'t automatically send metrics from the cluster to the '
        'Google Cloud Monitoring API.',
        dest='enable_cloud_monitoring',
        action='store_false')
    parser.add_argument(
        '--disk-size',
        type=int,
        help='Size in GB for node VM boot disks. Defaults to 100GB')
    parser.set_defaults(enable_cloud_monitoring=True)

  def ParseCreateOptions(self, args):
    if not args.scopes:
      args.scopes = []
    return api_adapter.CreateClusterOptions(
        node_machine_type=args.machine_type,
        scopes=args.scopes,
        num_nodes=args.num_nodes,
        user=args.username,
        password=args.password,
        cluster_version=args.cluster_version,
        network=args.network,
        container_ipv4_cidr=args.container_ipv4_cidr,
        node_disk_size_gb=args.disk_size,
        enable_cloud_logging=args.enable_cloud_logging,
        enable_cloud_monitoring=args.enable_cloud_monitoring)

  @exceptions.RaiseToolExceptionInsteadOf(util.Error)
  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    Returns:
      Cluster message for the successfully created cluster.

    Raises:
      ToolException, if creation failed.
    """
    util.CheckKubectlInstalled()
    if not args.password:
      args.password = ''.join(random.SystemRandom().choice(
          string.ascii_letters + string.digits) for _ in range(16))

    adapter = self.context['api_adapter']

    if not args.scopes:
      args.scopes = []
    cluster_ref = adapter.ParseCluster(args.name)
    options = self.ParseCreateOptions(args)

    try:
      operation_ref = adapter.CreateCluster(cluster_ref, options)
      if not args.wait:
        return adapter.GetCluster(cluster_ref)

      adapter.WaitForOperation(
          operation_ref,
          'Creating cluster {0}'.format(cluster_ref.clusterId))
      cluster = adapter.GetCluster(cluster_ref)
    except apitools_base.HttpError as error:
      raise exceptions.HttpException(util.GetError(error))

    log.CreatedResource(cluster_ref)
    # Persist cluster config
    current_context = kconfig.Kubeconfig.Default().current_context
    c_config = util.ClusterConfig.Persist(
        cluster, cluster_ref.projectId, self.cli)
    if not c_config.has_certs:
      # Purge config so we retry the cert fetch on next kubectl command
      util.ClusterConfig.Purge(
          cluster.name, cluster.zone, cluster_ref.projectId)
      # reset current context
      if current_context:
        kubeconfig = kconfig.Kubeconfig.Default()
        kubeconfig.SetCurrentContext(current_context)
        kubeconfig.SaveToFile()
      raise exceptions.ToolException(NO_CERTS_ERROR_MESSAGE)
    return cluster

  def Display(self, args, result):
    """This method is called to print the result of the Run() method.

    Args:
      args: The arguments that command was run with.
      result: The value returned from the Run() method.
    """
    self.context['api_adapter'].PrintClusters([result])


@base.ReleaseTracks(base.ReleaseTrack.ALPHA)
class CreateAlpha(CreateBeta):
  """Create a cluster for running containers."""

  @staticmethod
  def Args(parser):
    _Args(parser)
    parser.add_argument(
        '--source-image',
        help='The source image to use for workers. Defaults to '
        'server-specified')
    parser.add_argument(
        '--user', '-u',
        help='The user name to use for cluster auth.',
        default='admin')
    parser.add_argument(
        '--cluster-api-version',
        help='The kubernetes release version to launch the cluster with. '
        'Defaults to server-specified.')
    parser.add_argument(
        '--no-enable-cloud-logging',
        help='Don\'t automatically send logs from the cluster to the '
        'Google Cloud Logging API.',
        dest='enable_cloud_logging',
        action='store_false')
    parser.set_defaults(enable_cloud_logging=True)

  def ParseCreateOptions(self, args):
    if not args.scopes:
      args.scopes = []
    return api_adapter.CreateClusterOptions(
        node_machine_type=args.machine_type,
        node_source_image=args.source_image,
        scopes=args.scopes,
        num_nodes=args.num_nodes,
        user=args.user,
        password=args.password,
        cluster_version=args.cluster_api_version,
        network=args.network,
        container_ipv4_cidr=args.container_ipv4_cidr,
        enable_cloud_logging=args.enable_cloud_logging)

