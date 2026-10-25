import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from contextlib import contextmanager
import grpc
import pytest
from debugmesh.generated import debugmesh_pb2 as pb, debugmesh_pb2_grpc as rpc

ROOT=Path(__file__).resolve().parents[1]


def freeport():
    s=socket.socket();s.bind(('127.0.0.1',0));port=s.getsockname()[1];s.close();return port


@contextmanager
def processes(commands):
    env={**os.environ,'PYTHONPATH':str(ROOT/'src'),'PYTHONUNBUFFERED':'1'}
    ps=[]
    try:
        for cmd in commands:
            p=subprocess.Popen([sys.executable,'-m','debugmesh',*cmd],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,env=env)
            ps.append(p)
        yield ps
    finally:
        for p in ps:
            if p.poll() is None:p.terminate()
        for p in ps:
            try:p.wait(timeout=3)
            except subprocess.TimeoutExpired:p.kill();p.wait(timeout=3)


def ready(addr,timeout=4):
    with grpc.insecure_channel(addr) as ch:
        grpc.channel_ready_future(ch).result(timeout=timeout)


def submit(addr,lines):
    with grpc.insecure_channel(addr) as ch:
        return rpc.CoordinatorServiceStub(ch).SubmitLogs(pb.SubmitLogsRequest(meta=pb.Envelope(sender_id='pytest',logical_timestamp=2),source='integration',lines=[pb.LogLine(line_number=i,text=line) for i,line in enumerate(lines,1)]),timeout=3)


def status(addr,analysis_id):
    with grpc.insecure_channel(addr) as ch:
        return rpc.CoordinatorServiceStub(ch).GetAnalysisStatus(pb.GetAnalysisStatusRequest(meta=pb.Envelope(sender_id='pytest',logical_timestamp=3),analysis_id=analysis_id),timeout=3)


def wait_done(addr,analysis_id,timeout=8):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        s=status(addr,analysis_id)
        if s.state in (pb.ANALYSIS_COMPLETED,pb.ANALYSIS_FAILED): return s
        time.sleep(.05)
    pytest.fail('Analysis did not finish')


def test_multiworker_rpc_lamport_and_error_handling():
    a,b,c,co=[f'127.0.0.1:{freeport()}' for _ in range(4)]
    commands=[['worker','--id',name,'--bind',addr,'--delay','0.2'] for name,addr in [('A',a),('B',b),('C',c)]]
    commands += [['coordinator','--id','coord','--bind',co,'--priority','20','--workers',','.join([a,b,c]),'--batch-size','1']]
    with processes(commands):
        for addr in [a,b,c,co]:ready(addr)
        # Leader election is asynchronous; wait for startup.
        deadline=time.monotonic()+4
        while True:
            try:
                result=submit(co,['ModuleNotFoundError foo','FAILED tests/test_x.py','connection refused host'])
                break
            except grpc.RpcError as exc:
                if exc.code()!=grpc.StatusCode.FAILED_PRECONDITION or time.monotonic()>deadline:raise
                time.sleep(.1)
        s=wait_done(co,result.analysis_id)
        assert s.state==pb.ANALYSIS_COMPLETED and len(s.findings)==3
        assert {f.worker_id for f in s.findings}=={'A','B','C'}
        assert all(f.logical_timestamp>0 for f in s.findings)
        assert s.meta.logical_timestamp>result.meta.logical_timestamp
        with grpc.insecure_channel(co) as ch:
            stub=rpc.CoordinatorServiceStub(ch)
            with pytest.raises(grpc.RpcError) as ex:
                stub.SubmitLogs(pb.SubmitLogsRequest(meta=pb.Envelope(sender_id='pytest'),source='empty'),timeout=2)
            assert ex.value.code()==grpc.StatusCode.INVALID_ARGUMENT
            with pytest.raises(grpc.RpcError) as ex:
                stub.GetAnalysisStatus(pb.GetAnalysisStatusRequest(meta=pb.Envelope(sender_id='pytest'),analysis_id='unknown'),timeout=2)
            assert ex.value.code()==grpc.StatusCode.NOT_FOUND


def test_unavailable_worker_reports_failure():
    port=freeport();co=f'127.0.0.1:{port}';missing=f'127.0.0.1:{freeport()}'
    with processes([['coordinator','--id','coord','--bind',co,'--priority','20','--workers',missing,'--worker-timeout','0.3']]):
        ready(co)
        deadline=time.monotonic()+4
        while True:
            try:r=submit(co,['ERROR test failure']);break
            except grpc.RpcError as exc:
                if exc.code()!=grpc.StatusCode.FAILED_PRECONDITION or time.monotonic()>deadline:raise
                time.sleep(.1)
        s=wait_done(co,r.analysis_id)
        assert s.state==pb.ANALYSIS_FAILED
        assert 'UNAVAILABLE' in s.error or 'DEADLINE_EXCEEDED' in s.error


def test_bully_election_and_failover():
    high=f'127.0.0.1:{freeport()}';low=f'127.0.0.1:{freeport()}';worker=f'127.0.0.1:{freeport()}'
    cmds=[['worker','--id','worker','--bind',worker],
          ['coordinator','--id','high','--bind',high,'--priority','20','--peers',f'low@10@{low}','--workers',worker,'--election-timeout','0.3'],
          ['coordinator','--id','low','--bind',low,'--priority','10','--peers',f'high@20@{high}','--workers',worker,'--election-timeout','0.3']]
    with processes(cmds) as ps:
        for a in [high,low,worker]: ready(a)
        # Eventually high should be leader and low should reject writes.
        deadline=time.monotonic()+9
        while True:
            try:
                accepted=submit(high,['FAILED tests/test_y.py'])
                with pytest.raises(grpc.RpcError) as err:submit(low,['FAILED tests/test_z.py'])
                if err.value.code()==grpc.StatusCode.FAILED_PRECONDITION:break
            except grpc.RpcError:pass
            if time.monotonic()>deadline:pytest.fail('High priority leader did not converge')
            time.sleep(.15)
        assert wait_done(high,accepted.analysis_id).state==pb.ANALYSIS_COMPLETED
        ps[1].terminate();ps[1].wait(timeout=3)
        deadline=time.monotonic()+9
        while True:
            try:
                r=submit(low,['ERROR compilation failed'])
                break
            except grpc.RpcError as exc:
                if exc.code()!=grpc.StatusCode.FAILED_PRECONDITION or time.monotonic()>deadline:raise
                time.sleep(.1)
        assert wait_done(low,r.analysis_id).state==pb.ANALYSIS_COMPLETED
