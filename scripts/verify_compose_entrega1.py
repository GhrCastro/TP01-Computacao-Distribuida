"""End-to-end verification of Entrega 1 on a Docker Compose virtual network.

Run from the repository root after `docker compose up --build -d`.
All traffic uses real gRPC sockets; JSON, container logs and results are saved.
This does not claim to test distinct physical hosts.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import grpc
from google.protobuf.json_format import MessageToDict
from debugmesh.generated import debugmesh_pb2 as pb
from debugmesh.generated import debugmesh_pb2_grpc as rpc

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "artifacts" / "entrega1-compose"
EVIDENCE.mkdir(parents=True, exist_ok=True)
ADDR_A = "127.0.0.1:50051"
ADDR_B = "127.0.0.1:50052"
SAMPLE = ROOT / "samples" / "ci_pipeline.log"
LINES = [
    pb.LogLine(line_number=i, text=line.rstrip("\n"))
    for i, line in enumerate(SAMPLE.read_text(encoding="utf-8").splitlines(keepends=True), 1)
]
results = {"scenario": "Docker Compose: 2 coordinators + 3 workers", "checks": []}


def record(name: str, **details: object) -> None:
    results["checks"].append({"check": name, "passed": True, **details})
    print(f"PASS: {name}", flush=True)


def compose(*args: str) -> str:
    done = subprocess.run(
        ["docker", "compose", *args], cwd=ROOT, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=90,
        check=True,
    )
    print(done.stdout[-4000:], flush=True)
    return done.stdout


def rpc_call(address: str, method: str, request: object) -> object:
    with grpc.insecure_channel(address) as channel:
        return getattr(rpc.CoordinatorServiceStub(channel), method)(request, timeout=3)


def envelope() -> pb.Envelope:
    return pb.Envelope(sender_id="ci-compose", logical_timestamp=1)


def submit(address: str) -> pb.SubmitLogsResponse:
    return rpc_call(address, "SubmitLogs", pb.SubmitLogsRequest(
        meta=envelope(), source="samples/ci_pipeline.log", lines=LINES
    ))


def status(address: str, analysis_id: str) -> pb.GetAnalysisStatusResponse:
    return rpc_call(address, "GetAnalysisStatus", pb.GetAnalysisStatusRequest(
        meta=envelope(), analysis_id=analysis_id
    ))


def submit_eventually(address: str, timeout: float = 30) -> pb.SubmitLogsResponse:
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        try:
            return submit(address)
        except grpc.RpcError as exc:
            last = exc
            if exc.code() not in (
                grpc.StatusCode.FAILED_PRECONDITION,
                grpc.StatusCode.UNAVAILABLE,
                grpc.StatusCode.DEADLINE_EXCEEDED,
            ):
                raise
            time.sleep(0.25)
    raise AssertionError(f"{address} did not accept submissions: {last}")


def wait_done(address: str, analysis_id: str, timeout: float = 20) -> pb.GetAnalysisStatusResponse:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = status(address, analysis_id)
        if response.state in (pb.ANALYSIS_COMPLETED, pb.ANALYSIS_FAILED):
            return response
        time.sleep(0.2)
    raise AssertionError(f"Analysis {analysis_id} on {address} did not finish")


def assert_follower(address: str, timeout: float = 15) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            status(address, "not-a-real-analysis")
        except grpc.RpcError as exc:
            if exc.code() == grpc.StatusCode.FAILED_PRECONDITION:
                return
            if exc.code() not in (grpc.StatusCode.NOT_FOUND, grpc.StatusCode.UNAVAILABLE,
                                  grpc.StatusCode.DEADLINE_EXCEEDED):
                raise
        time.sleep(0.25)
    raise AssertionError(f"{address} did not converge as follower")


def assert_completed(result: pb.GetAnalysisStatusResponse, label: str) -> None:
    assert result.state == pb.ANALYSIS_COMPLETED, f"{label}: {result.error}"
    workers = {finding.worker_id for finding in result.findings}
    assert workers == {"worker-a", "worker-b", "worker-c"}, (label, workers)
    assert len(result.findings) == 6, (label, len(result.findings))
    assert all(0 < f.logical_timestamp < result.meta.logical_timestamp for f in result.findings)
    assert not result.error
    record(label, workers=sorted(workers), findings=len(result.findings),
           logical_timestamp=result.meta.logical_timestamp)
    (EVIDENCE / f"{label}.json").write_text(
        json.dumps(MessageToDict(result, preserving_proto_field_name=True),
                   indent=2, ensure_ascii=False), encoding="utf-8")


def validate_event_logs(raw: str) -> None:
    events = []
    for line in raw.splitlines():
        start = line.find('{"node":')
        if start >= 0:
            try:
                events.append(json.loads(line[start:]))
            except json.JSONDecodeError:
                pass
    assert events, "No structured container events were captured"
    assert any(e.get("node") == "coordinator-a" and e.get("event") == "elected" for e in events), "No A election"
    assert any(e.get("node") == "coordinator-b" and e.get("event") == "leader_unreachable" for e in events), "No leader failure detection"
    assert any(e.get("node") == "coordinator-b" and e.get("event") == "elected" for e in events), "No B election"
    finished = {e.get("node") for e in events if e.get("event") == "task_done"}
    assert {"worker-a", "worker-b", "worker-c"}.issubset(finished), finished
    receptions = [e for e in events if e.get("event") == "receive"]
    assert receptions, "No Lamport receive events found"
    assert all(e["logical_timestamp"] > e["remote_timestamp"] for e in receptions), "Lamport receive rule violated"
    record("event_logs_election_worker_activity_and_lamport",
           structured_events=len(events), receive_events=len(receptions))


def collect_logs() -> str:
    for args, filename in [
        (("logs", "--no-color", "--timestamps"), "docker-compose.log"),
        (("ps", "--all"), "compose-ps.txt"),
    ]:
        try:
            completed = subprocess.run(
                ["docker", "compose", *args], cwd=ROOT, capture_output=True,
                text=True, timeout=30, check=False
            )
            (EVIDENCE / filename).write_text(
                completed.stdout + "\n" + completed.stderr, encoding="utf-8"
            )
        except Exception as exc:
            (EVIDENCE / filename).write_text(repr(exc), encoding="utf-8")
    return (EVIDENCE / "docker-compose.log").read_text(encoding="utf-8")


def main() -> None:
    assert len(LINES) == 12, f"Unexpected sample size: {len(LINES)}"
    submit_eventually(ADDR_A)
    assert_follower(ADDR_B)
    record("initial_election_A_leader_B_follower")

    initial = submit_eventually(ADDR_A)
    assert_completed(wait_done(ADDR_A, initial.analysis_id), "three_workers_before_failover")

    compose("stop", "worker-b")
    offline = submit_eventually(ADDR_A)
    offline_status = wait_done(ADDR_A, offline.analysis_id)
    assert offline_status.state == pb.ANALYSIS_FAILED, offline_status.state
    assert "UNAVAILABLE" in offline_status.error or "DEADLINE_EXCEEDED" in offline_status.error, offline_status.error
    record("worker_offline_is_reported_as_failed", error=offline_status.error)
    compose("start", "worker-b")

    compose("stop", "coordinator-a")
    recovered = submit_eventually(ADDR_B)
    assert_completed(wait_done(ADDR_B, recovered.analysis_id), "three_workers_after_failover")
    record("leader_failover_to_B")

    compose("start", "coordinator-a")
    submit_eventually(ADDR_A)
    assert_follower(ADDR_B)
    record("higher_priority_A_reclaims_leadership")

    raw = collect_logs()
    validate_event_logs(raw)


if __name__ == "__main__":
    try:
        main()
        results["passed"] = True
    except Exception as exc:
        results["passed"] = False
        results["error"] = f"{type(exc).__name__}: {exc}"
        print(f"FAIL: {results['error']}", file=sys.stderr, flush=True)
        raise
    finally:
        collect_logs()
        (EVIDENCE / "summary.json").write_text(
            json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
        )
