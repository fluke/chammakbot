# Copyright 2015 Google Inc. All Rights Reserved.

"""Source apis layer."""

from googlecloudapis.source.v1 import source_v1_messages as messages
from googlecloudapis.source.v1.source_v1_client import SourceV1 as client


class Source(object):
  """Base class for source api wrappers."""
  _client = None
  _resource_parser = None

  @classmethod
  def SetApiEndpoint(cls, http, endpoint):
    cls._client = client(url=endpoint, get_credentials=False, http=http)

  @classmethod
  def SetResourceParser(cls, parser):
    cls._resource_parser = parser


class Project(Source):
  """Abstracts source project."""

  def __init__(self, project_id):
    self.id = project_id

  def GetRepoList(self):
    """Returns list of repos."""
    request = messages.SourceProjectsReposListRequest(projectId=self.id)
    return self._client.projects_repos.List(request).repos
