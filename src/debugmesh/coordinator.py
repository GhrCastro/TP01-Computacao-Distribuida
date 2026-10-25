"""In-memory coordinator, RPC scheduler and simple Bully election demonstration.

No quorum/consensus or state replication is implemented (Entrega 2 scope).
"""
import logging
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
import grpc
from .common import Node
from .generated import debugmesh_pb2 as pb, debugmesh_pb2_grpc as rpc

LOG=logging.getLogger('debugmesh.coordinator')


class Coordinator(Node, rpc.CoordinatorServiceServicer, rpc.ElectionServiceServicer):
    def __init__(self, node_id, address, priority, peers, workers, batch_size=3, worker_timeout=3.0, election_timeout=1.0):
        super().__init__(node_id)
        self.address=address
        self.priority=priority
        self.peers=peers  # list of (node_id, priority, address)
        self.workers=workers  # list of network addresses
        self.batch_size=batch_size
        self.worker_timeout=worker_timeout
        self.election_timeout=election_timeout
        self._lock=threading.RLock()
        self._election_lock=threading.Lock()
        self._leader_event=threading.Event()
        self.leader=None
        self.leader_priority=-1
        self._jobs={}
        self._pool=ThreadPoolExecutor(max_workers=max(8,len(workers)*2+2))
        self._stop=threading.Event()

    def _peer(self, address):
        return rpc.ElectionServiceStub(grpc.insecure_channel(address))

    def _leader_address(self):
        return self.address if self.leader==self.node_id else next((addr for nid,_,addr in self.peers if nid==self.leader),None)

    def _check_leader(self, context):
        with self._lock:
            if self.leader!=self.node_id:
                context.abort(grpc.StatusCode.FAILED_PRECONDITION, f'Not leader; leader={self._leader_address() or "unknown"}')

    def SubmitLogs(self, request, context):
        if not request.meta.sender_id or not request.source or not request.lines:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, 'sender_id, source and nonempty lines required')
        self.receive(request.meta)
        self._check_leader(context)
        analysis_id=str(uuid.uuid4())
        lines=list(request.lines)
        with self._lock:
            self._jobs[analysis_id]={'state':pb.ANALYSIS_PENDING,'findings':[],'error':''}
        self._pool.submit(self._process,analysis_id,lines)
        self.event('accepted',analysis_id=analysis_id,line_count=len(lines))
        return pb.SubmitLogsResponse(meta=self.send(request.meta.request_id),analysis_id=analysis_id,state=pb.ANALYSIS_PENDING)

    def GetAnalysisStatus(self, request, context):
        if not request.analysis_id or not request.meta.sender_id:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT,'analysis_id and sender_id required')
        self.receive(request.meta)
        self._check_leader(context)
        with self._lock:
            job=self._jobs.get(request.analysis_id)
            if job is None:
                context.abort(grpc.StatusCode.NOT_FOUND,'Analysis not found')
            return pb.GetAnalysisStatusResponse(meta=self.send(request.meta.request_id),analysis_id=request.analysis_id, state=job['state'], findings=list(job['findings']),error=job['error'])

    def _process(self,analysis_id,lines):
        with self._lock: self._jobs[analysis_id]['state']=pb.ANALYSIS_RUNNING
        if not self.workers:
            with self._lock:self._jobs[analysis_id].update(state=pb.ANALYSIS_FAILED,error='No workers configured')
            return
        batches=[lines[i:i+self.batch_size] for i in range(0,len(lines),self.batch_size)]
        futures={}
        for i,batch in enumerate(batches):
            addr=self.workers[i%len(self.workers)]
            task_id=f'{analysis_id}:{i}'
            futures[self._pool.submit(self._send_task,addr,task_id,analysis_id,batch)]=(task_id,addr)
        findings=[]; errors=[]
        for future in as_completed(futures):
            task_id,addr=futures[future]
            try:
                result=future.result()
                findings.extend(result)
                self.event('task_result',task_id=task_id,worker=addr,findings=len(result))
            except grpc.RpcError as exc:
                errors.append(f'{task_id} -> {addr}: {exc.code().name}')
            except Exception as exc:
                errors.append(f'{task_id} -> {addr}: {type(exc).__name__}')
        findings.sort(key=lambda x: (x.task_id, x.evidence[0] if x.evidence else ''))
        with self._lock:
            self._jobs[analysis_id].update(findings=findings,error='; '.join(errors),state=pb.ANALYSIS_FAILED if errors else pb.ANALYSIS_COMPLETED)
        self.event('analysis_done',analysis_id=analysis_id,findings=len(findings),errors=len(errors))

    def _send_task(self,address,task_id,analysis_id,lines):
        with grpc.insecure_channel(address) as ch:
            stub=rpc.WorkerServiceStub(ch)
            req=pb.AssignTaskRequest(meta=self.send(),analysis_id=analysis_id,task_id=task_id,attempt=1,lines=lines)
            reply=stub.AssignTask(req,timeout=self.worker_timeout)
            self.receive(reply.meta)
            return list(reply.findings)

    # Election is intentionally not distributed consensus. Safety requires healthy LAN.
    def Election(self,request,context):
        if not request.meta.sender_id:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT,'sender_id required')
        self.receive(request.meta)
        higher=self.priority>request.candidate_priority
        if higher and not self._stop.is_set():
            # No new thread per request if election already running.
            threading.Thread(target=self.run_election,daemon=True).start()
        return pb.ElectionResponse(meta=self.send(request.meta.request_id),higher_priority_alive=higher)

    def AnnounceLeader(self,request,context):
        if not request.leader_id or not request.meta.sender_id:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT,'leader_id and sender_id required')
        self.receive(request.meta)
        known={nid:p for nid,p,_ in self.peers}
        known[self.node_id]=self.priority
        if request.leader_id not in known or known[request.leader_id]!=request.leader_priority:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT,'Unknown leader identity or priority')
        with self._lock:
            self.leader=request.leader_id
            self.leader_priority=request.leader_priority
            self._leader_event.set()
        self.event('leader_announced',leader=self.leader)
        return pb.Ack(meta=self.send(request.meta.request_id),accepted=True)

    def run_election(self):
        if not self._election_lock.acquire(blocking=False):
            return
        try:
            self._leader_event.clear()
            with self._lock:
                self.leader=None
                self.leader_priority=-1
            higher=[]
            for nid,priority,addr in self.peers:
                if priority<=self.priority:continue
                try:
                    with grpc.insecure_channel(addr) as ch:
                        rep=rpc.ElectionServiceStub(ch).Election(pb.ElectionRequest(meta=self.send(),candidate_priority=self.priority),timeout=self.election_timeout)
                    self.receive(rep.meta)
                    if rep.higher_priority_alive:higher.append(nid)
                except grpc.RpcError:pass
            if higher:
                self.event('waiting_higher',higher=higher)
                self._leader_event.wait(timeout=self.election_timeout*2)
                if self._leader_event.is_set():return
                # No announcement; monitoring will trigger another election.
                return
            with self._lock:
                self.leader=self.node_id
                self.leader_priority=self.priority
                self._leader_event.set()
            self.event('elected',leader=self.node_id)
            for nid,_,addr in self.peers:
                try:
                    with grpc.insecure_channel(addr) as ch:
                        ack=rpc.ElectionServiceStub(ch).AnnounceLeader(pb.LeaderAnnouncement(meta=self.send(),leader_id=self.node_id,leader_priority=self.priority,term=self.clock.value),timeout=self.election_timeout)
                    self.receive(ack.meta)
                except grpc.RpcError:pass
        finally:
            self._election_lock.release()

    def monitor(self):
        while not self._stop.wait(0.6):
            if not self._election_lock.locked():
                with self._lock:
                    leader=self.leader
                    addr=self._leader_address()
                if leader==self.node_id: continue
                if not leader or not addr:
                    self.run_election()
                    continue
                try:
                    with grpc.insecure_channel(addr) as ch:
                        grpc.channel_ready_future(ch).result(timeout=self.election_timeout)
                except grpc.FutureTimeoutError:
                    self.event('leader_unreachable',leader=leader)
                    self.run_election()

    def close(self):
        self._stop.set()
        self._pool.shutdown(wait=False,cancel_futures=True)


def serve_coordinator(node_id,address,priority,peers,workers,batch_size=3,worker_timeout=3,election_timeout=0.8):
    c=Coordinator(node_id,address,priority,peers,workers,batch_size,worker_timeout,election_timeout)
    server=grpc.server(ThreadPoolExecutor(max_workers=16))
    rpc.add_CoordinatorServiceServicer_to_server(c,server)
    rpc.add_ElectionServiceServicer_to_server(c,server)
    if not server.add_insecure_port(address):
        raise RuntimeError('Unable to bind coordinator '+address)
    server.start()
    c.event('listening',address=address,priority=priority)
    threading.Thread(target=c.monitor,daemon=True).start()
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        c.close();server.stop(grace=2).wait()
