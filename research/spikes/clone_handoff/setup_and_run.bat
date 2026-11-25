@echo off
REM v2: stops at the first failure and saves everything to run_log.txt (send that file back).
setlocal
cd /d "%~dp0"
set LOG=%~dp0run_log.txt
echo Run started %date% %time% > "%LOG%"

if not exist "%~dp0clone_local.py" (
  echo ERROR: clone_local.py is not next to this file.
  echo You probably opened the .bat from INSIDE the zip. Right-click the zip, "Extract All", then run the .bat from the extracted folder.
  echo ERROR: run from inside the zip >> "%LOG%"
  pause & exit /b 1
)

echo [check] Python 3.11 ...
py -3.11 -c "import sys; print(sys.version)" >> "%LOG%" 2>&1 || (
  echo ERROR: Python 3.11 not found. Installed versions:
  py -0
  py -0 >> "%LOG%" 2>&1
  echo Install Python 3.11 from python.org ^(tick "Add python.exe to PATH"^), then run this again.
  pause & exit /b 1
)
echo [check] NVIDIA GPU ...
nvidia-smi >> "%LOG%" 2>&1 || (echo ERROR: nvidia-smi failed - NVIDIA driver missing? & pause & exit /b 1)
where git >> "%LOG%" 2>&1 || (echo ERROR: git not found. Install Git for Windows. & pause & exit /b 1)

echo.
echo === 1/2  Chatterbox (English) - first run downloads a few GB, be patient ===
if not exist venv-chatterbox\Scripts\python.exe py -3.11 -m venv venv-chatterbox >> "%LOG%" 2>&1
set PY=venv-chatterbox\Scripts\python.exe
if not exist %PY% (echo ERROR: could not create venv-chatterbox. See run_log.txt & pause & exit /b 1)
echo [1/4] pip ... & %PY% -m pip install --upgrade pip >> "%LOG%" 2>&1
echo [2/4] torch with CUDA ... & %PY% -m pip install torch==2.6.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu124 >> "%LOG%" 2>&1 || (echo ERROR installing torch. See run_log.txt & pause & exit /b 1)
echo [3/4] chatterbox-tts ... & %PY% -m pip install chatterbox-tts >> "%LOG%" 2>&1 || (echo ERROR installing chatterbox-tts. See run_log.txt & pause & exit /b 1)
%PY% -c "import torch; assert torch.cuda.is_available(), 'CPU-only torch'; print('GPU ok:', torch.cuda.get_device_name(0))" >> "%LOG%" 2>&1 || (echo ERROR: torch cannot see the GPU. See run_log.txt & pause & exit /b 1)
echo [4/4] generating English clones ... & %PY% clone_local.py en >> "%LOG%" 2>&1 || (echo ERROR generating English. See run_log.txt & pause & exit /b 1)

echo.
echo === 2/2  IndicF5 (Hindi + Kannada) ===
if not exist venv-indicf5\Scripts\python.exe py -3.11 -m venv venv-indicf5 >> "%LOG%" 2>&1
set PY=venv-indicf5\Scripts\python.exe
if not exist %PY% (echo ERROR: could not create venv-indicf5. See run_log.txt & pause & exit /b 1)
echo [1/4] pip ... & %PY% -m pip install --upgrade pip >> "%LOG%" 2>&1
echo [2/4] torch with CUDA ... & %PY% -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124 >> "%LOG%" 2>&1 || (echo ERROR installing torch. See run_log.txt & pause & exit /b 1)
echo [3/4] IndicF5 ... & %PY% -m pip install git+https://github.com/ai4bharat/IndicF5.git soundfile >> "%LOG%" 2>&1 || (echo ERROR installing IndicF5. See run_log.txt & pause & exit /b 1)
%PY% -c "import torch; assert torch.cuda.is_available(), 'CPU-only torch'; print('GPU ok:', torch.cuda.get_device_name(0))" >> "%LOG%" 2>&1 || (echo ERROR: torch cannot see the GPU. See run_log.txt & pause & exit /b 1)
echo [4/4] generating Hindi + Kannada clones ... & %PY% clone_local.py indic >> "%LOG%" 2>&1 || (echo ERROR generating Hindi/Kannada. See run_log.txt - maybe the Hugging Face login step in README & pause & exit /b 1)

echo.
echo DONE. Files in output:
dir /b output
echo Listen to them, then zip the output folder ^(with run_log.txt copied into it^) as clones_return.zip.
pause
