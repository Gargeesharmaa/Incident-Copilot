from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import Base, engine, get_db
from app.models import AlertRecord, Incident

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Incident Copilot")

DEDUPE_WINDOW = timedelta(minutes=15)


class Alert(BaseModel):
    service: str
    alert: str
    value: str | float
    threshold: str | float


def find_or_create_incident(db: Session, alert: Alert):
    """Return (incident, is_new)."""
    now = datetime.now(timezone.utc)
    cutoff = now - DEDUPE_WINDOW

    incident = db.scalars(
        select(Incident)
        .where(
            Incident.service == alert.service,
            Incident.title == alert.alert,
            Incident.status == "open",
            Incident.last_seen >= cutoff,
        )
        .order_by(Incident.last_seen.desc())
    ).first()

    if incident:
        incident.alert_count += 1
        incident.last_seen = now
        return incident, False

    incident = Incident(service=alert.service, title=alert.alert)
    db.add(incident)
    db.flush()  # gives the incident an id without committing yet
    return incident, True


@app.get("/")
def health():
    return {"status": "ok"}


@app.post("/webhook/alert")
def receive_alert(alert: Alert, db: Session = Depends(get_db)):
    incident, is_new = find_or_create_incident(db, alert)

    record = AlertRecord(
        service=alert.service,
        alert=alert.alert,
        value=str(alert.value),
        threshold=str(alert.threshold),
        incident_id=incident.id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "status": "saved",
        "alert_id": record.id,
        "incident_id": incident.id,
        "new_incident": is_new,
    }


def incident_to_dict(i: Incident):
    return {
        "id": i.id,
        "service": i.service,
        "title": i.title,
        "status": i.status,
        "alert_count": i.alert_count,
        "first_seen": i.first_seen,
        "last_seen": i.last_seen,
    }


@app.get("/incidents")
def list_incidents(db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Incident).order_by(Incident.last_seen.desc()).limit(50)
    ).all()
    return [incident_to_dict(r) for r in rows]


@app.get("/incidents/{incident_id}")
def get_incident(incident_id: int, db: Session = Depends(get_db)):
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    data = incident_to_dict(incident)
    data["alerts"] = [
        {"id": a.id, "value": a.value, "threshold": a.threshold, "created_at": a.created_at}
        for a in incident.alerts
    ]
    return data


@app.post("/incidents/{incident_id}/resolve")
def resolve_incident(incident_id: int, db: Session = Depends(get_db)):
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    incident.status = "resolved"
    db.commit()
    return {"status": "resolved", "id": incident_id}


@app.get("/alerts")
def list_alerts(db: Session = Depends(get_db)):
    rows = db.scalars(
        select(AlertRecord).order_by(AlertRecord.id.desc()).limit(50)
    ).all()
    return [
        {
            "id": r.id,
            "incident_id": r.incident_id,
            "service": r.service,
            "alert": r.alert,
            "value": r.value,
            "threshold": r.threshold,
            "created_at": r.created_at,
        }
        for r in rows
    ]