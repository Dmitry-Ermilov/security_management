import os
import uuid
from datetime import datetime, UTC
from typing import Any, Optional

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Boolean, Column, DateTime, Integer, JSON, String, create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, declarative_base, sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./security.db",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


class DeviceModel(Base):
    __tablename__ = "devices"

    id = Column(String, primary_key=True)
    cert = Column(String, nullable=True)
    status = Column(String, nullable=True)
    last_seen = Column(DateTime, nullable=True)


class PolicyModel(Base):
    __tablename__ = "policies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    conditions = Column(JSON, nullable=False, default=dict)
    actions = Column(JSON, nullable=False, default=dict)
    enabled = Column(Boolean, nullable=False, default=True)


class AlertModel(Base):
    __tablename__ = "alerts"

    id = Column(String, primary_key=True)
    source = Column(String, nullable=False)
    rule_id = Column(String, nullable=False)
    severity = Column(Integer, nullable=False)
    data = Column(JSON, nullable=False, default=dict)
    decision = Column(JSON, nullable=True)
    processed = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False)


class DeviceIn(BaseModel):
    id: str
    cert: Optional[str] = None
    status: Optional[str] = None


class DeviceOut(DeviceIn):
    last_seen: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PolicyIn(BaseModel):
    name: str
    conditions: dict = Field(default_factory=dict)
    actions: Any = Field(default_factory=dict)
    enabled: bool = True


class PolicyOut(PolicyIn):
    id: int

    model_config = ConfigDict(from_attributes=True)


class AlertIn(BaseModel):
    source: str
    rule_id: str
    severity: int = Field(ge=0, le=10)
    data: dict = Field(default_factory=dict)


class AlertOut(AlertIn):
    id: str
    created_at: datetime
    processed: bool
    decision: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)


class RthRequest(BaseModel):
    drone_id: str
    mode: str = "RTL"


app = FastAPI(title="Security API")


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def normalize_actions(actions: Any) -> list[dict]:
    if actions is None:
        return []
    if isinstance(actions, list):
        return [a for a in actions if isinstance(a, dict)]
    if isinstance(actions, dict):
        return [actions]
    return []


def policy_matches(alert: AlertIn, conditions: dict) -> bool:
    severity_gte = conditions.get("severity_gte")
    if severity_gte is not None and alert.severity < severity_gte:
        return False

    severity_lte = conditions.get("severity_lte")
    if severity_lte is not None and alert.severity > severity_lte:
        return False

    source_in = conditions.get("source_in")
    if source_in and alert.source not in source_in:
        return False

    rule_id_in = conditions.get("rule_id_in")
    if rule_id_in and alert.rule_id not in rule_id_in:
        return False

    return True


def evaluate_policies(alert: AlertIn, db: Session) -> list[dict]:
    actions: list[dict] = []
    policies = db.query(PolicyModel).filter(PolicyModel.enabled.is_(True)).all()

    for policy in policies:
        if not policy_matches(alert, policy.conditions or {}):
            continue
        for action in normalize_actions(policy.actions):
            action_with_meta = dict(action)
            action_with_meta.setdefault("policy", policy.name)
            actions.append(action_with_meta)

    return actions


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    db.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.get("/devices", response_model=list[DeviceOut])
def list_devices(db: Session = Depends(get_db)) -> list[DeviceModel]:
    return db.query(DeviceModel).all()


@app.post("/devices", response_model=DeviceOut)
def create_device(device: DeviceIn, db: Session = Depends(get_db)) -> DeviceModel:
    model = DeviceModel(id=device.id, cert=device.cert, status=device.status)
    db.add(model)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Device already exists")
    db.refresh(model)
    return model


@app.post("/devices/{device_id}/heartbeat", response_model=DeviceOut)
def device_heartbeat(
    device_id: str,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
) -> DeviceModel:
    model = db.get(DeviceModel, device_id)
    if not model:
        raise HTTPException(status_code=404, detail="Device not found")
    if status is not None:
        model.status = status
    model.last_seen = datetime.now(UTC)
    db.commit()
    db.refresh(model)
    return model


@app.get("/policies", response_model=list[PolicyOut])
def list_policies(db: Session = Depends(get_db)) -> list[PolicyModel]:
    return db.query(PolicyModel).all()


@app.post("/policies", response_model=PolicyOut)
def create_policy(policy: PolicyIn, db: Session = Depends(get_db)) -> PolicyModel:
    model = PolicyModel(
        name=policy.name,
        conditions=policy.conditions,
        actions=policy.actions,
        enabled=policy.enabled,
    )
    db.add(model)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Policy name already exists")
    db.refresh(model)
    return model


@app.get("/alerts", response_model=list[AlertOut])
def list_alerts(db: Session = Depends(get_db)) -> list[AlertModel]:
    return db.query(AlertModel).order_by(AlertModel.created_at.desc()).all()


@app.post("/alerts", response_model=AlertOut)
def receive_alert(alert: AlertIn, db: Session = Depends(get_db)) -> AlertModel:
    model = AlertModel(
        id=str(uuid.uuid4()),
        source=alert.source,
        rule_id=alert.rule_id,
        severity=alert.severity,
        data=alert.data,
        created_at=datetime.now(UTC),
        processed=False,
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


@app.post("/alerts/process", response_model=AlertOut)
def process_alert(alert: AlertIn, db: Session = Depends(get_db)) -> AlertModel:
    actions = evaluate_policies(alert, db)
    model = AlertModel(
        id=str(uuid.uuid4()),
        source=alert.source,
        rule_id=alert.rule_id,
        severity=alert.severity,
        data=alert.data,
        decision={"actions": actions},
        created_at=datetime.now(UTC),
        processed=True,
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


@app.post("/actions/rth")
def action_rth(payload: RthRequest) -> dict:
    # stub: call GCS/FCU, here we just return intent
    return {"drone_id": payload.drone_id, "mode": payload.mode, "status": "sent"}
