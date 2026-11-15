from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from backend.app.assistant_evidence import excerpt,snapshot,quality_report
from backend.app.common import text_hash


@pytest.mark.parametrize('body,cue',[
    ('Administrative cover '*100+' No new symptom reported. History: fictional cough for three days.','History:'),
    ('ข้อมูลส่วนปกเอกสาร '*200+' ไม่มีการเปลี่ยนยา อาการสมมุติไอสามวัน กรุณาทบทวนต้นฉบับ','อาการสมมุติ'),
    ('📄 Cover sheet '*200+' History: authored fictional follow-up; no treatment change.','History:'),
])
def test_single_line_passage_reaches_actual_cue_and_preserves_original_offsets(body,cue):
    selected,start,end=excerpt(body)
    assert start>0 and cue in selected and selected==body[start:end]
    assert len(selected.encode('utf-8'))<=480


def test_short_original_text_is_preserved_whole():
    text='อาการสมมุติ 📄 ไม่มีข้อมูลเพิ่ม'
    assert excerpt(text)==(text,0,len(text))


def source_run(text,selected,start,end):
    source={'ref':'s1','kind':'document','id':'doc1','version':1,'label':'Fictional note','fields':{'revision':'v1','content_hash':text_hash(text)},'text':text,'selection':{'kind':'excerpt','start':start,'end':end}}
    run=SimpleNamespace(id='run1',locale='en',source_manifest={'sources':[source]},inference_view={'sources':[{'ref':'s1','kind':'document','fields':{},'text':selected}]})
    return run,source


def test_duplicate_quotes_highlight_occurrence_within_original_selected_span():
    text='Same quote. 📄 Original cover. Same quote.';start=text.rfind('Same quote.')
    run,row=source_run(text,text[start:],start,len(text))
    revision=SimpleNamespace(artifact={'facts':[{'source_ref':'s1','quote':'Same quote.','display':'Same quote.'}]})
    result=snapshot(run,row,True,revision);citation=result['citations'][0]
    assert citation['start']==start and result['text'][citation['start']:citation['end']]=='Same quote.'


@pytest.mark.parametrize('corruption',['hash','span','selected'])
def test_unavailable_original_or_selected_span_abstains(corruption):
    run,row=source_run('Original text','Original text',0,13)
    if corruption=='hash':row['fields']['content_hash']='f'*64
    elif corruption=='span':row['selection']['end']=99
    else:run.inference_view['sources'][0]['text']='Invented text'
    with pytest.raises(HTTPException) as caught:snapshot(run,row,True)
    assert caught.value.status_code==409


def test_wrong_typed_display_is_not_counted_as_verified_evidence():
    run=SimpleNamespace(locale='en',source_manifest={'sources':[{'ref':'s1','kind':'lab'}]},inference_view={'sources':[{'ref':'s1','kind':'lab','fields':{'result':'Fictional analyte A: 152 mg/dL'}}]})
    revision=SimpleNamespace(artifact={'facts':[{'source_ref':'s1','field':'result','display':'Fictional analyte B: 152 mg/dL'}]})
    assert quality_report(run,revision)['verified_fact_count']==0
