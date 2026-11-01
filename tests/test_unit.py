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


def test_lamport_causality_across_message_round_trip():
    """A reply and a subsequent local event must follow their causal predecessors."""
    from debugmesh.common import Node

    client = Node('unit-client')
    worker = Node('unit-worker')
    outbound = client.send(request_id='round-trip')
    worker_received_at = worker.receive(outbound)
    response = worker.send(request_id=outbound.request_id)
    client_received_at = client.receive(response)

    assert outbound.sender_id == 'unit-client'
    assert response.request_id == outbound.request_id
    assert outbound.logical_timestamp < worker_received_at < response.logical_timestamp < client_received_at
    assert client.send().logical_timestamp > client_received_at


def test_lamport_receive_uses_maximum_clock():
    clock = LamportClock()
    for _ in range(12):
        clock.tick()
    assert clock.receive(3) == 13  # a late message never sets the clock back
    assert clock.receive(30) == 31  # a future causal timestamp advances it


def test_lamport_thread_safety_under_concurrent_events():
    from concurrent.futures import ThreadPoolExecutor

    clock = LamportClock()
    def advance(_):
        return clock.tick()

    with ThreadPoolExecutor(max_workers=12) as executor:
        values = list(executor.map(advance, range(1200)))

    assert clock.value == 1200
    assert len(set(values)) == 1200
    assert min(values) == 1 and max(values) == 1200
