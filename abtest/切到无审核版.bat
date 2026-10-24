@echo off
chcp 936 >nul
cd /d "D:\Strata\Strata-main"
echo [1/5] 正在停止 Strata（也就是关掉助手本人）...
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":8080" ^| findstr "LISTENING"') do taskkill /F /PID %%p >nul 2>nul
taskkill /F /IM strata.exe >nul 2>nul
taskkill /F /IM strata-vision.exe >nul 2>nul
timeout /t 6 /nobreak >nul
echo [2/5] 正在建 pack：要读 44 GB，约 10 到 20 分钟，窗口别关 ...
".venv\Scripts\python.exe" "D:\Strata\Strata-main\tools\iq_pack.py" --gguf "D:\Strata\Strata-data\models\sc117_iq3_xxs\Qwen3.8-Flash-Next-GSQ-RCO-abliterated-IQ3_XXS-00001-of-00002.gguf" --out "D:\Strata\Strata-data\packs\sc117_iq3_xxs"
if errorlevel 1 goto PACKFAIL
echo [3/5] pack 建好，正在切换配置（改前自动备份）...
".venv\Scripts\python.exe" "E:\Desktop\aigz\strata-bench\abtest\switch_config.py" --to sc117
if errorlevel 1 goto SWFAIL
echo [4/5] 正在启动 Strata（无审核版模型）。窗口会一直开着，代表引擎正在跑
"D:\Strata\Strata-main\serve\server.py" --engine strata --config "D:\Strata\Strata-main\strata-iq3_xxs.json" --port 8080 --open
echo [5/5] 完事。想换回原来那份，双击同目录的 切回原版.bat
pause
exit /b 0
:PACKFAIL
echo [失败] 建 pack 失败。配置一点没动。正在用原来的模型重启 Strata ...
"D:\Strata\Strata-main\serve\server.py" --engine strata --config "D:\Strata\Strata-main\strata-iq3_xxs.json" --port 8080 --open
pause
exit /b 1
:SWFAIL
echo [失败] 切换失败。配置一点没动。正在用原来的模型重启 Strata ...
"D:\Strata\Strata-main\serve\server.py" --engine strata --config "D:\Strata\Strata-main\strata-iq3_xxs.json" --port 8080 --open
pause
exit /b 1
