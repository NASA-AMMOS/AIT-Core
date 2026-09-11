#!/usr/bin/env python3
"""
Repair a CodeQL SARIF report so SonarQube Cloud can import it correctly.

This runs *after* nasa-scrub's ``translate_results``, which the AMMOS scanning
guide prescribes:

    https://wiki.jpl.nasa.gov/display/AmmosArch/Code+Vulnerability+Scanning+Set+Up+for+AMMOS+Open+Source+Software

scrub is kept in the pipeline for compliance with that guide, but it is
lossy. Measured against a CodeQL-shaped report with nasa-scrub 3.0.2 (the
current release), ``translate_results``:

1. Rewrites workspace-relative URIs to **absolute** filesystem paths, and
   writes the absolute source root into ``uriBaseId`` -- where SARIF 2.1.0
   expects a symbolic key into ``originalUriBaseIds`` such as ``%SRCROOT%``.
   SonarQube cannot map issues to files with either, so findings collapse to
   project-level "Unable to resolve issue location" warnings.

2. Deletes ``runs[].tool.extensions`` and rebuilds ``runs[].tool.driver.rules``
   as id-only stubs::

       {"id": "js/redos", "shortDescription": {"text": "js/redos"}}

   CodeQL publishes its real query metadata -- descriptions, ``help``,
   ``defaultConfiguration.level`` and ``properties.security-severity`` -- under
   ``tool.extensions[].rules``, leaving ``driver.rules`` empty. SonarQube reads
   only ``driver.rules``. So scrub is the only thing populating the field
   SonarQube reads, but it populates it with metadata-free stubs, and every
   finding imports as MEDIUM regardless of real severity.

   This is not an ordering problem: scrub rebuilds ``driver.rules`` from
   scratch even when handed a report whose driver already carries rich rules,
   so it cannot be fixed by running this script first.

3. Sets ``driver.name`` to the input *filename* (e.g. ``javascript``) rather
   than ``CodeQL``, which is what SonarQube uses to namespace external rule
   keys (``external_javascript:js/redos`` instead of ``external_CodeQL:...``).

Passing ``--reference`` with the original, pre-scrub CodeQL SARIF lets this
script restore (2) and (3) from the authoritative source, and it always fixes
(1). The result is a report that satisfies the AMMOS guide's pipeline while
still importing with correct paths, rule names, descriptions and severities.

Known residual loss: scrub also discards ``relatedLocations`` and
``codeFlows``. Those are not restored here -- re-associating them would mean
matching results across two reports by heuristic, which is fragile. If the
security office is open to it, dropping the scrub step entirely (feeding this
script the raw CodeQL SARIF, where ``--reference`` is unnecessary because the
extensions are still present) preserves them.

Usage:
    fix_sarif_paths.py <input_sarif> <output_sarif> <workspace_path>
                       [--reference <original_codeql_sarif>]
"""
import json
import os
import sys

# The valid SARIF 2.1.0 schema URL. Some tools emit the old master-branch URL
# (which 404s); rewrite it. Mirrors nasa/scrub PR #121.
GOOD_SCHEMA_URL = (
    'https://raw.githubusercontent.com/oasis-tcs/sarif-spec/main/'
    'sarif-2.1/schema/sarif-schema-2.1.0.json'
)
BAD_SCHEMA_URLS = (
    'https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/'
    'Schemata/sarif-schema-2.1.0.json',
)


def collect_rules(run):
    """Gather every rule a run publishes, richest-first, de-duplicated by id.

    CodeQL puts its query metadata under ``tool.extensions[].rules`` (one tool
    component per query pack) and leaves ``tool.driver.rules`` empty, so both
    locations have to be consulted. Driver rules win on conflict.
    """
    tool = run.get('tool')
    if not isinstance(tool, dict):
        return []

    rules = []
    seen = set()
    driver = tool.get('driver')
    sources = []
    if isinstance(driver, dict):
        sources.append(driver.get('rules') or [])
    for extension in tool.get('extensions') or []:
        if isinstance(extension, dict):
            sources.append(extension.get('rules') or [])

    for source in sources:
        for rule in source:
            if not isinstance(rule, dict):
                continue
            rule_id = rule.get('id')
            if rule_id is None or rule_id in seen:
                continue
            # An id-only stub carries no metadata worth keeping; let a richer
            # definition of the same id from a later source replace it.
            seen.add(rule_id)
            rules.append(rule)
    return rules


def is_stub(rule):
    """True if a rule carries no metadata beyond its id.

    scrub emits ``{"id": X, "shortDescription": {"text": X}}`` -- a description
    identical to the id and nothing else. Treated as empty so a reference
    report can replace it.
    """
    if not isinstance(rule, dict):
        return True
    rule_id = rule.get('id')
    has_severity = bool(
        (rule.get('defaultConfiguration') or {}).get('level')
        or (rule.get('properties') or {}).get('security-severity')
    )
    short = (rule.get('shortDescription') or {}).get('text')
    has_text = bool(short and short != rule_id) or bool(rule.get('fullDescription'))
    return not (has_severity or has_text)


def apply_rules(run, rules, tool_name=None, force_level=False):
    """Install ``rules`` on the run's driver and re-point every result at them.

    Results are matched by ``ruleId``; ``ruleIndex`` and ``result.rule`` are
    rewritten to index into the driver's array, since any previous index
    referred to an extension that may no longer exist. ``result.level`` is made
    explicit from the rule's ``defaultConfiguration`` so SonarQube's importer
    cannot miss it and fall back to MEDIUM.

    ``force_level`` overwrites a level that is already present. It is set when
    restoring from a reference report, because scrub materializes a flat
    ``"warning"`` onto every result -- SARIF says an absent level is inherited
    from the rule's ``defaultConfiguration``, and scrub writes that inherited
    value out after having already discarded the real one. Left off, a genuine
    per-result level from the tool is preserved.
    """
    if not rules:
        return False

    tool = run.setdefault('tool', {})
    driver = tool.setdefault('driver', {})
    driver['rules'] = rules
    if tool_name:
        driver['name'] = tool_name

    index_of = {rule.get('id'): i for i, rule in enumerate(rules)}

    for result in run.get('results') or []:
        rule_id = result.get('ruleId') or (result.get('rule') or {}).get('id')
        index = index_of.get(rule_id)
        if index is None:
            continue
        result['ruleId'] = rule_id
        result['ruleIndex'] = index
        result['rule'] = {'id': rule_id, 'index': index}
        if force_level or 'level' not in result:
            level = (rules[index].get('defaultConfiguration') or {}).get('level')
            if level:
                result['level'] = level

    return True


def restore_rules(run, reference_run):
    """Replace scrub's stub rules with the real metadata from the pre-scrub report.

    No-op when the run already carries non-stub rules, so a report that was
    never degraded is left alone.
    """
    # Only the driver's own rules decide whether the report is already good --
    # SonarQube reads nothing else. Rules sitting in tool.extensions[] (where
    # CodeQL actually puts them) still need promoting onto the driver.
    driver_rules = ((run.get('tool') or {}).get('driver') or {}).get('rules') or []
    if driver_rules and not all(is_stub(rule) for rule in driver_rules):
        return False

    existing = collect_rules(run)
    if reference_run is None:
        # Nothing authoritative to restore from; fall back to whatever the run
        # itself publishes (this is the no-scrub path, where CodeQL's
        # extensions are still intact).
        return apply_rules(run, existing)

    rules = collect_rules(reference_run)
    if not rules:
        return apply_rules(run, existing)

    reference_name = (
        (reference_run.get('tool') or {}).get('driver') or {}
    ).get('name')
    return apply_rules(run, rules, tool_name=reference_name, force_level=True)


def harden_attribution(sarif):
    """Normalize the document so SonarQube can attribute imported issues.

    SonarQube reads the tool name from ``runs[].tool.driver.name`` (mandatory)
    and rule metadata from ``runs[].tool.driver.rules[]``. Anything under
    ``runs[].tool.rules`` is ignored on import.
    """
    modified = False

    if sarif.get('$schema') in BAD_SCHEMA_URLS:
        sarif['$schema'] = GOOD_SCHEMA_URL
        modified = True

    for run in sarif.get('runs') or []:
        tool = run.get('tool')
        if not isinstance(tool, dict):
            continue
        driver = tool.setdefault('driver', {})
        if not isinstance(driver, dict):
            continue

        # Move misplaced rules onto the driver, without clobbering richer ones.
        if 'rules' in tool:
            if not driver.get('rules'):
                driver['rules'] = tool['rules']
            del tool['rules']
            modified = True

        # SonarQube drops the whole report if driver.name is missing.
        if not driver.get('name'):
            driver['name'] = 'CodeQL'
            modified = True

    return modified


def strip_absolute_uri_base_id(artifact_loc):
    """Drop a ``uriBaseId`` holding a filesystem path rather than a symbolic name.

    SARIF 2.1.0 defines ``uriBaseId`` as a key into ``run.originalUriBaseIds``
    (e.g. ``%SRCROOT%``). scrub writes the absolute source root, which
    SonarQube may prepend to an already-relative ``uri``. Symbolic ids are left
    untouched.
    """
    base_id = artifact_loc.get('uriBaseId')
    if isinstance(base_id, str) and (base_id.startswith('/') or base_id.startswith('file://')):
        del artifact_loc['uriBaseId']
        return True
    return False


def relativize(artifact_loc, workspace_path):
    """Make a single artifactLocation's URI relative to the workspace root."""
    modified = False
    uri = artifact_loc.get('uri')
    if isinstance(uri, str):
        if uri.startswith('file://'):
            uri = uri[len('file://'):]
        if uri.startswith(workspace_path + '/'):
            uri = uri[len(workspace_path) + 1:]
        if uri != artifact_loc.get('uri'):
            artifact_loc['uri'] = uri
            modified = True
    if strip_absolute_uri_base_id(artifact_loc):
        modified = True
    return modified


def iter_artifact_locations(run):
    """Yield every artifactLocation in a run, including nested flow locations.

    scrub currently discards relatedLocations and codeFlows, but the raw
    CodeQL report carries both, so this also covers the no-scrub pipeline.
    """
    for artifact in run.get('artifacts') or []:
        location = artifact.get('location')
        if isinstance(location, dict):
            yield location

    def from_location(location):
        physical = (location or {}).get('physicalLocation') or {}
        artifact_loc = physical.get('artifactLocation')
        if isinstance(artifact_loc, dict):
            yield artifact_loc

    for result in run.get('results') or []:
        for key in ('locations', 'relatedLocations'):
            for location in result.get(key) or []:
                yield from from_location(location)
        for flow in result.get('codeFlows') or []:
            for thread_flow in flow.get('threadFlows') or []:
                for entry in thread_flow.get('locations') or []:
                    yield from from_location(entry.get('location'))


def fix_sarif(sarif_file, output_file, workspace_path, reference_file=None):
    """Repair paths and rule attribution, writing the result to ``output_file``."""
    try:
        with open(sarif_file, 'r', encoding='utf-8') as handle:
            sarif = json.load(handle)

        reference = None
        if reference_file:
            try:
                with open(reference_file, 'r', encoding='utf-8') as handle:
                    reference = json.load(handle)
            except (OSError, ValueError) as exc:
                print(
                    f"WARNING: could not read reference {reference_file}: {exc}; "
                    "continuing without rule restoration",
                    file=sys.stderr,
                )

        reference_runs = (reference or {}).get('runs') or []
        modified = False

        for index, run in enumerate(sarif.get('runs') or []):
            reference_run = None
            if index < len(reference_runs):
                reference_run = reference_runs[index]
            elif len(reference_runs) == 1:
                reference_run = reference_runs[0]

            if restore_rules(run, reference_run):
                modified = True

        if harden_attribution(sarif):
            modified = True

        workspace_path = workspace_path.rstrip('/')
        for run in sarif.get('runs') or []:
            for artifact_loc in iter_artifact_locations(run):
                if relativize(artifact_loc, workspace_path):
                    modified = True

        with open(output_file, 'w', encoding='utf-8') as handle:
            json.dump(sarif, handle, ensure_ascii=False, indent=2)

        name = os.path.basename(output_file)
        if modified:
            print(f"[ok] Normalized paths/attribution in {name}")
        else:
            print(f"[info] No changes needed for {name}")
        return 0

    except Exception as exc:  # noqa: BLE001 - surface any failure to the runner
        print(f"ERROR processing {sarif_file}: {exc}", file=sys.stderr)
        return 1


def main(argv):
    args = list(argv)
    reference_file = None
    if '--reference' in args:
        position = args.index('--reference')
        if position + 1 >= len(args):
            print("ERROR: --reference requires a file path", file=sys.stderr)
            return 2
        reference_file = args[position + 1]
        del args[position:position + 2]

    if len(args) != 3:
        print(
            "Usage: fix_sarif_paths.py <input_sarif> <output_sarif> "
            "<workspace_path> [--reference <original_codeql_sarif>]",
            file=sys.stderr,
        )
        return 2

    return fix_sarif(args[0], args[1], args[2], reference_file)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
