from fastapi.middleware.cors import CORSMiddleware
origins = [
    "http://localhost:5173",   # React app
]
def setup_cors(app):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,  # change in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )