#!/usr/bin/env python3
"""Tests for fix_sarif_paths.py.

Run with:  python3 .github/scripts/test_fix_sarif_paths.py
"""
import copy
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fix_sarif_paths import (  # noqa: E402
    GOOD_SCHEMA_URL,
    collect_rules,
    fix_sarif,
    is_stub,
)

WORKSPACE = '/home/runner/work/AIT-Core/AIT-Core'

# A CodeQL report as github/codeql-action actually emits it: rules live under
# tool.extensions[], driver.rules is empty, URIs are relative with a symbolic
# %SRCROOT% uriBaseId, and results carry no explicit level.
RAW_CODEQL = {
    "$schema": ("https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/"
                "Schemata/sarif-schema-2.1.0.json"),
    "version": "2.1.0",
    "runs": [{
        "tool": {
            "driver": {"name": "CodeQL", "rules": []},
            "extensions": [{
                "name": "codeql/javascript-queries",
                "rules": [
                    {"id": "js/redos",
                     "shortDescription": {"text": "Inefficient regular expression"},
                     "fullDescription": {"text": "Exponential backtracking."},
                     "defaultConfiguration": {"level": "error"},
                     "properties": {"security-severity": "7.5"}},
                    {"id": "js/unused-local-variable",
                     "shortDescription": {"text": "Unused variable"},
                     "defaultConfiguration": {"level": "note"}},
                ],
            }],
        },
        "originalUriBaseIds": {"%SRCROOT%": {"uri": "file://" + WORKSPACE + "/"}},
        "artifacts": [{"location": {"uri": "src/app.js", "uriBaseId": "%SRCROOT%"}}],
        "results": [{
            "ruleId": "js/redos",
            "rule": {"id": "js/redos", "index": 0, "toolComponent": {"index": 0}},
            "message": {"text": "Vulnerable regex."},
            "locations": [{"physicalLocation": {
                "artifactLocation": {"uri": "src/app.js", "uriBaseId": "%SRCROOT%"},
                "region": {"startLine": 1}}}],
            "relatedLocations": [{"id": 1, "physicalLocation": {
                "artifactLocation": {"uri": "src/util.js", "uriBaseId": "%SRCROOT%"},
                "region": {"startLine": 9}}}],
            "codeFlows": [{"threadFlows": [{"locations": [{"location": {
                "physicalLocation": {
                    "artifactLocation": {"uri": "src/flow.js", "uriBaseId": "%SRCROOT%"},
                    "region": {"startLine": 3}}}}]}]}],
        }],
    }],
}

# The same report after nasa-scrub's translate_results: absolute URIs, an
# absolute uriBaseId, extensions deleted, driver.rules rebuilt as id-only
# stubs, driver.name set to the filename, and a flat "warning" level.
SCRUBBED = {
    "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
    "version": "2.1.0",
    "runs": [{
        "tool": {"driver": {
            "name": "javascript",
            "rules": [{"id": "js/redos", "shortDescription": {"text": "js/redos"}}],
        }},
        "artifacts": [{"location": {"uri": WORKSPACE + "/src/app.js"}}],
        "results": [{
            "ruleId": "js/redos",
            "level": "warning",
            "message": {"text": "Vulnerable regex."},
            "locations": [{"physicalLocation": {
                "artifactLocation": {"uri": WORKSPACE + "/src/app.js",
                                     "uriBaseId": WORKSPACE},
                "region": {"startLine": 1}}}],
        }],
    }],
}


def run_fix(document, reference=None, workspace=WORKSPACE):
    """Run fix_sarif on an in-memory document, returning the parsed output."""
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, 'in.sarif')
        dst = os.path.join(tmp, 'out.sarif')
        with open(src, 'w', encoding='utf-8') as handle:
            json.dump(document, handle)

        ref_path = None
        if reference is not None:
            ref_path = os.path.join(tmp, 'ref.sarif')
            with open(ref_path, 'w', encoding='utf-8') as handle:
                json.dump(reference, handle)

        code = fix_sarif(src, dst, workspace, ref_path)
        assert code == 0, f"fix_sarif returned {code}"
        with open(dst, encoding='utf-8') as handle:
            return json.load(handle)


def first_location(result):
    return result['locations'][0]['physicalLocation']['artifactLocation']


class TestScrubRepair(unittest.TestCase):
    """The wiki-prescribed pipeline: CodeQL -> scrub -> this script."""

    def setUp(self):
        self.out = run_fix(copy.deepcopy(SCRUBBED), reference=copy.deepcopy(RAW_CODEQL))
        self.run = self.out['runs'][0]

    def test_rule_metadata_restored_from_reference(self):
        rules = self.run['tool']['driver']['rules']
        self.assertEqual(len(rules), 2)
        redos = rules[0]
        self.assertEqual(redos['shortDescription']['text'],
                         'Inefficient regular expression')
        self.assertEqual(redos['defaultConfiguration']['level'], 'error')
        self.assertEqual(redos['properties']['security-severity'], '7.5')

    def test_tool_name_restored(self):
        # Drives SonarQube's external rule namespace: external_CodeQL:js/redos
        # rather than external_javascript:js/redos.
        self.assertEqual(self.run['tool']['driver']['name'], 'CodeQL')

    def test_scrub_flat_warning_is_overridden(self):
        # scrub flattens every finding to "warning"; the real rule is "error".
        self.assertEqual(self.run['results'][0]['level'], 'error')

    def test_paths_relativized(self):
        self.assertEqual(first_location(self.run['results'][0])['uri'], 'src/app.js')
        self.assertEqual(self.run['artifacts'][0]['location']['uri'], 'src/app.js')

    def test_absolute_uri_base_id_removed(self):
        self.assertNotIn('uriBaseId', first_location(self.run['results'][0]))

    def test_results_repointed_at_driver_rules(self):
        result = self.run['results'][0]
        self.assertEqual(result['ruleIndex'], 0)
        self.assertEqual(result['rule'], {'id': 'js/redos', 'index': 0})


class TestRawCodeQL(unittest.TestCase):
    """The no-scrub pipeline: CodeQL -> this script."""

    def setUp(self):
        self.out = run_fix(copy.deepcopy(RAW_CODEQL))
        self.run = self.out['runs'][0]

    def test_extension_rules_promoted_to_driver(self):
        rules = self.run['tool']['driver']['rules']
        self.assertEqual([r['id'] for r in rules],
                         ['js/redos', 'js/unused-local-variable'])
        self.assertEqual(rules[0]['properties']['security-severity'], '7.5')

    def test_level_derived_from_rule(self):
        self.assertEqual(self.run['results'][0]['level'], 'error')

    def test_symbolic_uri_base_id_preserved(self):
        # %SRCROOT% is valid SARIF and must survive; only filesystem paths go.
        self.assertEqual(first_location(self.run['results'][0])['uriBaseId'],
                         '%SRCROOT%')

    def test_relative_paths_untouched(self):
        self.assertEqual(first_location(self.run['results'][0])['uri'], 'src/app.js')

    def test_related_locations_and_code_flows_preserved(self):
        result = self.run['results'][0]
        self.assertEqual(len(result['relatedLocations']), 1)
        self.assertEqual(len(result['codeFlows']), 1)

    def test_broken_schema_url_corrected(self):
        self.assertEqual(self.out['$schema'], GOOD_SCHEMA_URL)


class TestPathHandling(unittest.TestCase):
    def test_absolute_paths_in_nested_locations_relativized(self):
        doc = copy.deepcopy(RAW_CODEQL)
        result = doc['runs'][0]['results'][0]
        result['relatedLocations'][0]['physicalLocation']['artifactLocation'] = {
            'uri': 'file://' + WORKSPACE + '/src/util.js'}
        flow = result['codeFlows'][0]['threadFlows'][0]['locations'][0]
        flow['location']['physicalLocation']['artifactLocation'] = {
            'uri': WORKSPACE + '/src/flow.js'}

        out = run_fix(doc)['runs'][0]['results'][0]
        self.assertEqual(
            out['relatedLocations'][0]['physicalLocation']['artifactLocation']['uri'],
            'src/util.js')
        self.assertEqual(
            out['codeFlows'][0]['threadFlows'][0]['locations'][0]['location']
               ['physicalLocation']['artifactLocation']['uri'],
            'src/flow.js')

    def test_trailing_slash_workspace_is_tolerated(self):
        out = run_fix(copy.deepcopy(SCRUBBED), reference=copy.deepcopy(RAW_CODEQL),
                      workspace=WORKSPACE + '/')
        self.assertEqual(first_location(out['runs'][0]['results'][0])['uri'],
                         'src/app.js')

    def test_paths_outside_workspace_left_alone(self):
        doc = copy.deepcopy(SCRUBBED)
        first_location(doc['runs'][0]['results'][0])['uri'] = '/usr/lib/node/thing.js'
        out = run_fix(doc, reference=copy.deepcopy(RAW_CODEQL))
        self.assertEqual(first_location(out['runs'][0]['results'][0])['uri'],
                         '/usr/lib/node/thing.js')


class TestAttributionHardening(unittest.TestCase):
    def test_misplaced_tool_rules_moved_to_driver(self):
        doc = copy.deepcopy(SCRUBBED)
        tool = doc['runs'][0]['tool']
        tool['driver'] = {'name': 'javascript'}
        tool['rules'] = [{'id': 'js/redos',
                          'shortDescription': {'text': 'Inefficient regex'},
                          'defaultConfiguration': {'level': 'error'}}]
        out = run_fix(doc)['runs'][0]['tool']
        self.assertNotIn('rules', out)
        self.assertEqual(out['driver']['rules'][0]['id'], 'js/redos')

    def test_missing_driver_name_defaults(self):
        doc = copy.deepcopy(SCRUBBED)
        del doc['runs'][0]['tool']['driver']['name']
        out = run_fix(doc)
        self.assertEqual(out['runs'][0]['tool']['driver']['name'], 'CodeQL')

    def test_rich_rules_not_clobbered_by_reference(self):
        # A report that was never degraded must be left alone.
        doc = copy.deepcopy(SCRUBBED)
        doc['runs'][0]['tool']['driver']['rules'] = [{
            'id': 'js/redos',
            'shortDescription': {'text': 'Real description'},
            'defaultConfiguration': {'level': 'note'}}]
        out = run_fix(doc, reference=copy.deepcopy(RAW_CODEQL))
        rules = out['runs'][0]['tool']['driver']['rules']
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0]['shortDescription']['text'], 'Real description')
        # And a genuine per-result level survives.
        self.assertEqual(out['runs'][0]['results'][0]['level'], 'warning')


class TestRobustness(unittest.TestCase):
    def test_missing_reference_file_does_not_fail_the_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, 'in.sarif')
            dst = os.path.join(tmp, 'out.sarif')
            with open(src, 'w', encoding='utf-8') as handle:
                json.dump(SCRUBBED, handle)
            code = fix_sarif(src, dst, WORKSPACE, os.path.join(tmp, 'nope.sarif'))
        self.assertEqual(code, 0)

    def test_malformed_input_reports_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, 'in.sarif')
            with open(src, 'w', encoding='utf-8') as handle:
                handle.write('{not json')
            code = fix_sarif(src, os.path.join(tmp, 'out.sarif'), WORKSPACE)
        self.assertEqual(code, 1)

    def test_empty_runs_is_a_no_op(self):
        out = run_fix({"version": "2.1.0", "runs": []})
        self.assertEqual(out['runs'], [])


class TestHelpers(unittest.TestCase):
    def test_is_stub_detects_scrub_output(self):
        self.assertTrue(is_stub({'id': 'js/redos',
                                 'shortDescription': {'text': 'js/redos'}}))

    def test_is_stub_rejects_real_rule(self):
        self.assertFalse(is_stub({'id': 'js/redos',
                                  'shortDescription': {'text': 'Inefficient regex'}}))
        self.assertFalse(is_stub({'id': 'js/redos',
                                  'defaultConfiguration': {'level': 'error'}}))

    def test_collect_rules_merges_driver_and_extensions(self):
        rules = collect_rules(RAW_CODEQL['runs'][0])
        self.assertEqual([r['id'] for r in rules],
                         ['js/redos', 'js/unused-local-variable'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
