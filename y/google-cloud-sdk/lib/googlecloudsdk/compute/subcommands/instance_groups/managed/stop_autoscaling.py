# Copyright 2015 Google Inc. All Rights Reserved.
"""Command for deleting autoscalers."""
from googlecloudsdk.calliope import base
from googlecloudsdk.compute.lib import autoscaler_util
from googlecloudsdk.compute.lib import base_classes
from googlecloudsdk.compute.lib import utils


@base.Hidden
class StopAutoscaling(base_classes.BaseAsyncMutator):
  """Remove autoscaling, if any, from a Managed Instance Group."""

  @property
  def service(self):
    return self.compute.autoscalers

  @property
  def resource_type(self):
    return 'autoscalers'

  @property
  def method(self):
    return 'Delete'

  @staticmethod
  def Args(parser, resource=None, cli=None, command=None):
    name = parser.add_argument(
        'name',
        metavar='NAME',
        help='Managed instance group which will no longer be autoscaled.')
    if cli:
      name.completer = utils.GetCompleterForResource(
          resource, cli, command)
    utils.AddZoneFlag(
        parser, resource_type='resources', operation_type='delete', cli=cli)

  def CreateRequests(self, args):
    igm_ref = self.CreateZonalReference(
        args.name, args.zone, resource_type='instanceGroupManagers')
    # We need the zone name, which might have been passed after prompting.
    # In that case, we get it from the reference.
    zone = args.zone or igm_ref.zone

    autoscaler_util.AssertInstanceGroupManagerExists(
        igm_ref, self.project, self.messages, self.compute, self.http,
        self.batch_url)

    autoscaler = autoscaler_util.AutoscalerForMig(
        mig_name=args.name,
        autoscalers=autoscaler_util.AutoscalersForZone(
            zone=zone,
            project=self.project,
            compute=self.compute,
            http=self.http,
            batch_url=self.batch_url),
        project=self.project,
        zone=zone)
    if autoscaler is None:
      raise autoscaler_util.ResourceNotFoundException(
          'The Managed Instance Grup is not Autoscaled.')
    as_ref = self.CreateZonalReference(autoscaler.name, zone)
    request = self.messages.ComputeAutoscalersDeleteRequest(
        project=self.project)
    request.zone = zone
    request.autoscaler = as_ref.Name()
    return (request,)


StopAutoscaling.detailed_help = {
    'brief': 'Delete Google Compute Engine autoscalers',
    'DESCRIPTION': """\
        *{command}* stops autoscaling a Managed Instance Group. If the Managed
        Instance Group is not autoscaled it will not be modified and command
        will report an error.
        """,
}
