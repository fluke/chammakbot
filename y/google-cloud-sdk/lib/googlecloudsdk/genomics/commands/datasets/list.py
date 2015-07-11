# Copyright 2015 Google Inc. All Rights Reserved.

"""datasets list command."""

from googlecloudapis.apitools.base import py as apitools_base
from googlecloudsdk.calliope import base
from googlecloudsdk.core.util import list_printer
from googlecloudsdk.genomics import lib
from googlecloudsdk.genomics.lib import genomics_util


class List(base.Command):
  """List Genomics datasets in a project.

  Prints a table with summary information on datasets in the project.
  """

  @staticmethod
  def Args(parser):
    """Args is called by calliope to gather arguments for this command.

    Args:
      parser: An argparse parser that you can use to add arguments that go
          on the command line after this command. Positional arguments are
          allowed.
    """
    parser.add_argument('--limit',
                        type=int,
                        help='The maximum number of results to list.')
    # TODO(user): when b/20336579 is resolved, this parameter goes away
    parser.add_argument('--project-number',
                        type=int,
                        help='The project number to list datasets for.',
                        required=True)

  @genomics_util.ReraiseHttpException
  def Run(self, args):
    """Run 'datasets list'.

    Args:
      args: argparse.Namespace, The arguments that this command was invoked
          with.

    Returns:
      The list of datasets for this project.

    Raises:
      HttpException: An http error response was received while executing api
          request.
    """
    genomics_util.ValidateLimitFlag(args.limit)

    apitools_client = self.context[lib.GENOMICS_APITOOLS_CLIENT_KEY]
    req_class = (self.context[lib.GENOMICS_MESSAGES_MODULE_KEY]
                 .GenomicsDatasetsListRequest)
    request = req_class(
        projectNumber=args.project_number)
    res = apitools_base.list_pager.YieldFromList(
        apitools_client.datasets,
        request,
        limit=args.limit,
        batch_size_attribute='pageSize',
        batch_size=None,  # Use server default.
        field='datasets')

    return res

  def Display(self, args, result):
    """Display prints information about what just happened to stdout.

    Args:
      args: The same as the args in Run.

      result: a list of Dataset objects.

    Raises:
      ValueError: if result is None or not a list
    """
    list_printer.PrintResourceList('genomics.datasets', result)
