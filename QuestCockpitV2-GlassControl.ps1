# Optional reversible glass tint control for user-selected original player PMT.
# Offline model operation, NOT an in-game OpenXR/GPU or F11 override.
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()
$root=Split-Path -Parent $MyInvocation.MyCommand.Path
$tool=Join-Path $root 'quest_cockpit_glass.py'
if(!(Test-Path -LiteralPath $tool)){throw 'Missing quest_cockpit_glass.py: extract complete ZIP'}
$py=Get-Command py.exe -ErrorAction SilentlyContinue
$pythonArgs=@()
if($py){$pythonArgs=@('-3')}
else{$py=Get-Command python.exe -ErrorAction SilentlyContinue}
if(!$py){throw 'Python 3 is required to patch a selected user-owned PMT'}
function Invoke-Glass([string]$model,[string[]]$operation){
    if(Get-Process -Name 'OR2006C2C' -ErrorAction SilentlyContinue){
        throw 'Close the game before applying or restoring a PMT model.'
    }
    if(!(Test-Path -LiteralPath $model -PathType Leaf)){
        throw 'Choose an existing obj_plcar_*_pmt.sz model.'
    }
    $cli=@($pythonArgs)+@($tool,$model)+$operation
    $output=@(& $py.Source @cli 2>&1)
    $exitCode=$LASTEXITCODE
    $message=($output|ForEach-Object{[string]$_}) -join [Environment]::NewLine
    if($exitCode -ne 0){throw $message}
    return $message
}
$form=New-Object System.Windows.Forms.Form
$form.Text='Quest Cockpit V2 - Windshield Tint Brightness ON/OFF'
$form.ClientSize=New-Object System.Drawing.Size(670,310)
$form.StartPosition='CenterScreen'
$form.FormBorderStyle='FixedDialog'
$form.MaximizeBox=$false
$note=New-Object System.Windows.Forms.Label
$note.SetBounds(15,12,640,40)
$note.Text='File-based, experimental. Select a real installed player-car PMT; close game first.' +
    [Environment]::NewLine + 'ON adjusts tint alpha. OFF restores exact original bytes. No live GPU effect.'
$form.Controls.Add($note)
$path=New-Object System.Windows.Forms.TextBox
$path.SetBounds(15,58,520,25)
$path.ReadOnly=$true
$form.Controls.Add($path)
$browse=New-Object System.Windows.Forms.Button
$browse.Text='Choose PMT'
$browse.SetBounds(542,56,112,28)
$browse.Add_Click({
    $dialog=New-Object System.Windows.Forms.OpenFileDialog
    $dialog.Filter='Player PMT|obj_plcar_*_pmt.sz'
    $dialog.CheckFileExists=$true
    if($dialog.ShowDialog() -eq 'OK'){$path.Text=$dialog.FileName}
})
$form.Controls.Add($browse)
$label=New-Object System.Windows.Forms.Label
$label.Text='Brightness: 75 (0 darker / 100 clearer)'
$label.SetBounds(15,94,620,22)
$form.Controls.Add($label)
$slider=New-Object System.Windows.Forms.TrackBar
$slider.Minimum=0
$slider.Maximum=100
$slider.Value=75
$slider.TickFrequency=10
$slider.SetBounds(15,116,635,45)
$slider.Add_ValueChanged({
    $label.Text="Brightness: $($slider.Value) (0 darker / 100 clearer)"
})
$form.Controls.Add($slider)
$on=New-Object System.Windows.Forms.Button
$on.Text='ON - Apply'
$on.SetBounds(15,174,155,32)
$form.Controls.Add($on)
$off=New-Object System.Windows.Forms.Button
$off.Text='OFF - Restore Original'
$off.SetBounds(185,174,210,32)
$form.Controls.Add($off)
$status=New-Object System.Windows.Forms.TextBox
$status.Multiline=$true
$status.ReadOnly=$true
$status.ScrollBars='Vertical'
$status.SetBounds(15,219,640,74)
$status.Text='No file has been selected or changed.'
$form.Controls.Add($status)
$on.Add_Click({
    try{
        $brightness=$slider.Value
        $status.Text=Invoke-Glass $path.Text @('--in-place','--brightness',"$brightness")
    }catch{$status.Text="REFUSED: $($_.Exception.Message)"}
})
$off.Add_Click({
    try{$status.Text=Invoke-Glass $path.Text @('--restore')}
    catch{$status.Text="REFUSED: $($_.Exception.Message)"}
})
[void]$form.ShowDialog()
