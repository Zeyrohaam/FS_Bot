from .miniapp_backend import app
from config import BACKEND_HOST, BACKEND_PORT
import uvicorn

if __name__ == '__main__':
    uvicorn.run(app, host=BACKEND_HOST, port=BACKEND_PORT, reload=False)
