from debugmesh.clock import LamportClock
from debugmesh.analyzer import analyze
from debugmesh.generated import debugmesh_pb2 as pb


def test_lamport_causal_rule():
    a=LamportClock();b=LamportClock()
    sent=a.tick()
    assert sent==1
    received=b.receive(sent)
    assert received>sent
    assert a.receive(received)>received


def test_deterministic_classification():
    lines=[pb.LogLine(line_number=2,text='ModuleNotFoundError: dependency'),pb.LogLine(line_number=5,text='FAILED tests/test_api.py'),pb.LogLine(line_number=6,text='INFO OK')]
    findings=analyze(lines,'task','worker',lambda:12)
    assert [f.category for f in findings]==['build','tests']
    assert findings[0].evidence==["line 2: ModuleNotFoundError: dependency"]
    assert all(f.worker_id=='worker' and f.logical_timestamp==12 for f in findings)


def test_wire_roundtrip():
    msg=pb.SubmitLogsRequest(meta=pb.Envelope(request_id='r',sender_id='c',logical_timestamp=7),source='ci',lines=[pb.LogLine(line_number=3,text='error')])
    assert pb.SubmitLogsRequest.FromString(msg.SerializeToString())==msg
