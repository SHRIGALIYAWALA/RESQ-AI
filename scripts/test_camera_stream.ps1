param(
    [Parameter(Mandatory = $true)]
    [string]$CameraStreamUrl
)

$ErrorActionPreference = "Stop"
$uri = $null
if (-not [System.Uri]::TryCreate($CameraStreamUrl, [System.UriKind]::Absolute, [ref]$uri)) {
    throw "CameraStreamUrl must be an absolute HTTP or HTTPS URL."
}
if ($uri.Scheme -notin @("http", "https")) {
    throw "CameraStreamUrl must use HTTP or HTTPS."
}

$request = [System.Net.HttpWebRequest]::Create($uri)
$request.Method = "GET"
$request.Timeout = 5000
$request.ReadWriteTimeout = 5000
$response = $null
try {
    $response = $request.GetResponse()
    if ($response.StatusCode -ne [System.Net.HttpStatusCode]::OK) {
        throw "Camera endpoint returned HTTP $([int]$response.StatusCode)."
    }

    $contentType = $response.ContentType.ToLowerInvariant()
    if ($contentType -notmatch "multipart/x-mixed-replace|multipart/mjpeg|image/jpeg") {
        throw "Expected an MJPEG stream, received content type '$contentType'."
    }

    $stream = $response.GetResponseStream()
    $stream.ReadTimeout = 5000
    $frameCount = 0
    $bytesRead = 0
    $previousByte = -1
    $insideFrame = $false
    $maximumBytes = 2MB

    while ($frameCount -lt 2 -and $bytesRead -lt $maximumBytes) {
        $currentByte = $stream.ReadByte()
        if ($currentByte -lt 0) { break }
        $bytesRead += 1

        if (-not $insideFrame -and $previousByte -eq 0xFF -and $currentByte -eq 0xD8) {
            $insideFrame = $true
        } elseif ($insideFrame -and $previousByte -eq 0xFF -and $currentByte -eq 0xD9) {
            $frameCount += 1
            $insideFrame = $false
        }
        $previousByte = $currentByte
    }

    if ($frameCount -lt 2) {
        throw "Received fewer than two complete JPEG frames from the camera stream."
    }
    Write-Output "Camera stream passed: HTTP 200, $contentType, and two complete JPEG frames received."
} catch {
    throw "Camera stream check failed. Verify the phone's current IP, IP Webcam server state, authentication, and LAN reachability. $($_.Exception.Message)"
} finally {
    if ($response) { $response.Close() }
}
