# Copyright 2015 Google Inc. All Rights Reserved.

"""Common helper methods for Genomics commands."""

import json
import sys

from googlecloudapis.apitools.base import py as apitools_base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core.util import resource_printer
from googlecloudsdk.genomics import lib
from googlecloudsdk.genomics.lib.exceptions import GenomicsError


def ValidateLimitFlag(limit):
  """Validates a limit flag value.

  Args:
    limit: the limit flag value to sanitize.
  Raises:
    GenomicsError: if the provided limit flag value is negative
  """
  if limit is None:
    return

  if limit < 0:
    raise GenomicsError(
        '--limit must be a non-negative integer; received: {0}'
        .format(limit))


def PrettyPrint(resource, print_format='json'):
  """Prints the given resource."""
  resource_printer.Print(
      resources=[resource],
      print_format=print_format,
      out=log.out)


def GetError(error, verbose=False):
  """Returns a ready-to-print string representation from the http response.

  Args:
    error: A string representing the raw json of the Http error response.
    verbose: Whether or not to print verbose messages [default false]

  Returns:
    A ready-to-print string representation of the error.
  """
  data = json.loads(error.content)
  if verbose:
    PrettyPrint(data)
  code = data['error']['code']
  message = data['error']['message']
  return 'ResponseError: code={0}, message={1}'.format(code, message)


def GetErrorMessage(error):
  content_obj = json.loads(error.content)
  return content_obj.get('error', {}).get('message', '')


def ReraiseHttpException(foo):
  def Func(*args, **kwargs):
    try:
      return foo(*args, **kwargs)
    except apitools_base.HttpError as error:
      msg = GetErrorMessage(error)
      unused_type, unused_value, traceback = sys.exc_info()
      raise exceptions.HttpException, msg, traceback
  return Func


@ReraiseHttpException
def GetDataset(context, dataset_id):
  apitools_client = context[lib.GENOMICS_APITOOLS_CLIENT_KEY]
  genomics_messages = context[lib.GENOMICS_MESSAGES_MODULE_KEY]

  request = genomics_messages.GenomicsDatasetsGetRequest(
      datasetId=str(dataset_id),
  )

  return apitools_client.datasets.Get(request)

