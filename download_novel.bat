@echo off
chcp 65001 >nul
echo 小说下载器
echo ===========
echo.

REM 检查是否安装了Python
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python，请先安装Python 3.6或更高版本
    pause
    exit /b 1
)

REM 检查是否安装了依赖
python -c "import requests" >nul 2>&1
if errorlevel 1 (
    echo 正在安装依赖包...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo 错误: 依赖安装失败
        pause
        exit /b 1
    )
)

REM 下载小说
echo 开始下载小说...
echo.
python novel_downloader.py https://www.qb5.io/xs-66401/

echo.
echo 完成！
pause



