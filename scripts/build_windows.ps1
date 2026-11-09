$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

$projectRoot = Get-Location
$buildRoot = Join-Path $projectRoot ".build"
$python = Join-Path $projectRoot ".venv-build\Scripts\python.exe"
if (-not (Test-Path $python)) {
    py -m venv .venv-build
    if ($LASTEXITCODE -ne 0) { throw "Não foi possível criar o ambiente Python." }
}

& $python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "Não foi possível atualizar o pip." }
& $python -m pip install -e ".[build]"
if ($LASTEXITCODE -ne 0) { throw "Não foi possível instalar as dependências de build." }
& $python -m PyInstaller --noconfirm --clean --onefile --windowed --name ColetorDeDatasets --distpath (Join-Path $buildRoot 'dist') --workpath (Join-Path $buildRoot 'work') --specpath $buildRoot src\coletor_datasets\__main__.py
if ($LASTEXITCODE -ne 0) { throw "A criação do executável falhou." }

$appFolder = Join-Path $projectRoot "Aplicativo"
New-Item -ItemType Directory -Force $appFolder | Out-Null
$appPath = Join-Path $appFolder "ColetorDeDatasets.exe"
Copy-Item (Join-Path $buildRoot 'dist\ColetorDeDatasets.exe') $appPath -Force
@'
COLETOR DE DATASETS

Para abrir, dê dois cliques em ColetorDeDatasets.exe nesta pasta.
Os arquivos CSV ficam no caminho escolhido dentro do aplicativo.
'@ | Set-Content -Encoding utf8 (Join-Path $appFolder 'LEIA-ME.txt')

Write-Host "Executável pronto em: $appPath"

