@echo off
REM One-click: builds two separate Python environments (the two models need different
REM library versions), then makes all 6 clone files in output\. Safe to run again.
cd /d "%~dp0"

where py >nul 2>nul || (echo Python launcher "py" not found. Install Python 3.11 from python.org first. & pause & exit /b 1)
where git >nul 2>nul || (echo git not found. Install Git for Windows first. & pause & exit /b 1)

echo.
echo === 1/2  Chatterbox (English) ===
if not exist venv-chatterbox py -3.11 -m venv venv-chatterbox
call venv-chatterbox\Scripts\activate.bat
python -m pip install -q --upgrade pip
python -m pip install -q torch==2.6.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu124
python -m pip install -q chatterbox-tts
python -c "import torch; assert torch.cuda.is_available(), 'CPU-only torch got installed'; print('GPU ok:', torch.cuda.get_device_name(0))" || (echo See README "If something fails". & pause & exit /b 1)
python clone_local.py en
call deactivate

echo.
echo === 2/2  IndicF5 (Hindi + Kannada) ===
if not exist venv-indicf5 py -3.11 -m venv venv-indicf5
call venv-indicf5\Scripts\activate.bat
python -m pip install -q --upgrade pip
python -m pip install -q torch torchaudio --index-url https://download.pytorch.org/whl/cu124
python -m pip install -q git+https://github.com/ai4bharat/IndicF5.git soundfile
python -c "import torch; assert torch.cuda.is_available(), 'CPU-only torch got installed'; print('GPU ok:', torch.cuda.get_device_name(0))" || (echo See README "If something fails". & pause & exit /b 1)
python clone_local.py indic
call deactivate

echo.
echo Finished. Listen to the files in output\, then zip the output folder as clones_return.zip.
dir /b output
pause
