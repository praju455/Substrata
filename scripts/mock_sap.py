"""Local OData-shaped development fixture, explicitly synthetic and unaffiliated."""

from fastapi import FastAPI, HTTPException

from substrata.platform.seeds import generate

app = FastAPI(title="Synthetic OData development mock; no SAP affiliation")


@app.get("/odata/{resource}")
def resource(resource: str, industry: str = "automotive"):
    fixture = generate(industry).model_dump(mode="json")
    if resource not in fixture:
        raise HTTPException(404, "Unknown fixture resource.")
    return {
        "@odata.context": "synthetic://local-mock",
        "synthetic": True,
        "value": fixture[resource],
    }
