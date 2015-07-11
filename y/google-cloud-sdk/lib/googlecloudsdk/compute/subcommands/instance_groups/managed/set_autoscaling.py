# Copyright 2015 Google Inc. All Rights Reserved.
"""Command for creating & updating autoscalers."""
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.compute.lib import autoscaler_util
from googlecloudsdk.compute.lib import base_classes
from googlecloudsdk.compute.lib import utils


@base.Hidden
class SetAutoscaling(base_classes.BaseAsyncMutator):
  """Set autoscaling parameters of a Managed Instance Group."""

  _method = None

  @property
  def service(self):
    return self.compute.autoscalers

  @property
  def resource_type(self):
    return 'autoscalers'

  @property
  def method(self):
    if self._method is None:
      raise exceptions.ToolException(
          'Internal error: attempted calling method before determining which '
          'method to call.')
    return self._method

  @staticmethod
  def Args(parser, resource=None, cli=None, command=None):
    autoscaler_util.AddAutoscalerArgs(parser)
    name = parser.add_argument(
        'name',
        metavar='NAME',
        help='Managed instance group which autoscaling parameters will be set.')
    if cli:
      name.completer = utils.GetCompleterForResource(
          resource, cli, command)
    utils.AddZoneFlag(
        parser, resource_type='resources', operation_type='update', cli=cli)

  def CreateRequests(self, args):
    autoscaler_util.ValidateAutoscalerArgs(args)

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
        zone=zone,
        project=self.project)
    autoscaler_name = getattr(autoscaler, 'name', None)
    as_ref = self.CreateZonalReference(autoscaler_name or args.name, zone)
    autoscaler_resource = autoscaler_util.BuildAutoscaler(
        args, self.messages, as_ref, igm_ref)

    if autoscaler_name is None:
      self._method = 'Insert'
      request = self.messages.ComputeAutoscalersInsertRequest(
          project=self.project)
      autoscaler_util.AdjustAutoscalerNameForCreation(autoscaler_resource)
      request.autoscaler = autoscaler_resource
    else:
      self._method = 'Update'
      request = self.messages.ComputeAutoscalersUpdateRequest(
          project=self.project)
      request.autoscaler = as_ref.Name()
      request.autoscalerResource = autoscaler_resource

    request.zone = as_ref.zone
    return (request,)


SetAutoscaling.detailed_help = {
    'brief': 'Insert or Update Google Compute Engine autoscalers',
    'DESCRIPTION': """\
        *{command}* sets autoscaling parameters of specified Managed Instance
        Group.
        """,
}
