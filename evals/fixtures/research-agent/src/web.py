"""Web UI backend. oauth2-proxy sits in front and sets X-Forwarded-Email."""
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from src.agent import RunLimitReached, run
from src.render import render_brief

app = FastAPI()


class Question(BaseModel):
    question: str = Field(min_length=3, max_length=2000)


@app.post("/ask", response_class=HTMLResponse)
def ask(q: Question, x_forwarded_email: str = Header(...)):
    if not x_forwarded_email.endswith("@northwind.example"):
        raise HTTPException(status_code=403)
    try:
        brief = run(q.question, user=x_forwarded_email)
    except RunLimitReached as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    return render_brief(brief)
