# Copyright 2015 Google Inc. All Rights Reserved.

"""Resource execeptions."""

from googlecloudsdk.core import exceptions


class Error(exceptions.Error):
  """A base exception for all user recoverable resource errors."""
  pass


class ExpressionSyntaxError(Error):
  """An exception for user recoverable resource expression syntax errors."""
  pass
