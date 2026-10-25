"""Protocol helpers shared by coordinator, workers and client."""
import json
import logging
import uuid
from .clock import LamportClock
from .generated import debugmesh_pb2 as pb


def configure_logging():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')


class Node:
    def __init__(self, node_id):
        self.node_id = node_id
        self.clock = LamportClock()
        self.log = logging.getLogger('debugmesh.' + node_id)

    def send(self, request_id=None):
        n = self.clock.tick()
        self.event('send', n)
        return pb.Envelope(request_id=request_id or str(uuid.uuid4()), sender_id=self.node_id, logical_timestamp=n)

    def receive(self, meta):
        n = self.clock.receive(meta.logical_timestamp)
        self.event('receive', n, remote=meta.sender_id, remote_timestamp=meta.logical_timestamp)
        return n

    def event(self, event, timestamp=None, **kwargs):
        self.log.info(json.dumps({'node': self.node_id, 'event': event, 'logical_timestamp': timestamp if timestamp is not None else self.clock.value, **kwargs}, ensure_ascii=False))
