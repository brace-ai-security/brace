"""JUnit XML, for CI dashboards that show test results.

One test case per finding, failed; one per rule with no findings, passed; and one for the
scan's completeness, an error when the scan is incomplete (an incomplete scan never reports
clean, here as everywhere). Notes go to system-out. Every string from the scan passes through
output.xml_safe, so no file name, detail, note or rule text can make the XML ill-formed.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

from ..model import Report
from ..output import safe_path, xml_safe
from .common import ReportOptions, rules_by_id, shared_lines

SUITE = "open-agent-security"


class Junit:
    name = "junit"
    media = "text"

    def render(self, report: Report, opts: ReportOptions) -> str:
        meta = rules_by_id(report)
        suite = ET.Element("testsuite", name=SUITE)
        failures = errors = 0
        shared = shared_lines(report.findings)
        for f in report.findings:
            m, path = meta[f.rule], xml_safe(safe_path(f.file))
            name = f"{f.rule} {path}:{f.line}" + (f" {f.id[:8]}" if (f.rule, f.file, f.line) in shared else "")
            case = ET.SubElement(suite, "testcase", classname=xml_safe(f"{SUITE}.{f.rule}"), name=name, file=path,
                                 line=str(f.line))
            failure = ET.SubElement(case, "failure", type=f.severity, message=xml_safe(f"{m.title}: {f.detail}"))
            failure.text = xml_safe(f"Why: {m.why}\nFix: {m.fix}\n{m.help_uri}")
            failures += 1
        found = {f.rule for f in report.findings}
        for r in report.rules:
            if r.id not in found:
                ET.SubElement(suite, "testcase", classname=xml_safe(f"{SUITE}.{r.id}"), name=xml_safe(f"{r.id} {r.title}"))
        case = ET.SubElement(suite, "testcase", classname=f"{SUITE}.scan", name="the scan is complete")
        if report.verdict == "incomplete":
            ET.SubElement(case, "error", type="incomplete",
                          message="The scan is incomplete (see the notes), so it cannot say this folder is clean.")
            errors += 1
        if report.notes:
            ET.SubElement(suite, "system-out").text = xml_safe("\n".join(f"note: {n}" for n in report.notes))
        tests = len(report.findings) + len(report.rules) - len(found) + 1
        suite.attrib.update(tests=str(tests), failures=str(failures), errors=str(errors), skipped="0")
        if report.started:
            suite.set("timestamp", report.started.strftime("%Y-%m-%dT%H:%M:%S"))
        if report.started and report.finished:
            suite.set("time", str((report.finished - report.started).total_seconds()))
        root = ET.Element("testsuites", name=SUITE, tests=str(tests), failures=str(failures), errors=str(errors))
        root.append(suite)
        ET.indent(root)
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode") + "\n"
