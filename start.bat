@echo off
echo Starting Yuewang Goujian Chat MVP...
python -m uvicorn main:app --host 0.0.0.0 --port 8001
pause