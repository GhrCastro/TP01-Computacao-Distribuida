from concurrent.futures import ThreadPoolExecutor

from debugmesh.clock import LamportClock


def test_lamport_causal_rule():
    sender = LamportClock()
    receiver = LamportClock()

    sent = sender.tick()
    received = receiver.receive(sent)

    assert sent == 1
    assert received > sent
    assert sender.receive(received) > received


def test_lamport_receive_uses_maximum_clock():
    clock = LamportClock()
    for _ in range(12):
        clock.tick()

    assert clock.receive(3) == 13
    assert clock.receive(30) == 31


def test_lamport_thread_safety_under_concurrent_events():
    clock = LamportClock()

    with ThreadPoolExecutor(max_workers=12) as executor:
        values = list(executor.map(lambda _: clock.tick(), range(1200)))

    assert clock.value == 1200
    assert len(set(values)) == 1200
    assert min(values) == 1
    assert max(values) == 1200


def test_lamport_causality_across_message_round_trip():
    """A reply and a later local event follow their causal predecessors."""
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
