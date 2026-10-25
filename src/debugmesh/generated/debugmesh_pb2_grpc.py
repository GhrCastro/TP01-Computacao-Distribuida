"""gRPC Python service bindings for debugmesh.v1."""
import grpc
from . import debugmesh_pb2 as pb


def _stub_method(channel, service, method, request, response):
    return channel.unary_unary(
        f'/debugmesh.v1.{service}/{method}',
        request_serializer=request.SerializeToString,
        response_deserializer=response.FromString,
    )


class CoordinatorServiceStub:
    def __init__(self, channel):
        self.SubmitLogs = _stub_method(channel, 'CoordinatorService', 'SubmitLogs', pb.SubmitLogsRequest, pb.SubmitLogsResponse)
        self.GetAnalysisStatus = _stub_method(channel, 'CoordinatorService', 'GetAnalysisStatus', pb.GetAnalysisStatusRequest, pb.GetAnalysisStatusResponse)


class WorkerServiceStub:
    def __init__(self, channel):
        self.AssignTask = _stub_method(channel, 'WorkerService', 'AssignTask', pb.AssignTaskRequest, pb.AssignTaskResponse)


class ElectionServiceStub:
    def __init__(self, channel):
        self.Election = _stub_method(channel, 'ElectionService', 'Election', pb.ElectionRequest, pb.ElectionResponse)
        self.AnnounceLeader = _stub_method(channel, 'ElectionService', 'AnnounceLeader', pb.LeaderAnnouncement, pb.Ack)


class CoordinatorServiceServicer:
    def SubmitLogs(self, request, context):
        context.abort(grpc.StatusCode.UNIMPLEMENTED, 'SubmitLogs')

    def GetAnalysisStatus(self, request, context):
        context.abort(grpc.StatusCode.UNIMPLEMENTED, 'GetAnalysisStatus')


class WorkerServiceServicer:
    def AssignTask(self, request, context):
        context.abort(grpc.StatusCode.UNIMPLEMENTED, 'AssignTask')


class ElectionServiceServicer:
    def Election(self, request, context):
        context.abort(grpc.StatusCode.UNIMPLEMENTED, 'Election')

    def AnnounceLeader(self, request, context):
        context.abort(grpc.StatusCode.UNIMPLEMENTED, 'AnnounceLeader')


def _register(server, name, handler_specs, impl):
    handlers = {
        method: grpc.unary_unary_rpc_method_handler(
            getattr(impl, method),
            request_deserializer=req.FromString,
            response_serializer=resp.SerializeToString,
        ) for method, req, resp in handler_specs
    }
    server.add_generic_rpc_handlers((grpc.method_handlers_generic_handler('debugmesh.v1.'+name, handlers),))


def add_CoordinatorServiceServicer_to_server(servicer, server):
    _register(server, 'CoordinatorService', [('SubmitLogs', pb.SubmitLogsRequest, pb.SubmitLogsResponse), ('GetAnalysisStatus', pb.GetAnalysisStatusRequest, pb.GetAnalysisStatusResponse)], servicer)


def add_WorkerServiceServicer_to_server(servicer, server):
    _register(server, 'WorkerService', [('AssignTask', pb.AssignTaskRequest, pb.AssignTaskResponse)], servicer)


def add_ElectionServiceServicer_to_server(servicer, server):
    _register(server, 'ElectionService', [('Election', pb.ElectionRequest, pb.ElectionResponse), ('AnnounceLeader', pb.LeaderAnnouncement, pb.Ack)], servicer)
