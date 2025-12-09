from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="Security API")

devices = {}
policies = {}

class Device(BaseModel):
    id: str
    cert: Optional[str] = None
    status: Optional[str] = None

class Policy(BaseModel):
    name: str
    conditions: dict
    actions: dict

class Alert(BaseModel):
    source: str
    rule_id: str
    severity: int
    data: dict

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/devices", response_model=List[Device])
def list_devices():
    return list(devices.values())

@app.post("/devices", response_model=Device)
def create_device(device: Device):
    devices[device.id] = device
    return device

@app.get("/policies", response_model=List[Policy])
def list_policies():
    return list(policies.values())

@app.post("/policies", response_model=Policy)
def create_policy(policy: Policy):
    policies[policy.name] = policy
    return policy

@app.post("/alerts")
def receive_alert(alert: Alert):
    # stub: here integrate TheHive/Cortex
    return {"received": alert.rule_id, "severity": alert.severity}

@app.post("/actions/rth")
def action_rth(drone_id: str, mode: str = "RTL"):
    # stub: call GCS/FCU
    return {"drone_id": drone_id, "mode": mode, "status": "sent"}
