from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.ingest import load_comps
from app.estimate import estimate_market_rent
from app.models import TargetAsset


app = FastAPI(
    title="Market Rent Engine",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/v1/market-rent/estimate")
def estimate_market_rent_endpoint(target: TargetAsset):
    try:
        used_comps, dropped_comps = load_comps(target)

        estimate = estimate_market_rent(
            target=target,
            used_comps=used_comps,
            dropped_comps=dropped_comps,
        )

        return estimate

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
