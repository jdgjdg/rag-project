@echo off
echo Starting RAG Project...

:: Start FastAPI in a new terminal
start "FastAPI" cmd /k "cd /d "C:\Users\sacha\RiceLocal\RAG project" && "C:\Users\sacha\RiceLocal\RAG project\.venv\Scripts\activate.bat" && uvicorn api:app --reload"

:: Wait a few seconds for FastAPI to start
timeout /t 5 /nobreak

:: Start Angular in a new terminal
start "Angular" cmd /k "cd /d "C:\Users\sacha\RiceLocal\RAG project\frontend\chat" && npm start"

:: Wait for Angular to compile then open browser
timeout /t 10 /nobreak
start http://localhost:4200