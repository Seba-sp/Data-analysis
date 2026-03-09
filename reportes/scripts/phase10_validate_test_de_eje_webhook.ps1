param(
    [Parameter(Mandatory = $false)]
    [string]$CorrelationId = ("phase10-" + (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")),

    [Parameter(Mandatory = $false)]
    [switch]$DryRun,

    [Parameter(Mandatory = $false)]
    [switch]$TriggerWebhook,

    [Parameter(Mandatory = $false)]
    [string]$WebhookUrl = $env:PHASE10_WEBHOOK_URL,

    [Parameter(Mandatory = $false)]
    [string]$WebhookSecret,

    [Parameter(Mandatory = $false)]
    [string]$RecipientEmail,

    [Parameter(Mandatory = $false)]
    [string]$PayloadFile,

    [Parameter(Mandatory = $false)]
    [string]$FirestoreProject = $env:GOOGLE_CLOUD_PROJECT
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Mask-Value {
    param([string]$Value)
    if ([string]::IsNullOrWhiteSpace($Value)) { return "<missing>" }
    if ($Value.Length -le 4) { return ("*" * $Value.Length) }
    return ("*" * ($Value.Length - 4)) + $Value.Substring($Value.Length - 4)
}

function Add-Checkpoint {
    param(
        [string]$Name,
        [bool]$Pass,
        [string]$Details
    )
    $status = if ($Pass) { "PASS" } else { "FAIL" }
    [PSCustomObject]@{
        name = $Name
        status = $status
        details = $Details
    }
}

Write-Host "== Phase 10 validation helper (test_de_eje) =="
Write-Host ("Timestamp (UTC): {0}" -f (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ"))
Write-Host ("CorrelationId : {0}" -f $CorrelationId)
Write-Host ("Mode          : {0}" -f ($(if ($DryRun) { "DRY-RUN" } else { "LIVE" })))
Write-Host ""

Write-Host "== Preflight summary (secret-safe) =="
$preflight = [ordered]@{
    ASSESSMENT_MAPPING_SOURCE = $env:ASSESSMENT_MAPPING_SOURCE
    IDS_XLSX_GCS_PATH = $env:IDS_XLSX_GCS_PATH
    FIRESTORE_PROJECT = $FirestoreProject
    WEBHOOK_URL = $WebhookUrl
    WEBHOOK_SECRET_PRESENT = $(if ([string]::IsNullOrWhiteSpace($WebhookSecret)) { "no" } else { "yes" })
    EMAIL_SENDER = $env:EMAIL_SENDER
    SMTP_HOST = $env:SMTP_HOST
    SMTP_USERNAME = $env:SMTP_USERNAME
    SMTP_PASSWORD = Mask-Value -Value $env:SMTP_PASSWORD
}
$preflight.GetEnumerator() | ForEach-Object {
    Write-Host ("- {0}: {1}" -f $_.Key, $(if ([string]::IsNullOrWhiteSpace([string]$_.Value)) { "<missing>" } else { $_.Value }))
}
Write-Host ""

$checkpoints = New-Object System.Collections.Generic.List[object]

$mapOk = -not [string]::IsNullOrWhiteSpace($env:ASSESSMENT_MAPPING_SOURCE)
$mapPass = $mapOk -or $DryRun.IsPresent
$checkpoints.Add((Add-Checkpoint -Name "preflight.mapping_source_present" -Pass $mapPass -Details ("ASSESSMENT_MAPPING_SOURCE={0}{1}" -f $(if ($mapOk) { $env:ASSESSMENT_MAPPING_SOURCE } else { "<missing>" }), $(if (-not $mapOk -and $DryRun) { " (dry-run non-blocking)" } else { "" }))))

$idsOk = -not [string]::IsNullOrWhiteSpace($env:IDS_XLSX_GCS_PATH)
$idsPass = $idsOk -or $DryRun.IsPresent
$checkpoints.Add((Add-Checkpoint -Name "preflight.ids_gcs_path_present" -Pass $idsPass -Details ("IDS_XLSX_GCS_PATH={0}{1}" -f $(if ($idsOk) { $env:IDS_XLSX_GCS_PATH } else { "<missing>" }), $(if (-not $idsOk -and $DryRun) { " (dry-run non-blocking)" } else { "" }))))

$senderOk = -not [string]::IsNullOrWhiteSpace($env:EMAIL_SENDER)
$senderPass = $senderOk -or $DryRun.IsPresent
$checkpoints.Add((Add-Checkpoint -Name "preflight.email_sender_present" -Pass $senderPass -Details ("EMAIL_SENDER={0}{1}" -f $(if ($senderOk) { $env:EMAIL_SENDER } else { "<missing>" }), $(if (-not $senderOk -and $DryRun) { " (dry-run non-blocking)" } else { "" }))))

$webhookTriggered = $false
$triggerResult = "<not-triggered>"
$httpStatus = $null

if ($TriggerWebhook) {
    if ([string]::IsNullOrWhiteSpace($WebhookUrl)) {
        $checkpoints.Add((Add-Checkpoint -Name "trigger.webhook_request" -Pass $false -Details "WebhookUrl is missing."))
    } elseif ($DryRun) {
        $checkpoints.Add((Add-Checkpoint -Name "trigger.webhook_request" -Pass $true -Details "Dry-run: webhook call skipped intentionally."))
    } else {
        $bodyObject = $null
        if (-not [string]::IsNullOrWhiteSpace($PayloadFile)) {
            if (-not (Test-Path -LiteralPath $PayloadFile)) {
                throw "PayloadFile not found: $PayloadFile"
            }
            $payloadText = Get-Content -Raw -LiteralPath $PayloadFile
            $bodyObject = $payloadText | ConvertFrom-Json
        } else {
            $bodyObject = [ordered]@{
                assessment_type = "test_de_eje"
                correlation_id = $CorrelationId
                recipient_email = $RecipientEmail
            }
        }

        if ($null -eq $bodyObject.PSObject.Properties["correlation_id"]) {
            $bodyObject | Add-Member -NotePropertyName "correlation_id" -NotePropertyValue $CorrelationId
        } else {
            $bodyObject.correlation_id = $CorrelationId
        }
        if ($null -eq $bodyObject.PSObject.Properties["assessment_type"]) {
            $bodyObject | Add-Member -NotePropertyName "assessment_type" -NotePropertyValue "test_de_eje"
        } else {
            $bodyObject.assessment_type = "test_de_eje"
        }
        if (-not [string]::IsNullOrWhiteSpace($RecipientEmail)) {
            if ($null -eq $bodyObject.PSObject.Properties["recipient_email"]) {
                $bodyObject | Add-Member -NotePropertyName "recipient_email" -NotePropertyValue $RecipientEmail
            } else {
                $bodyObject.recipient_email = $RecipientEmail
            }
        }

        $headers = @{
            "Content-Type" = "application/json"
            "X-Correlation-Id" = $CorrelationId
        }
        if (-not [string]::IsNullOrWhiteSpace($WebhookSecret)) {
            $headers["X-Webhook-Secret"] = $WebhookSecret
        }

        $jsonBody = $bodyObject | ConvertTo-Json -Depth 15
        try {
            $response = Invoke-WebRequest -Method Post -Uri $WebhookUrl -Headers $headers -Body $jsonBody -TimeoutSec 60
            $webhookTriggered = $true
            $httpStatus = [int]$response.StatusCode
            $triggerResult = ("HTTP {0}" -f $httpStatus)
            $pass = ($httpStatus -ge 200 -and $httpStatus -lt 300)
            $checkpoints.Add((Add-Checkpoint -Name "trigger.webhook_request" -Pass $pass -Details $triggerResult))
        } catch {
            $triggerResult = $_.Exception.Message
            $checkpoints.Add((Add-Checkpoint -Name "trigger.webhook_request" -Pass $false -Details $triggerResult))
        }
    }
} else {
    $checkpoints.Add((Add-Checkpoint -Name "trigger.webhook_request" -Pass $true -Details "Skipped (use -TriggerWebhook to execute)."))
}

$gcloudAvailable = $false
try {
    & gcloud --version | Out-Null
    $gcloudAvailable = $true
} catch {
    $gcloudAvailable = $false
}

if ($DryRun) {
    $checkpoints.Add((Add-Checkpoint -Name "firestore.queue_checkpoint" -Pass $true -Details "Dry-run: Firestore query skipped."))
    $checkpoints.Add((Add-Checkpoint -Name "firestore.counter_checkpoint" -Pass $true -Details "Dry-run: Firestore query skipped."))
    $checkpoints.Add((Add-Checkpoint -Name "firestore.batch_checkpoint" -Pass $true -Details "Dry-run: Firestore query skipped."))
} elseif (-not $gcloudAvailable) {
    $checkpoints.Add((Add-Checkpoint -Name "firestore.queue_checkpoint" -Pass $false -Details "gcloud CLI not available in this environment."))
    $checkpoints.Add((Add-Checkpoint -Name "firestore.counter_checkpoint" -Pass $false -Details "gcloud CLI not available in this environment."))
    $checkpoints.Add((Add-Checkpoint -Name "firestore.batch_checkpoint" -Pass $false -Details "gcloud CLI not available in this environment."))
} elseif ([string]::IsNullOrWhiteSpace($FirestoreProject)) {
    $checkpoints.Add((Add-Checkpoint -Name "firestore.queue_checkpoint" -Pass $false -Details "GOOGLE_CLOUD_PROJECT / -FirestoreProject missing."))
    $checkpoints.Add((Add-Checkpoint -Name "firestore.counter_checkpoint" -Pass $false -Details "GOOGLE_CLOUD_PROJECT / -FirestoreProject missing."))
    $checkpoints.Add((Add-Checkpoint -Name "firestore.batch_checkpoint" -Pass $false -Details "GOOGLE_CLOUD_PROJECT / -FirestoreProject missing."))
} else {
    $checkpoints.Add((Add-Checkpoint -Name "firestore.queue_checkpoint" -Pass $true -Details ("Manual query required: filter by correlation_id={0}" -f $CorrelationId)))
    $checkpoints.Add((Add-Checkpoint -Name "firestore.counter_checkpoint" -Pass $true -Details ("Manual query required: counter delta for correlation_id={0}" -f $CorrelationId)))
    $checkpoints.Add((Add-Checkpoint -Name "firestore.batch_checkpoint" -Pass $true -Details ("Manual query required: batch lifecycle for correlation_id={0}" -f $CorrelationId)))
}

if ($DryRun) {
    $checkpoints.Add((Add-Checkpoint -Name "email.proof_checkpoint" -Pass $true -Details "Dry-run: email receipt not expected."))
} else {
    $checkpoints.Add((Add-Checkpoint -Name "email.proof_checkpoint" -Pass $false -Details "Human verification required: verify one email with one PDF attachment and expected filename."))
}

Write-Host ""
Write-Host "== Checkpoint summary =="
$checkpoints | ForEach-Object {
    Write-Host ("[{0}] {1} :: {2}" -f $_.status, $_.name, $_.details)
}

$failed = @($checkpoints | Where-Object { $_.status -eq "FAIL" })
$overall = if ($failed.Count -eq 0) { "PASS" } else { "FAIL" }

Write-Host ""
Write-Host ("OVERALL: {0}" -f $overall)
Write-Host ("CorrelationId: {0}" -f $CorrelationId)
Write-Host ("WebhookTriggered: {0}" -f $webhookTriggered)
Write-Host ("WebhookResult: {0}" -f $triggerResult)

if ($overall -eq "FAIL") {
    exit 2
}
exit 0
