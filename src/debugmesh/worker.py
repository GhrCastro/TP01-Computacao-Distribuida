"""Standalone gRPC worker process."""
import time
from concurrent.futures import ThreadPoolExecutor
import grpc
from .common import Node
from .analyzer import analyze
from .generated import debugmesh_pb2 as pb, debugmesh_pb2_grpc as rpc


class Worker(Node, rpc.WorkerServiceServicer):
    def __init__(self, node_id, delay=0.0):
        super().__init__(node_id)
        self.delay=delay

    def AssignTask(self, request, context):
        if not request.task_id or not request.meta.sender_id:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, 'task_id and sender_id are required')
        self.receive(request.meta)
        if self.delay:
            time.sleep(self.delay)
        findings=analyze(request.lines, request.task_id, self.node_id, self.clock.tick)
        self.event('task_done', task_id=request.task_id, findings=len(findings))
        return pb.AssignTaskResponse(meta=self.send(request.meta.request_id), task_id=request.task_id, findings=findings)


def serve_worker(node_id, address, delay=0.0):
    worker=Worker(node_id,delay)
    server=grpc.server(ThreadPoolExecutor(max_workers=8))
    rpc.add_WorkerServiceServicer_to_server(worker,server)
    if server.add_insecure_port(address)==0:
        raise RuntimeError('Unable to bind worker to '+address)
    server.start()
    worker.event('listening',address=address)
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        server.stop(grace=2).wait()
