# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Test manifest split."""

import manifest_split
import tempfile
import unittest
import xml.etree.ElementTree as ET
from hashlib import sha1


class ManifestSplitTest(unittest.TestCase):

  def test_read_config(self):
    with tempfile.NamedTemporaryFile('w+t') as test_config:
      test_config.write("""
        <config>
          <add_project name="add1" />
          <add_project name="add2" />
          <remove_project name="remove1" />
          <remove_project name="remove2" />
        </config>""")
      test_config.flush()
      remove_projects, add_projects = manifest_split.read_config(
          test_config.name)
      self.assertEqual(remove_projects, set(['remove1', 'remove2']))
      self.assertEqual(add_projects, set(['add1', 'add2']))

  def test_get_repo_projects(self):
    with tempfile.NamedTemporaryFile('w+t') as repo_list_file:
      repo_list_file.write("""
        system/project1 : platform/project1
        system/project2 : platform/project2""")
      repo_list_file.flush()
      repo_projects = manifest_split.get_repo_projects(repo_list_file.name)
      self.assertEqual(
          repo_projects, {
              'system/project1': 'platform/project1',
              'system/project2': 'platform/project2',
          })

  def test_get_module_info(self):
    with tempfile.NamedTemporaryFile('w+t') as module_info_file:
      module_info_file.write("""{
        "target1a": { "path": ["system/project1"] },
        "target1b": { "path": ["system/project1"] },
        "target2": { "path": ["out/project2"] },
        "target3": { "path": ["vendor/google/project3"] }
      }""")
      module_info_file.flush()
      repo_projects = {
          'system/project1': 'platform/project1',
          'vendor/google/project3': 'vendor/project3',
      }
      module_info = manifest_split.get_module_info(module_info_file.name,
                                                   repo_projects)
      self.assertEqual(
          module_info, {
              'platform/project1': set(['target1a', 'target1b']),
              'vendor/project3': set(['target3']),
          })

  def test_get_module_info_raises_on_unknown_module_path(self):
    with tempfile.NamedTemporaryFile('w+t') as module_info_file:
      module_info_file.write("""{
        "target1": { "path": ["system/unknown/project1"] }
      }""")
      module_info_file.flush()
      repo_projects = {}
      with self.assertRaises(ValueError):
        manifest_split.get_module_info(module_info_file.name, repo_projects)

  def test_scan_repo_projects(self):
    repo_projects = {
        'system/project1': 'platform/project1',
        'system/project2': 'platform/project2',
    }
    self.assertEqual(
        manifest_split.scan_repo_projects(repo_projects,
                                          'system/project1/path/to/file.h'),
        'system/project1')
    self.assertEqual(
        manifest_split.scan_repo_projects(
            repo_projects, 'system/project2/path/to/another_file.cc'),
        'system/project2')
    self.assertIsNone(
        manifest_split.scan_repo_projects(
            repo_projects, 'system/project3/path/to/unknown_file.h'))

  def test_get_input_projects(self):
    repo_projects = {
        'system/project1': 'platform/project1',
        'system/project2': 'platform/project2',
        'system/project4': 'platform/project4',
    }
    inputs = [
        'system/project1/path/to/file.h',
        'out/path/to/out/file.h',
        'system/project2/path/to/another_file.cc',
        'system/project3/path/to/unknown_file.h',
        '/tmp/absolute/path/file.java',
    ]
    self.assertEqual(
        manifest_split.get_input_projects(repo_projects, inputs),
        set(['platform/project1', 'platform/project2']))

  def test_update_manifest(self):
    manifest_contents = """
      <manifest>
        <project name="platform/project1" path="system/project1" />
        <project name="platform/project2" path="system/project2" />
        <project name="platform/project3" path="system/project3" />
      </manifest>"""
    input_projects = set(['platform/project1', 'platform/project3'])
    remove_projects = set(['platform/project3'])
    manifest = manifest_split.update_manifest(
        ET.ElementTree(ET.fromstring(manifest_contents)), input_projects,
        remove_projects)

    projects = manifest.getroot().findall('project')
    self.assertEqual(len(projects), 1)
    self.assertEqual(
        ET.tostring(projects[0]).strip().decode(),
        '<project name="platform/project1" path="system/project1" />')

  def test_create_manifest_sha1_element(self):
    manifest = ET.ElementTree(ET.fromstring('<manifest></manifest>'))
    manifest_sha1 = sha1(ET.tostring(manifest.getroot())).hexdigest()
    self.assertEqual(
        ET.tostring(
            manifest_split.create_manifest_sha1_element(
                manifest, 'test_manifest')).decode(),
        '<hash name="test_manifest" type="sha1" value="%s" />' % manifest_sha1)

  # TODO(b/147590297): Test the main split_manifest() function.


if __name__ == '__main__':
  unittest.main()
