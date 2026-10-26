param(
    [string]$BaseUrl = "https://localhost",
    [string]$Username = $env:RESQ_OPERATOR_USERNAME,
    [string]$Password = $env:RESQ_OPERATOR_PASSWORD,
    [switch]$SkipTlsValidation
)

$ErrorActionPreference = "Stop"
if ($SkipTlsValidation) {
    [System.Net.ServicePointManager]::ServerCertificateValidationCallback = { $true }
}

function Invoke-Json($Method, $Path, $Body = $null, $Headers = @{}) {
    $params = @{ Method = $Method; Uri = "$BaseUrl$Path"; Headers = $Headers; UseBasicParsing = $true }
    if ($null -ne $Body) {
        $params.ContentType = "application/json"
        $params.Body = ($Body | ConvertTo-Json -Depth 8)
    }
    return Invoke-RestMethod @params
}

$health = Invoke-Json "GET" "/health"
if ($health.status -ne "ok") { throw "Health check failed" }
$ready = Invoke-Json "GET" "/ready"
if ($ready.status -ne "ready" -or $ready.database -ne "ok") { throw "Readiness check failed" }
$providers = Invoke-Json "GET" "/api/health/providers"
if ($providers.status -ne "ok") { throw "Provider health check failed" }

if ($Username -and $Password) {
    $token = Invoke-Json "POST" "/api/auth/token" @{ username = $Username; password = $Password }
    if (-not $token.access_token) { throw "Authentication did not return an access token" }
    $headers = @{ Authorization = "Bearer $($token.access_token)" }
    $headers = @{ Authorization = "Bearer $($token.access_token)" }
    $audit = Invoke-Json "GET" "/api/audit" $null $headers
    Write-Output "Authenticated audit endpoint: OK ($($audit.Count) records)"
} else {
    Write-Warning "RESQ_OPERATOR_USERNAME and RESQ_OPERATOR_PASSWORD were not supplied; authenticated checks skipped."
}

Write-Output "Production acceptance checks passed for $BaseUrl"
