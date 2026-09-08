"""PR5 intake tests reconciled with canonical versioned paper records."""
import copy
import hashlib
import json
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr
from zipfile import ZipFile
import pytest
from jailbreak_eval.literature.inputs import InputError, read_rows
from jailbreak_eval.literature.core import (import_rows, review_notes, fields, doi, arxiv, duplicate_candidates)
from jailbreak_eval.registry import REGISTRIES, load_registries, latest_records, web_bundle, validate_history
from jailbreak_eval.store import envelopes, encode

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

TIME='2026-09-08T00:00:00Z'
LATER='2026-09-09T00:00:00Z'

@pytest.fixture
def workspace(tmp_path):
    d=tmp_path/'registries';d.mkdir()
    for n,e in envelopes({n:[] for n in REGISTRIES}).items(): (d/f'{n}.json').write_bytes(encode(e))
    return tmp_path


def import_values(root,values,name='papers.json'):
    path=root/name;path.write_text(json.dumps(values))
    return import_rows(read_rows(path)[0],root/'registries',root,TIME)


def papers(root):return latest_records(load_registries(root/'registries'))['papers']


def curator(paper_id,version='2',status='screened',time=LATER,verified=False):
    claim={'id':'evidence:safe-fixture','topic':'success_definition','claim':'Synthetic fixture only, not a real paper finding.',
           'source_id':'source:safe-fixture','locator':'Fixture paragraph 1','verification_status':'verified' if verified else 'unverified'}
    return {'id':paper_id,'version':version,'timestamp':time,'evidence_status':status,
            'sources':[{'id':'source:safe-fixture','url':'https://example.invalid/safe-paper','locator':'Synthetic paper fixture'}],
            'paper_demonstrates':[claim],
            'review':{'reviewer':'Synthetic reviewer','reviewed_at':time,'notes':'Explicit source extraction test.',
                      'verified_evidence_ids':[claim['id']] if verified else []}}


def test_excel_notes_canonical_web_roundtrip_preserves_all_cells(workspace):
    path=workspace/'matrix.xlsx'
    values=['Safe fixture']+[None]*18
    values[14]='Intake interpretation';values[15]='Open intake question'
    workbook(path,{'Matrix':[MATRIX_HEADERS,values],'Guide':[['Column','Meaning'],['Paper','Title']]},
             {'Matrix':{'A2':'https://example.invalid/safe-paper'}})
    rows,notices=read_rows(path)
    assert notices and len(rows)==1
    import_rows(rows,workspace/'registries',workspace,TIME)
    p=papers(workspace)[0]
    assert p['evidence_status']=='listed' and not p['paper_demonstrates']
    assert p['year'] is None and p['review'] is None
    assert p['our_interpretation'][0]['text']=='Intake interpretation'
    artifact=p['intake_artifacts'][0]
    raw=(workspace/artifact['uri']).read_bytes();source=json.loads(raw)['source']
    assert hashlib.sha256(raw).hexdigest()==artifact['sha256']
    assert source['sha256']==hashlib.sha256(path.read_bytes()).hexdigest()
    assert source['sheet']=='Matrix' and source['row']==2
    assert len(source['columns'])==19 and source['columns'][0]['cell']=='A2'
    assert source['columns'][0]['hyperlink']=='https://example.invalid/safe-paper'
    b=web_bundle(workspace/'registries')
    assert b['papers'][0]['id']==p['id'] and b['readiness']['experiments']==0


def test_listed_to_screened_deep_reviewed_verified_keeps_id_and_history(workspace):
    import_values(workspace,[{'Paper':'Safe title','paper_id':'paper:stable'}])
    previous=load_registries(workspace/'registries')
    for i,status in enumerate(('screened','deep-reviewed','verified'),2):
        note=curator('paper:stable',str(i),status,f'2026-09-{8+i:02d}T00:00:00Z',status=='verified')
        review_notes([note],workspace/'registries')
        current=load_registries(workspace/'registries');validate_history(current,previous)
        assert len(current['papers'])==i and {p['id'] for p in current['papers']}=={'paper:stable'}
        exported=web_bundle(workspace/'registries')
        assert len(exported['papers'])==1 and exported['papers'][0]['evidence_status']==status
        assert exported['paper_evidence'][0]['review_state']==status
        previous=current


def test_raw_matrix_status_or_claim_is_not_verified_evidence(workspace):
    import_values(workspace,[{'Paper':'Safe fixture','evidence_status':'verified','paper_demonstrates':['User claim'],
                             'review':{'reviewer':'someone'},'Main Result':'Claimed result','executes_code':False}])
    p=papers(workspace)[0]
    assert p['evidence_status']=='listed' and p['paper_demonstrates']==[]
    s=json.loads((workspace/p['intake_artifacts'][0]['uri']).read_text())['source']
    assert any(c['header']=='executes_code' and c['value'] is False for c in s['columns'])


def test_duplicate_candidates_retained_and_repeat_import_stable(workspace):
    values=[{'Paper':'Same fixture','doi':'10.1234/Test'}, {'Paper':'Same fixture','doi':'https://doi.org/10.1234/test'}]
    first=import_values(workspace,values)
    assert len(first['imported_ids'])==2
    assert {'doi','title'} <= {g['reason'] for g in first['duplicate_candidates']}
    second=import_values(workspace,values)
    assert first['imported_ids']==second['imported_ids'] and len(papers(workspace))==2


def test_exact_duplicate_rows_are_not_silently_merged(workspace):
    r=import_values(workspace,[{'Paper':'Same fixture'},{'Paper':'Same fixture'}])
    assert len(set(r['imported_ids']))==2
    assert import_values(workspace,[{'Paper':'Same fixture'},{'Paper':'Same fixture'}])['imported_ids']==r['imported_ids']


def test_duplicate_gate_leaves_previous_outputs(workspace):
    path=workspace/'papers.json';path.write_text('[{"Paper":"same"},{"Paper":"same"}]')
    before=(workspace/'registries/papers.json').read_bytes()
    with pytest.raises(ValueError,match='Duplicate candidates'):
        import_rows(read_rows(path)[0],workspace/'registries',workspace,TIME,fail_on_duplicates=True)
    assert (workspace/'registries/papers.json').read_bytes()==before
    assert not (workspace/'literature/intake').exists()


def test_reordering_unique_unchanged_rows_keeps_identity(workspace):
    import_values(workspace,[{'Paper':'First'},{'Paper':'Second'}])
    ids={p['title']:p['id'] for p in papers(workspace)}
    # Row locations change, so attach fresh provenance through explicit versions.
    with pytest.raises(ValueError,match='Updated intake needs'):
        import_values(workspace,[{'Paper':'Second'},{'Paper':'First'}])
    assert {p['title']:p['id'] for p in papers(workspace)}==ids


def test_changed_intake_requires_explicit_id_version_and_keeps_curated_fields(workspace):
    import_values(workspace,[{'Paper':'First','paper_id':'paper:stable'}])
    review_notes([curator('paper:stable')],workspace/'registries')
    with pytest.raises(ValueError,match='Changed intake row'):
        import_values(workspace,[{'Paper':'Corrected'}])
    import_values(workspace,[{'Paper':'Corrected','paper_id':'paper:stable','version':'3','timestamp':'2026-09-10T00:00:00Z'}])
    p=papers(workspace)[0]
    assert p['title']=='First' and p['evidence_status']=='screened' and len(p['intake_artifacts'])==2


@pytest.mark.parametrize('mutation',[{'version':'1'},{'timestamp':TIME},{'review':None}])
def test_invalid_review_update_rejected_without_writes(workspace,mutation):
    import_values(workspace,[{'Paper':'Safe','paper_id':'paper:stable'}])
    before=(workspace/'registries/papers.json').read_bytes()
    with pytest.raises(ValueError):review_notes([{**curator('paper:stable'),**mutation}],workspace/'registries')
    assert (workspace/'registries/papers.json').read_bytes()==before


def test_unverified_extraction_is_displayed_at_actual_state(workspace):
    import_values(workspace,[{'Paper':'Safe','paper_id':'paper:stable'}])
    review_notes([curator('paper:stable')],workspace/'registries')
    b=web_bundle(workspace/'registries')
    assert b['paper_evidence'][0]['verification_status']=='unverified'
    assert b['verified_paper_evidence']==[]


def test_verified_claim_needs_current_review_ids(workspace):
    import_values(workspace,[{'Paper':'Safe','paper_id':'paper:stable'}])
    note=curator('paper:stable',verified=True);note['review']['verified_evidence_ids']=[]
    with pytest.raises(ValueError,match='verification|provenance'):review_notes([note],workspace/'registries')


def test_missing_metadata_and_unknown_novelty_stay_unknown(workspace):
    import_values(workspace,[{'Paper':'Safe','Year':'Unknown','Main Result':'unverified note'}])
    p=papers(workspace)[0]
    assert p['year'] is None and p['identifiers']=={'doi':None,'arxiv_id':None}
    assert p['novelty']['status']=='unassessed'


def test_hidden_hyperlink_and_literal_formula_preserved(workspace):
    p=workspace/'links.xlsx'
    workbook(p,{'Matrix':[['Paper','Year','Code/data'],[('formula','HYPERLINK("https://example.invalid/paper","Safe title")'),('formula','2000+24'),'https://example.invalid/code']]})
    rows,_=read_rows(p);import_rows(rows,workspace/'registries',workspace,TIME)
    record=papers(workspace)[0]
    assert record['title']=='Safe title' and record['year'] is None
    assert {s['url'] for s in record['sources']}=={'https://example.invalid/paper','https://example.invalid/code'}


@pytest.mark.parametrize('suffix,content',[('.csv','Paper,Year\nSafe,\n'),('.tsv','Paper\tYear\nSafe\t\n'),('.json','[{"Paper":"Safe"}]'),('.jsonl','{"Paper":"Safe"}\n')])
def test_all_intake_formats(workspace,suffix,content):
    p=workspace/('source'+suffix);p.write_text(content)
    import_rows(read_rows(p)[0],workspace/'registries',workspace,TIME)
    assert papers(workspace)[0]['title']=='Safe'


@pytest.mark.parametrize('value,expected',[('DOI:10.1234/ABC','10.1234/abc'),('https://doi.org/10.1234%2FABC','10.1234/abc'),('https://example.invalid/10.1234/ABC',None)])
def test_doi_variants(value,expected):assert doi(value)==expected


@pytest.mark.parametrize('value',['https://arxiv.org/pdf/2401.01234v2.pdf','arXiv:2401.01234v3'])
def test_arxiv_versions(value):assert arxiv(value)=='2401.01234'


@pytest.mark.parametrize('content',['[{"Paper":"one","Paper":"two"}]','[{"Paper":"safe","Year":NaN}]'])
def test_malformed_json_is_rejected(workspace,content):
    p=workspace/'bad.json';p.write_text(content)
    with pytest.raises(ValueError):read_rows(p)


def test_sidecar_tamper_blocks_reimport(workspace):
    import_values(workspace,[{'Paper':'Safe'}]);p=papers(workspace)[0]
    (workspace/p['intake_artifacts'][0]['uri']).write_text('{}')
    with pytest.raises(ValueError,match='checksum'):import_values(workspace,[{'Paper':'Safe'}])


def test_designated_paper_url_duplicate_is_retained(workspace):
    result=import_values(workspace,[{'Paper':'Title one','url':'https://example.invalid/same'},{'Paper':'Title two','url':'https://example.invalid/same'}])
    assert any(g['reason']=='paper_url' for g in result['duplicate_candidates'])
    assert len(papers(workspace))==2


def test_conflicting_semantic_aliases_rejected(workspace):
    with pytest.raises(ValueError,match='Conflicting columns'):
        import_values(workspace,[{'Paper':'First title','title':'Different title'}])


def test_scientific_changes_need_fresh_review_provenance(workspace):
    import_values(workspace,[{'Paper':'Safe','paper_id':'paper:stable'}]);review_notes([curator('paper:stable')],workspace/'registries')
    note={'id':'paper:stable','version':'3','timestamp':'2026-09-10T00:00:00Z','title':'Corrected title','review':curator('paper:stable')['review']}
    with pytest.raises(ValueError,match='fresh review|later review'):review_notes([note],workspace/'registries')


def test_xlsx_internal_hyperlink_metadata_is_preserved(workspace):
    from openpyxl import Workbook
    from openpyxl.worksheet.hyperlink import Hyperlink
    book=Workbook();sheet=book.active;sheet.title='Matrix';sheet.append(['Paper']);sheet.append(['Safe'])
    sheet['A2'].hyperlink=Hyperlink(ref='A2',location="'Matrix'!A1",tooltip='Original tooltip',display='Original display')
    path=workspace/'internal.xlsx';book.save(path);book.close()
    rows,_=read_rows(path);c=rows[0]['columns'][0]
    assert c['hyperlink_location']=="'Matrix'!A1" and c['hyperlink_tooltip']=='Original tooltip' and c['hyperlink_display']=='Original display'
