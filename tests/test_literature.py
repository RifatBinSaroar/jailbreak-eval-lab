"""Safe synthetic fixtures: no downloaded papers, network or executable payloads."""

import contextlib
import copy
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from jailbreak_eval.literature.cli import main
from jailbreak_eval.literature.core import export_web, ingest, schema, validate_registry
from jailbreak_eval.literature.inputs import InputError, read_rows

MATRIX_HEADERS = ["Paper", "Year", "Venue", "Catagory", "Attack type", "white/black box",
                  "Main idea", "Models tested", "Benchmark", "Evaluation metric", "Main Result",
                  "Limitation", "Future work", "Code/data", "My understnding", "Questions",
                  "how the request is transforemed", "SoK relevance", "New-method relevance"]


def workbook(path, sheets, hyperlinks=None):
    """Write minimal OOXML test bytes with only the Python standard library."""
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    relns = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    pkg = "http://schemas.openxmlformats.org/package/2006/relationships"
    hyperlinks = hyperlinks or {}
    with ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="xml" ContentType="application/xml"/>'
                   '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                   + ''.join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in range(1, len(sheets)+1)) + '</Types>')
        z.writestr("_rels/.rels", f'<Relationships xmlns="{pkg}"><Relationship Id="rId1" Type="{relns}/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        z.writestr("xl/workbook.xml", f'<workbook xmlns="{ns}" xmlns:r="{relns}"><sheets>' +
                   ''.join(f'<sheet name={quoteattr(name)} sheetId="{i}" r:id="rId{i}"/>' for i, name in enumerate(sheets, 1)) + '</sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels", f'<Relationships xmlns="{pkg}">' +
                   ''.join(f'<Relationship Id="rId{i}" Type="{relns}/worksheet" Target="worksheets/sheet{i}.xml"/>' for i in range(1,len(sheets)+1)) + '</Relationships>')
        for i, (name, rows) in enumerate(sheets.items(), 1):
            xml = f'<worksheet xmlns="{ns}" xmlns:r="{relns}"><sheetData>'
            for number, values in enumerate(rows, 1):
                xml += f'<row r="{number}">'
                for col, value in enumerate(values):
                    assert col < 26, "fixture helper handles A-Z"
                    ref = f'{chr(65+col)}{number}'
                    if value is None:
                        continue
                    if isinstance(value, tuple) and value[0] == "formula":
                        xml += f'<c r="{ref}"><f>{escape(value[1])}</f></c>'
                    elif isinstance(value, (int, float)):
                        xml += f'<c r="{ref}" t="n"><v>{value}</v></c>'
                    else:
                        xml += f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">{escape(value)}</t></is></c>'
                xml += '</row>'
            xml += '</sheetData>'
            links = hyperlinks.get(name, {})
            if links:
                xml += '<hyperlinks>' + ''.join(f'<hyperlink ref="{ref}" r:id="rId{n}"/>' for n, ref in enumerate(links, 1)) + '</hyperlinks>'
                z.writestr(f'xl/worksheets/_rels/sheet{i}.xml.rels', f'<Relationships xmlns="{pkg}">' + ''.join(f'<Relationship Id="rId{n}" Type="{relns}/hyperlink" Target={quoteattr(url)} TargetMode="External"/>' for n, url in enumerate(links.values(), 1)) + '</Relationships>')
            z.writestr(f'xl/worksheets/sheet{i}.xml', xml + '</worksheet>')


class LiteratureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)

    def json_rows(self, values, name="papers.json"):
        path = self.path / name
        path.write_text(json.dumps(values), encoding="utf-8")
        return read_rows(path)[0]

    def registry(self, **values):
        return ingest(self.json_rows([{"title": "Synthetic paper fixture", **values}]))

    def command(self, *args):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return main(list(args))

    def test_actual_matrix_layout_and_guide_sheet(self):
        path = self.path / "matrix.xlsx"
        workbook(path, {"Matrix": [MATRIX_HEADERS, ["Synthetic title"]],
                        "Sheet1": [["Column", "What it means"], ["Paper", "Name of paper"]]})
        rows, notices = read_rows(path)
        self.assertEqual(len(rows), 1)
        self.assertIn("Skipped sheet 'Sheet1'", notices[0])
        registry = ingest(rows)
        record = registry["records"][0]
        self.assertEqual(record["evidence_status"], "unreviewed")
        self.assertIsNone(record["year"])
        self.assertIsNone(record["url"])
        self.assertIsNone(record["executes_code"])
        self.assertIn("validator", record["missing_fields"])
        self.assertEqual([c["header"] for c in record["sources"][0]["columns"]], MATRIX_HEADERS)
        self.assertEqual(record["sources"][0]["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())

    def test_attack_columns_and_notes_are_not_promoted_to_paper_evidence(self):
        values = {h: f"Original {h}" for h in MATRIX_HEADERS}
        values.update({"Year": "2024", "Evaluation metric": "ASR; F1", "Code/data": "https://example.org/code"})
        registry = ingest(self.json_rows([values]))
        record = registry["records"][0]
        self.assertEqual(record["metrics"], ["ASR", "F1"])
        self.assertEqual(record["our_interpretation"], ["Original My understnding"])
        self.assertEqual(record["open_questions"], ["Original Questions"])
        self.assertIsNone(record["paper_demonstrates"])
        self.assertIsNone(record["domain"])
        self.assertIsNone(record["authors_limitations"])
        self.assertIsNone(record["url"])
        self.assertEqual({c["header"]:c["value"] for c in record["sources"][0]["columns"]}, values)
        self.assertIn("https://example.org/code", record["source_links"])

    def test_excel_hidden_hyperlink_and_literal_hyperlink_formula(self):
        path = self.path / "links.xlsx"
        workbook(path, {"Matrix": [["Paper", "Code/data"], ["Synthetic one", None],
                                  [("formula", 'HYPERLINK("https://example.org/paper2","Synthetic two")'), None]]},
                 {"Matrix": {"A2": "https://example.org/paper1", "B2": "https://example.org/code"}})
        rows, _ = read_rows(path)
        records = ingest(rows)["records"]
        one = next(r for r in records if r["title"] == "Synthetic one")
        two = next(r for r in records if r["title"] == "Synthetic two")
        self.assertEqual(one["url"], "https://example.org/paper1")
        self.assertIn("https://example.org/code", one["source_links"])
        self.assertEqual(two["url"], "https://example.org/paper2")
        self.assertTrue(two["sources"][0]["columns"][0]["is_formula"])

    def test_formulas_are_not_evaluated_or_mistaken_for_details(self):
        path = self.path / "formula.xlsx"
        workbook(path, {"Matrix": [["Paper", "Year", "Attack type"],
                                  ["Synthetic", ("formula", "2000+24"), ("formula", "1+1")]]})
        record = ingest(read_rows(path)[0])["records"][0]
        self.assertIsNone(record["year"])
        self.assertTrue(any("Formula not evaluated" in w for w in record["warnings"]))
        self.assertEqual(record["sources"][0]["columns"][1]["value"], "=2000+24")

    def test_null_and_false_remain_different(self):
        for value, expected in [("no", False), (False, False), ("yes", True), ("unknown", None), ("N/A", None), (None, None)]:
            with self.subTest(value=value):
                record = self.registry(executes_code=value)["records"][0]
                self.assertIs(record["executes_code"], expected)
                self.assertEqual("executes_code" in record["missing_fields"], expected is None)

    def test_invalid_types_years_booleans_and_enums_rejected(self):
        for field, value in [("year", "2024-ish"), ("year", True), ("year", 2024.5),
                             ("executes_code", "maybe"), ("title", 3), ("metrics", [1]),
                             ("evaluation_type", ["magic"]), ("evidence_status", "done"),
                             ("novelty_threat", "ABSENT"), ("doi", "bad-doi")]:
            with self.subTest(field=field, value=value), self.assertRaises(InputError):
                self.registry(**{field:value})

    def test_duplicate_doi_arxiv_and_title_variants_retained(self):
        records = [{"title":"Synthetic A", "doi":"10.1234/TEST"},
                   {"title":"Alternate A", "url":"https://doi.org/10.1234/test"},
                   {"title":"Synthetic B", "arxiv_id":"2401.12345v1"},
                   {"title":"Alternate B", "url":"https://arxiv.org/pdf/2401.12345v3.pdf"},
                   {"title":"A Synthetic: Title!", "year":2024, "doi":"10.5555/one"},
                   {"title":"a synthetic title", "year":2025, "doi":"10.5555/two"}]
        registry = ingest(self.json_rows(records))
        self.assertEqual(len(registry["records"]), 6)
        self.assertEqual({d["reason"] for d in registry["duplicate_candidates"]}, {"doi", "arxiv_id", "title"})
        self.assertEqual(validate_registry(registry), [])

    def test_duplicate_identical_rows_get_unique_ids_without_data_loss(self):
        registry = ingest(self.json_rows([{"title":"Synthetic A"}, {"title":"Synthetic A"}]))
        self.assertEqual(len({r["paper_id"] for r in registry["records"]}), 2)
        self.assertEqual(len(registry["duplicate_candidates"]), 1)
        self.assertEqual(len(registry["records"]), 2)

    def test_identifier_url_queries_fragments_and_legacy_arxiv(self):
        registry = ingest(self.json_rows([
            {"title":"Synthetic A", "doi":"10.1234/a(b)"},
            {"title":"Alternate A", "url":"https://doi.org/10.1234/a%28b%29?source=notes#page2"},
            {"title":"Synthetic B", "arxiv_id":"cs/9901001v1"},
            {"title":"Alternate B", "url":"https://arxiv.org/pdf/cs/9901001v2.pdf?download=1#page3"}
        ]))
        self.assertEqual({d["reason"] for d in registry["duplicate_candidates"]}, {"doi", "arxiv_id"})

    def test_shared_code_link_does_not_make_papers_duplicates(self):
        registry = ingest(self.json_rows([{"title":t,"Code/data":"https://example.org/code"} for t in ("Synthetic A","Synthetic B")]))
        self.assertEqual(registry["duplicate_candidates"], [])

    def test_explicit_id_collisions_fail(self):
        with self.assertRaisesRegex(InputError, "Repeated explicit"):
            ingest(self.json_rows([{"title":t, "paper_id":"P1"} for t in ("A","B")]))

    def review(self):
        return {"reviewed_by":"Synthetic test reviewer", "reviewed_at":"2026-09-08", "notes":"Synthetic metadata fixture only"}

    def test_review_stages_require_provenance(self):
        for status in ("screened", "deep-reviewed", "verified"):
            with self.subTest(status=status), self.assertRaisesRegex(InputError,"review provenance"):
                self.registry(evidence_status=status)
        result = self.registry(evidence_status="screened", review=self.review())
        self.assertEqual(result["records"][0]["evidence_status"], "screened")
        with self.assertRaisesRegex(InputError, "primary paper"):
            self.registry(evidence_status="deep-reviewed", review=self.review(), paper_demonstrates=["Synthetic extraction"])
        deep = self.registry(evidence_status="deep-reviewed", review=self.review(), url="https://example.org/paper", paper_demonstrates=["Synthetic extraction"])
        self.assertEqual(validate_registry(deep), [])

    def test_verified_requires_field_source_locator_and_exact_value(self):
        review = self.review()
        review["checks"] = [{"field":"paper_demonstrates", "value":["Synthetic extraction"],
                             "source_url":"https://example.org/paper", "locator":"Synthetic section 2",
                             "checked_by":"Synthetic checker", "checked_at":"2026-09-08"}]
        result = self.registry(evidence_status="verified", review=review, url="https://example.org/paper", paper_demonstrates=["Synthetic extraction"])
        self.assertEqual(validate_registry(result), [])
        result["records"][0]["paper_demonstrates"] = ["Changed claim"]
        self.assertTrue(any("stale verification" in e for e in validate_registry(result)))
        del review["checks"][0]["locator"]
        with self.assertRaisesRegex(InputError, "locator"):
            self.registry(evidence_status="verified", review=review, url="https://example.org/paper", paper_demonstrates=["Synthetic extraction"])

    def test_invalid_review_date_and_empty_reviewer_rejected(self):
        for field, value in [("reviewed_at","2026-02-30"),("reviewed_by"," ")]:
            review = self.review()
            review[field] = value
            with self.assertRaises(InputError):
                self.registry(evidence_status="screened", review=review)

    def test_blank_claims_and_unknown_novelty_cannot_be_verified(self):
        for value in ([" "], ["unknown"]):
            with self.assertRaises(InputError):
                self.registry(paper_demonstrates=value)
        review = self.review()
        review["checks"] = [{"field":"novelty_threat", "value":"UNKNOWN",
                             "source_url":"https://example.org/paper", "locator":"Synthetic section",
                             "checked_by":"Synthetic checker", "checked_at":"2026-09-08"}]
        with self.assertRaisesRegex(InputError,"unknown/missing field novelty_threat"):
            self.registry(evidence_status="verified", review=review, url="https://example.org/paper", paper_demonstrates=["Synthetic extraction"])

    def test_verification_value_comparison_preserves_json_types(self):
        review = self.review()
        review["checks"] = [{"field":"executes_code", "value":0,
                             "source_url":"https://example.org/paper", "locator":"Synthetic section",
                             "checked_by":"Synthetic checker", "checked_at":"2026-09-08"}]
        with self.assertRaisesRegex(InputError,"stale verification value"):
            self.registry(evidence_status="verified", review=review, url="https://example.org/paper", executes_code=False, paper_demonstrates=["Synthetic extraction"])

    def test_notes_enrich_by_explicit_id_and_preserve_original_sources(self):
        rows = self.json_rows([{"title":"Synthetic A", "year":2024}])
        base = ingest(rows)
        pid = base["records"][0]["paper_id"]
        notes = self.json_rows([{"paper_id":pid, "url":"https://example.org/paper", "validator":"Synthetic rubric"}], "notes.json")
        result = ingest(rows, notes)
        self.assertEqual(result["records"][0]["validator"], "Synthetic rubric")
        self.assertEqual(len(result["records"][0]["sources"]), 2)
        self.assertEqual(result["records"][0]["paper_id"], pid)
        self.assertEqual(result["records"][0]["year"], 2024)
        self.assertEqual(result["records"][0]["evidence_status"], "unreviewed")

    def test_unmatched_or_repeated_notes_fail(self):
        rows = self.json_rows([{"title":"Synthetic A"}])
        with self.assertRaisesRegex(InputError,"needs a paper_id"):
            ingest(rows, self.json_rows([{"title":"Synthetic A"}], "notes.json"))
        pid = ingest(rows)["records"][0]["paper_id"]
        notes = self.json_rows([{"paper_id":pid},{"paper_id":pid}],"notes.json")
        with self.assertRaisesRegex(InputError,"Multiple note"):
            ingest(rows, notes)

    def test_csv_bom_unicode_multiline_and_tsv(self):
        path = self.path / "matrix.csv"
        path.write_text('\ufeffPaper,Year,My understnding\n"Synthetic café",2024,"Line one\nLine two"\n',encoding="utf-8")
        record = ingest(read_rows(path)[0])["records"][0]
        self.assertEqual(record["title"],"Synthetic café")
        self.assertEqual(record["our_interpretation"],["Line one","Line two"])
        path = self.path / "matrix.tsv"
        path.write_text('Paper\tYear\nSynthetic TSV\t2024\n',encoding="utf-8")
        self.assertEqual(ingest(read_rows(path)[0])["records"][0]["year"],2024)

    def test_header_selection_and_empty_rows(self):
        path = self.path / "matrix.xlsx"
        workbook(path,{"Research":[["Preface"],["Paper","Year"],[None,None],["Synthetic",2024]]})
        rows, _ = read_rows(path,"Research",2)
        self.assertEqual(rows[0]["row"],4)
        self.assertEqual(ingest(rows)["records"][0]["year"],2024)
        with self.assertRaisesRegex(InputError,"Available"):
            read_rows(path,"Wrong")
        with self.assertRaises(InputError):
            read_rows(path,header_row=0)

    def test_duplicate_headers_and_overflow_are_rejected(self):
        for content in ('Paper, paper \nA,B\n','Paper\nA,B\n'):
            path = self.path / "bad.csv"
            path.write_text(content)
            with self.assertRaises(InputError):
                read_rows(path)

    def test_jsonl_and_unknown_columns_are_preserved(self):
        path = self.path / "papers.jsonl"
        path.write_text('\n{"title":"Synthetic","Unmapped":{"custom":["note"]}}\n',encoding="utf-8")
        record = ingest(read_rows(path)[0])["records"][0]
        self.assertEqual(record["sources"][0]["row"],2)
        self.assertEqual(record["sources"][0]["columns"][1]["value"],{"custom":["note"]})

    def test_malformed_json_repeated_keys_nan_and_empty_inputs(self):
        for content in ('[{"title":"A","title":"B"}]','[{"title":"A","year":NaN}]','{','[]','[{}]'):
            path = self.path / "bad.json"
            path.write_text(content)
            with self.assertRaises((InputError, ValueError)):
                read_rows(path)

    def test_bad_urls_rejected_and_unsafe_hyperlink_preserved_only_as_source(self):
        with self.assertRaisesRegex(InputError, "HTTP"):
            self.registry(url="javascript:alert(1)")
        path = self.path / "unsafe.xlsx"
        workbook(path,{"Matrix":[["Paper"],["Synthetic"]]}, {"Matrix":{"A2":"file:///local/file"}})
        record = ingest(read_rows(path)[0])["records"][0]
        self.assertEqual(record["source_links"],[])
        self.assertIsNone(record["url"])
        self.assertEqual(record["sources"][0]["columns"][0]["hyperlink"],"file:///local/file")

    def test_stale_missing_and_duplicate_metadata_rejected_on_export(self):
        for mutation in ("missing", "duplicates", "unknown", "bad_record"):
            registry = self.registry()
            if mutation == "missing": registry["records"][0]["missing_fields"] = []
            if mutation == "duplicates": registry["duplicate_candidates"] = [{}]
            if mutation == "unknown": registry["records"][0]["invented"] = "no"
            if mutation == "bad_record": registry["records"] = [None]
            with self.subTest(mutation=mutation), self.assertRaises(InputError):
                export_web(registry)

    def test_every_schema_field_present_and_web_is_traceable(self):
        registry = self.registry(paper_demonstrates=["Synthetic unverified claim"], our_interpretation=["Synthetic opinion"], open_questions=["Synthetic question"])
        before = copy.deepcopy(registry)
        web = export_web(registry)
        self.assertEqual(set(web["records"][0]),set(schema()["properties"]))
        self.assertEqual(web["records"],registry["records"])
        self.assertEqual(web["summary"]["by_evidence_status"]["verified"],0)
        self.assertEqual(registry,before)

    def test_deterministic_import_and_python_only_cli_end_to_end(self):
        self.json_rows([{"title":"Synthetic A"}])
        inp, out, web, report = [self.path/n for n in ("papers.json","registry.json","web.json","report.json")]
        args = ["import",str(inp),"--output",str(out),"--web-output",str(web),"--report",str(report)]
        self.assertEqual(self.command(*args),0)
        expected = [p.read_bytes() for p in (out,web,report)]
        self.assertEqual(self.command(*args,"--replace"),0)
        self.assertEqual(expected,[p.read_bytes() for p in (out,web,report)])
        result = subprocess.run([sys.executable,str(ROOT/"scripts/literature.py"),"validate",str(out)],capture_output=True,text=True,cwd=self.path)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(self.command("export",str(out),"--output",str(web),"--replace"),0)
        self.assertEqual(web.read_bytes(),expected[1])

    def test_invalid_import_does_not_replace_prior_good_registry_or_web(self):
        self.json_rows([{"title":"Synthetic","year":"wrong"}])
        inp, out, web, report = [self.path/n for n in ("papers.json","registry.json","web.json","report.json")]
        out.write_text("existing registry")
        web.write_text("existing website")
        self.assertEqual(self.command("import",str(inp),"--output",str(out),"--web-output",str(web),"--report",str(report),"--replace"),2)
        self.assertEqual(out.read_text(),"existing registry")
        self.assertEqual(web.read_text(),"existing website")
        self.assertFalse(json.loads(report.read_text())["ok"])

    def test_duplicate_gate_and_output_input_collisions(self):
        self.json_rows([{"title":"Synthetic"},{"title":"Synthetic"}])
        inp, out, web, report = [self.path/n for n in ("papers.json","registry.json","web.json","report.json")]
        args = ["import",str(inp),"--output",str(out),"--web-output",str(web),"--report",str(report)]
        self.assertEqual(self.command(*args,"--fail-on-duplicates"),2)
        self.assertFalse(out.exists())
        self.assertTrue(json.loads(report.read_text())["duplicate_candidates"])
        before = inp.read_bytes()
        self.assertEqual(self.command("import",str(inp),"--output",str(inp),"--replace"),2)
        self.assertEqual(inp.read_bytes(),before)
        self.assertEqual(self.command("import",str(inp),"--output",str(out),"--web-output",str(out)),2)


if __name__ == "__main__":
    unittest.main()
