param(
    [string]$PostgresBin = "C:\Program Files\PostgreSQL\18\bin",
    [int]$Port = 55432
)

$ErrorActionPreference = "Stop"
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$runtimeRoot = [System.IO.Path]::GetFullPath((Join-Path $repoRoot ".phase6"))
$dataDirectory = Join-Path $runtimeRoot "postgres-data"
$initdb = Join-Path $PostgresBin "initdb.exe"
$pgCtl = Join-Path $PostgresBin "pg_ctl.exe"
$pgIsReady = Join-Path $PostgresBin "pg_isready.exe"
$psql = Join-Path $PostgresBin "psql.exe"
$createdb = Join-Path $PostgresBin "createdb.exe"
$postgres = Join-Path $PostgresBin "postgres.exe"
$stdoutLog = Join-Path $runtimeRoot "postgres.stdout.log"
$stderrLog = Join-Path $runtimeRoot "postgres.stderr.log"
$databaseName = "buglessfit_phase6_learning"

foreach ($executable in @($initdb, $pgCtl, $pgIsReady, $psql, $createdb, $postgres)) {
    if (-not (Test-Path -LiteralPath $executable -PathType Leaf)) {
        throw "Required PostgreSQL executable was not found: $executable"
    }
}

if (-not $runtimeRoot.StartsWith($repoRoot + [System.IO.Path]::DirectorySeparatorChar)) {
    throw "The Phase 6 runtime directory must remain inside the repository."
}

New-Item -ItemType Directory -Force -Path $runtimeRoot | Out-Null
if (-not (Test-Path -LiteralPath (Join-Path $dataDirectory "PG_VERSION"))) {
    & $initdb --pgdata=$dataDirectory --username=buglessfit_phase6 --encoding=UTF8 --no-locale --auth-local=trust --auth-host=trust
    if ($LASTEXITCODE -ne 0) {
        throw "Could not initialize the isolated PostgreSQL cluster."
    }
}

& $pgIsReady --host=127.0.0.1 --port=$Port *> $null
if ($LASTEXITCODE -eq 0) {
    throw "Port $Port already belongs to another PostgreSQL server. Choose another -Port."
}

# PostgreSQL 18's pg_ctl launcher cannot create its restricted re-execution
# token in some managed Windows shells. Starting postgres.exe directly avoids
# that launcher-only failure while retaining an isolated child process.
# Some managed shells also provide both Path and PATH. Windows PowerShell's
# Start-Process rejects that duplicate case-insensitive key, so keep the
# sandbox-aware uppercase value and remove only the duplicate spelling.
$processEnvironment = [Environment]::GetEnvironmentVariables()
if ($processEnvironment.Contains("Path") -and $processEnvironment.Contains("PATH")) {
    [Environment]::SetEnvironmentVariable("Path", $null, "Process")
}
$serverArguments = @(
    "-D", ('"{0}"' -f $dataDirectory),
    "-p", "$Port",
    "-h", "127.0.0.1",
    "-c", "autovacuum=off",
    "-c", "max_worker_processes=0",
    "-c", "io_method=sync"
)
$previousDatabaseUrl = $env:DATABASE_URL
$previousConnectionAge = $env:DB_CONN_MAX_AGE
$serverProcess = $null
try {
    $serverProcess = Start-Process -FilePath $postgres -ArgumentList $serverArguments -WorkingDirectory $repoRoot -WindowStyle Hidden -RedirectStandardOutput $stdoutLog -RedirectStandardError $stderrLog -PassThru

    $ready = $false
    for ($attempt = 0; $attempt -lt 120; $attempt++) {
        if ($serverProcess.HasExited) {
            $diagnostic = (Get-Content -LiteralPath $stderrLog -ErrorAction SilentlyContinue | Select-Object -Last 20) -join [Environment]::NewLine
            throw "The isolated PostgreSQL process exited during startup.$([Environment]::NewLine)$diagnostic"
        }
        & $pgIsReady --host=127.0.0.1 --port=$Port *> $null
        if ($LASTEXITCODE -eq 0) {
            $ready = $true
            break
        }
        Start-Sleep -Milliseconds 250
    }
    if (-not $ready) {
        throw "The isolated PostgreSQL cluster did not become ready within 30 seconds."
    }

    $databaseExists = & $psql --host=127.0.0.1 --port=$Port --username=buglessfit_phase6 --dbname=postgres --tuples-only --no-align --command="SELECT 1 FROM pg_database WHERE datname = '$databaseName'"
    if ($LASTEXITCODE -ne 0) {
        throw "Could not inspect the isolated PostgreSQL cluster."
    }
    if (($databaseExists | Out-String).Trim() -ne "1") {
        & $createdb --host=127.0.0.1 --port=$Port --username=buglessfit_phase6 $databaseName
        if ($LASTEXITCODE -ne 0) {
            throw "Could not create the Phase 6 PostgreSQL database."
        }
    }

    $env:DATABASE_URL = "postgresql://buglessfit_phase6@127.0.0.1:$Port/$databaseName"
    $env:DB_CONN_MAX_AGE = "0"
    # Keeping this disposable database avoids PostgreSQL's cluster-wide DROP
    # DATABASE barrier, which is unreliable inside some managed Windows shells.
    # Django still flushes every TransactionTestCase and applies new migrations.
    & python manage.py test store.tests.test_phase6_concurrency --verbosity 2 --keepdb
    if ($LASTEXITCODE -ne 0) {
        throw "The PostgreSQL concurrency suite failed."
    }
}
finally {
    $env:DATABASE_URL = $previousDatabaseUrl
    $env:DB_CONN_MAX_AGE = $previousConnectionAge
    if ($serverProcess -and -not $serverProcess.HasExited) {
        & $pgCtl stop --pgdata=$dataDirectory --wait --mode=fast
        if ($LASTEXITCODE -ne 0 -and -not $serverProcess.HasExited) {
            Stop-Process -Id $serverProcess.Id -Force
        }
    }
}
