"""Run coordinator, workers and CLI requests via `python -m debugmesh`."""
import argparse
import json
import logging
import sys
import time
import grpc
from google.protobuf.json_format import MessageToDict
from .common import Node, configure_logging
from .coordinator import serve_coordinator
from .worker import serve_worker
from .generated import debugmesh_pb2 as pb, debugmesh_pb2_grpc as rpc


def _peers(value):
    peers=[]
    for entry in filter(None,value.split(',')):
        try:
            node,priority,address=entry.split('@',2)
            peers.append((node,int(priority),address))
        except ValueError as exc:
            raise argparse.ArgumentTypeError('peers format: id@priority@host:port,...') from exc
    return peers


def parser():
    p=argparse.ArgumentParser(prog='debugmesh',description='DebugMesh Entrega 1')
    sub=p.add_subparsers(dest='command',required=True)
    w=sub.add_parser('worker'); w.add_argument('--id',required=True); w.add_argument('--bind',required=True);w.add_argument('--delay',type=float,default=0)
    c=sub.add_parser('coordinator');c.add_argument('--id',required=True);c.add_argument('--bind',required=True);c.add_argument('--priority',required=True,type=int);c.add_argument('--peers',default='');c.add_argument('--workers',required=True);c.add_argument('--batch-size',type=int,default=3);c.add_argument('--worker-timeout',type=float,default=3);c.add_argument('--election-timeout',type=float,default=0.8)
    submit=sub.add_parser('submit');submit.add_argument('--coordinator',required=True);submit.add_argument('--file',required=True);submit.add_argument('--wait',action='store_true');submit.add_argument('--wait-timeout',type=float,default=15)
    status=sub.add_parser('status');status.add_argument('--coordinator',required=True);status.add_argument('--analysis-id',required=True)
    return p


def _query(addr,method,req,timeout=3):
    with grpc.insecure_channel(addr) as ch:
        stub=rpc.CoordinatorServiceStub(ch)
        return getattr(stub,method)(req,timeout=timeout)


def _print(message):
    print(json.dumps(MessageToDict(message,preserving_proto_field_name=True),ensure_ascii=False,indent=2))


def main(argv=None):
    args=parser().parse_args(argv)
    if args.command in ('coordinator','worker'):
        configure_logging()
        if args.command=='worker':
            if args.delay<0: raise SystemExit('delay must be >=0')
            serve_worker(args.id,args.bind,args.delay)
        else:
            peers=_peers(args.peers)
            if args.batch_size<1 or args.worker_timeout<=0 or args.election_timeout<=0:raise SystemExit('invalid batch size or timeout')
            serve_coordinator(args.id,args.bind,args.priority,peers,[x for x in args.workers.split(',') if x],args.batch_size,args.worker_timeout,args.election_timeout)
        return 0
    client=Node('cli')
    try:
        if args.command=='submit':
            with open(args.file,encoding='utf-8') as f:
                lines=[pb.LogLine(line_number=i,text=line.rstrip('\n')) for i,line in enumerate(f,1)]
            res=_query(args.coordinator,'SubmitLogs',pb.SubmitLogsRequest(meta=client.send(),source=args.file,lines=lines))
            client.receive(res.meta)
            _print(res)
            if args.wait:
                deadline=time.monotonic()+args.wait_timeout
                while time.monotonic()<deadline:
                    status=_query(args.coordinator,'GetAnalysisStatus',pb.GetAnalysisStatusRequest(meta=client.send(),analysis_id=res.analysis_id))
                    client.receive(status.meta)
                    if status.state in (pb.ANALYSIS_COMPLETED,pb.ANALYSIS_FAILED):
                        _print(status)
                        return 0 if status.state==pb.ANALYSIS_COMPLETED else 1
                    time.sleep(0.2)
                print('Timeout waiting for analysis',file=sys.stderr)
                return 1
            return 0
        status=_query(args.coordinator,'GetAnalysisStatus',pb.GetAnalysisStatusRequest(meta=client.send(),analysis_id=args.analysis_id))
        client.receive(status.meta)
        _print(status)
        return 0
    except (grpc.RpcError,OSError) as exc:
        if isinstance(exc,grpc.RpcError):
            print(f'gRPC {exc.code().name}: {exc.details()}',file=sys.stderr)
        else:print(str(exc),file=sys.stderr)
        return 1


if __name__=='__main__':raise SystemExit(main())
