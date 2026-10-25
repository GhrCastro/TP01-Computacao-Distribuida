"""Offline bootstrap of checked-in proto bindings (no protoc needed at runtime).

Generation uses a checked field specification mirroring the public .proto schema;
for regular regeneration prefer: python -m grpc_tools.protoc ...
"""
from google.protobuf import descriptor_pb2
from pathlib import Path
import base64

root = Path(__file__).resolve().parents[1]
fd = descriptor_pb2.FileDescriptorProto(name="debugmesh/v1/debugmesh.proto", package="debugmesh.v1", syntax="proto3")
T = descriptor_pb2.FieldDescriptorProto
S = {
"Envelope": [('request_id','string'),('sender_id','string'),('logical_timestamp','uint64')],
"LogLine": [('line_number','uint64'),('text','string')],
"SubmitLogsRequest": [('meta','Envelope'),('source','string'),('lines','LogLine[]')],
"SubmitLogsResponse": [('meta','Envelope'),('analysis_id','string'),('state','AnalysisState')],
"GetAnalysisStatusRequest": [('meta','Envelope'),('analysis_id','string')],
"Finding": [('task_id','string'),('worker_id','string'),('category','string'),('evidence','string[]'),('root_cause_hypothesis','string'),('suggested_fix','string'),('suggested_test','string'),('confidence','double'),('logical_timestamp','uint64')],
"GetAnalysisStatusResponse": [('meta','Envelope'),('analysis_id','string'),('state','AnalysisState'),('findings','Finding[]'),('error','string')],
"AssignTaskRequest": [('meta','Envelope'),('analysis_id','string'),('task_id','string'),('attempt','uint32'),('lines','LogLine[]')],
"AssignTaskResponse": [('meta','Envelope'),('task_id','string'),('findings','Finding[]')],
"ElectionRequest": [('meta','Envelope'),('candidate_priority','uint32')],
"ElectionResponse": [('meta','Envelope'),('higher_priority_alive','bool')],
"LeaderAnnouncement": [('meta','Envelope'),('leader_id','string'),('leader_priority','uint32'),('term','uint64')],
"Ack": [('meta','Envelope'),('accepted','bool'),('detail','string')],
}
types={'string':T.TYPE_STRING,'uint32':T.TYPE_UINT32,'uint64':T.TYPE_UINT64,'double':T.TYPE_DOUBLE,'bool':T.TYPE_BOOL}
for name,fields in S.items():
    msg=fd.message_type.add();msg.name=name
    for i,(n,kind) in enumerate(fields,1):
        f=msg.field.add();f.name=n;f.number=i;f.label=T.LABEL_REPEATED if kind.endswith('[]') else T.LABEL_OPTIONAL
        kind=kind.removesuffix('[]')
        if kind in types: f.type=types[kind]
        else: f.type=T.TYPE_ENUM if kind=='AnalysisState' else T.TYPE_MESSAGE;f.type_name='.debugmesh.v1.'+kind
state=fd.enum_type.add();state.name='AnalysisState'
for i,name in enumerate(['ANALYSIS_STATE_UNSPECIFIED','ANALYSIS_PENDING','ANALYSIS_RUNNING','ANALYSIS_COMPLETED','ANALYSIS_FAILED']):
    v=state.value.add();v.name=name;v.number=i
for name,operations in [('CoordinatorService',[('SubmitLogs','SubmitLogsRequest','SubmitLogsResponse'),('GetAnalysisStatus','GetAnalysisStatusRequest','GetAnalysisStatusResponse')]),('WorkerService',[('AssignTask','AssignTaskRequest','AssignTaskResponse')]),('ElectionService',[('Election','ElectionRequest','ElectionResponse'),('AnnounceLeader','LeaderAnnouncement','Ack')])]:
    svc=fd.service.add();svc.name=name
    for meth,req,resp in operations:
        m=svc.method.add();m.name=meth;m.input_type='.debugmesh.v1.'+req;m.output_type='.debugmesh.v1.'+resp
out=root/'src/debugmesh/generated/debugmesh_pb2.py'
out.write_text('''# Auto-generated protocol classes. Source: proto/debugmesh/v1/debugmesh.proto\nfrom google.protobuf import descriptor_pool as _descriptor_pool\nfrom google.protobuf.internal import builder as _builder\nfrom google.protobuf import symbol_database as _symbol_database\n_sym_db = _symbol_database.Default()\nDESCRIPTOR = _descriptor_pool.Default().AddSerializedFile('''+repr(fd.SerializeToString())+''')\n_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, globals())\n_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'debugmesh.generated.debugmesh_pb2', globals())\n''')
print('Wrote',out)
