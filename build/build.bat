@echo off
setlocal EnableExtensions DisableDelayedExpansion

rem 按脚本位置定位项目目录
set "BUILD_DIR=%~dp0"
for %%I in ("%BUILD_DIR%..") do set "PROJECT_DIR=%%~fI"
set "BACKEND_SOURCE=%PROJECT_DIR%\backend"
set "FRONTEND_SOURCE=%PROJECT_DIR%\frontend"

set "RELEASE_DIR=%BUILD_DIR%output"
set "BACKEND_TARGET=%RELEASE_DIR%\backend"
set "FRONTEND_TARGET=%RELEASE_DIR%\frontend"

rem 后端入口与运行文件校验
if not exist "%BACKEND_SOURCE%\app\core\main.py" (
    echo Backend entry was not found: "%BACKEND_SOURCE%\app\core\main.py"
    goto :failed
)
for %%F in (pyproject.toml uv.lock .python-version .env) do (
    if not exist "%BACKEND_SOURCE%\%%F" (
        echo Required backend file is missing: %%F
        goto :failed
    )
)
rem 本地配置不入库，缺失时用示例配置顶上
set "CONFIG_SOURCE=%BACKEND_SOURCE%\config.yaml"
if not exist "%CONFIG_SOURCE%" (
    set "CONFIG_SOURCE=%BACKEND_SOURCE%\config.example.yaml"
)
if not exist "%CONFIG_SOURCE%" (
    echo Required backend file is missing: config.yaml
    goto :failed
)
for %%D in (app harness skills) do (
    if not exist "%BACKEND_SOURCE%\%%D\" (
        echo Required backend directory is missing: %%D
        goto :failed
    )
)
if not exist "%FRONTEND_SOURCE%\package.json" (
    echo Frontend source was not found: "%FRONTEND_SOURCE%"
    goto :failed
)

rem 部署文件校验
for %%F in (Dockerfile docker-compose.yaml nginx.conf README.md) do (
    if not exist "%BUILD_DIR%%%F" (
        echo Required deployment file is missing: %%F
        goto :failed
    )
)

rem 校验产物路径后清空，链接一律拒绝
powershell -NoProfile -Command "$root=(Resolve-Path -LiteralPath $env:BUILD_DIR).ProviderPath.TrimEnd([char]92); $target=[IO.Path]::GetFullPath([IO.Path]::Combine($root,'output')); if (-not [StringComparer]::OrdinalIgnoreCase.Equals([IO.Path]::GetDirectoryName($target),$root)) { throw 'Unsafe build output path' }; if (Test-Path -LiteralPath $target) { $item=Get-Item -LiteralPath $target -Force; if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Build output is a link' }; $links=Get-ChildItem -LiteralPath $target -Recurse -Force | Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint }; if ($links) { throw 'Build output contains a link' }; Remove-Item -LiteralPath $target -Recurse -Force }"
if errorlevel 1 goto :failed

rem 复制后端代码，排除缓存与本地数据
for %%D in (app harness skills) do (
    if not exist "%BACKEND_TARGET%\%%D" mkdir "%BACKEND_TARGET%\%%D" >nul 2>&1
    if errorlevel 1 goto :failed
    robocopy "%BACKEND_SOURCE%\%%D" "%BACKEND_TARGET%\%%D" /E /R:1 /W:1 /XD __pycache__ /XF *.pyc *.pyo /NFL /NDL /NJH /NJS /NP >nul
    if errorlevel 8 goto :failed
)

for %%F in (pyproject.toml uv.lock .python-version .env) do (
    copy /Y "%BACKEND_SOURCE%\%%F" "%BACKEND_TARGET%\%%F" >nul
    if errorlevel 1 goto :failed
)

rem 配置放目录里，配置页保存要能原子替换；根目录再放一份供直接运行
if not exist "%BACKEND_TARGET%\config" mkdir "%BACKEND_TARGET%\config" >nul 2>&1
if errorlevel 1 goto :failed
copy /Y "%CONFIG_SOURCE%" "%BACKEND_TARGET%\config\config.yaml" >nul
if errorlevel 1 goto :failed
copy /Y "%CONFIG_SOURCE%" "%BACKEND_TARGET%\config.yaml" >nul
if errorlevel 1 goto :failed

rem 技能运行时安装，保留挂载点
if not exist "%BACKEND_TARGET%\skills\public" mkdir "%BACKEND_TARGET%\skills\public" >nul 2>&1
if errorlevel 1 goto :failed
type nul > "%BACKEND_TARGET%\skills\public\.gitkeep"
echo Backend files copied: "%BACKEND_TARGET%"

rem 构建前端，只取生产产物
pushd "%FRONTEND_SOURCE%" >nul
if errorlevel 1 goto :failed
call npm.cmd run build
set "NPM_RESULT=%ERRORLEVEL%"
popd >nul
if not "%NPM_RESULT%"=="0" (
    echo Frontend build command failed.
    goto :failed
)
if not exist "%FRONTEND_SOURCE%\dist\index.html" (
    echo Frontend output was not found: "%FRONTEND_SOURCE%\dist"
    goto :failed
)
mkdir "%FRONTEND_TARGET%" >nul 2>&1
if errorlevel 1 goto :failed
robocopy "%FRONTEND_SOURCE%\dist" "%FRONTEND_TARGET%" /E /R:1 /W:1 /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 goto :failed

echo Frontend files copied: "%FRONTEND_TARGET%"
rem 复制部署文件
for %%F in (Dockerfile docker-compose.yaml nginx.conf README.md) do (
    copy /Y "%BUILD_DIR%%%F" "%RELEASE_DIR%\%%F" >nul
    if errorlevel 1 goto :failed
)
echo Build completed: "%RELEASE_DIR%"
set "RESULT=0"
goto :done

:failed
echo Build failed.
set "RESULT=1"

:done
rem 结束前停留几秒，--no-pause 关闭
if /I not "%~1"=="--no-pause" timeout /t 5 /nobreak >nul
exit /b %RESULT%
