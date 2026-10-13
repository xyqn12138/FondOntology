param(
    [Parameter(Mandatory = $true)][string]$Source,
    [Parameter(Mandatory = $true)][string]$Output
)

$resolvedSource = (Resolve-Path -LiteralPath $Source).Path
$resolvedOutput = [System.IO.Path]::GetFullPath($Output)
$workspaceData = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "../data"))
if (!$resolvedSource.StartsWith($workspaceData + "\", [StringComparison]::OrdinalIgnoreCase) -or
    !$resolvedOutput.StartsWith($workspaceData + "\_converted\", [StringComparison]::OrdinalIgnoreCase)) {
    throw "Word originals and converted outputs must remain within the data workspace"
}
if (Test-Path -LiteralPath $resolvedOutput) {
    throw "Conversion output already exists"
}
[System.IO.Directory]::CreateDirectory([System.IO.Path]::GetDirectoryName($resolvedOutput)) | Out-Null
$wordApplication = $null
$wordDocument = $null
try {
    $wordApplication = New-Object -ComObject Word.Application
    $wordApplication.Visible = $false
    $wordApplication.DisplayAlerts = 0
    $wordApplication.AutomationSecurity = 3
    $wordDocument = $wordApplication.Documents.Open($resolvedSource, $false, $true, $false)
    $paragraphCount = $wordDocument.Paragraphs.Count
    $tableCount = $wordDocument.Tables.Count
    $shapeCount = $wordDocument.Shapes.Count + $wordDocument.InlineShapes.Count
    $wordDocument.SaveAs2($resolvedOutput, 8)
    [ordered]@{
        converter = "Microsoft Word HTML export"
        version = $wordApplication.Version
        source = $resolvedSource
        output = $resolvedOutput
        paragraphs = $paragraphCount
        tables = $tableCount
        shapes = $shapeCount
        source_opened_readonly = $true
    } | ConvertTo-Json
}
finally {
    if ($wordDocument) {
        $wordDocument.Close(0)
        [Runtime.InteropServices.Marshal]::FinalReleaseComObject($wordDocument) | Out-Null
    }
    if ($wordApplication) {
        $wordApplication.Quit(0)
        [Runtime.InteropServices.Marshal]::FinalReleaseComObject($wordApplication) | Out-Null
    }
}
