#!/usr/bin/env python3
"""Private ZIP: Daytona actual native PMT replacement + additive OVC2.
Use self-contained wrappers; original game files are never changed here.
"""
from pathlib import Path
import hashlib, json, zipfile
ROOT=Path(__file__).resolve().parent
RUNTIME=ROOT/"runtime_v3"
PMT="obj_plcar_dayts_pmt.sz"
OVC="Daytona365_Cockpit_R26_v2.ovc"
ORIGINAL_SHA="f393ba5c706453a4d3f71604f25cd1631594152380856462fb0a504143ba6abe"
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
pmth=sha(RUNTIME/PMT)
ovch=sha(RUNTIME/OVC)
ps1=r'''param([switch]$Restore)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$root = $PSScriptRoot
$assets = Join-Path $root 'DAYTONA365_TEST_ASSETS'
$car = Join-Path $root 'Cars\obj_plcar_dayts_pmt.sz'
$backup = Join-Path $root 'Cars\obj_plcar_dayts_pmt.sz.DAYTONA365_V2_ORIGINAL.bak'
$sidecar = Join-Path $root 'Daytona365_Cockpit_R26_v2.ovc'
$sourcePmt = Join-Path $assets 'obj_plcar_dayts_pmt.sz'
$sourceOvc = Join-Path $assets 'Daytona365_Cockpit_R26_v2.ovc'
$originalHash = '__ORIGINAL__'
$modifiedHash = '__MODIFIED__'
$sidecarHash = '__OVCHASH__'
try {
    if (-not (Test-Path -LiteralPath (Join-Path $root 'OR2006C2C.EXE'))) {
        throw 'Extract the ZIP directly into your OR2006C2C.EXE game folder, then run the CMD from there.'
    }
    if (-not (Test-Path -LiteralPath $car)) {throw 'Original Cars\obj_plcar_dayts_pmt.sz not found.'}
    if ($Restore) {
        if (-not (Test-Path -LiteralPath $backup)) {throw 'No original Daytona backup to restore.'}
        if ((Get-FileHash -Algorithm SHA256 -LiteralPath $backup).Hash -ne $originalHash) {
            throw 'Backup hash mismatch: refusing restore.'
        }
        Copy-Item -LiteralPath $backup -Destination ($car+'.new') -Force
        Move-Item -LiteralPath ($car+'.new') -Destination $car -Force
        if ((Get-FileHash -Algorithm SHA256 -LiteralPath $car).Hash -ne $originalHash) {
            throw 'Restore verify failed.'
        }
        Remove-Item -LiteralPath $backup -Force
        if (Test-Path -LiteralPath $sidecar) {
            $existing = (Get-FileHash -Algorithm SHA256 -LiteralPath $sidecar).Hash
            if ($existing -eq $sidecarHash) {Remove-Item -LiteralPath $sidecar -Force}
            else {Write-Host 'Sidecar was modified externally; left untouched.'}
        }
        Write-Host 'RESTORED Daytona original. Dino never changed.'
    } else {
        foreach ($p in @($sourcePmt,$sourceOvc)) {
            if (-not (Test-Path -LiteralPath $p)) {throw "Missing packaged asset: $p"}
        }
        if ((Get-FileHash -Algorithm SHA256 -LiteralPath $sourcePmt).Hash -ne $modifiedHash) {
            throw 'Packaged Daytona PMT SHA mismatch.'
        }
        if ((Get-FileHash -Algorithm SHA256 -LiteralPath $sourceOvc).Hash -ne $sidecarHash) {
            throw 'Packaged Daytona OVC SHA mismatch.'
        }
        $liveHash=(Get-FileHash -Algorithm SHA256 -LiteralPath $car).Hash
        if ($liveHash -ne $originalHash -and $liveHash -ne $modifiedHash) {
            throw 'Daytona original is an unknown version: not overwriting.'
        }
        if (-not (Test-Path -LiteralPath $backup)) {
            if ($liveHash -eq $modifiedHash) {
                throw 'Patched asset exists but original backup is missing; do not overwrite.'
            }
            Copy-Item -LiteralPath $car -Destination $backup
        }
        if ((Get-FileHash -Algorithm SHA256 -LiteralPath $backup).Hash -ne $originalHash) {
            throw 'Existing Daytona backup is not original; refusing install.'
        }
        $stage=$car+'.new'
        Copy-Item -LiteralPath $sourcePmt -Destination $stage -Force
        Move-Item -LiteralPath $stage -Destination $car -Force
        Copy-Item -LiteralPath $sourceOvc -Destination $sidecar -Force
        if ((Get-FileHash -Algorithm SHA256 -LiteralPath $car).Hash -ne $modifiedHash) {
            throw 'Install PMT hash check failed.'
        }
        Write-Host 'INSTALLED: Daytona PMT texture upgrade + Daytona OVC2 sidecar.'
        Write-Host 'OVC2 geometry ALSO REQUIRES the tested Daytona branch DLL and [VR] DaytonaExternalCockpit = true.'
        Write-Host 'No DLL and no game EXE were modified. Original Daytona backup preserved.'
    }
    exit 0
} catch {
    Write-Host ('ERROR: ' + $_.Exception.Message) -ForegroundColor Red
    exit 1
}
'''.replace("__ORIGINAL__",ORIGINAL_SHA.upper()).replace("__MODIFIED__",pmth.upper()).replace("__OVCHASH__",ovch.upper())
install=r'''@echo off
setlocal
if not exist "%~dp0INSTALL-DAYTONA365-TEST.ps1" (
 echo [ERROR] Companion PowerShell file is missing from this folder.
 pause
 exit /b 2
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0INSTALL-DAYTONA365-TEST.ps1"
set "rc=%ERRORLEVEL%"
if not "%rc%"=="0" (echo [FAILED] Exit %rc%.) else (echo [OK] Daytona native texture install complete.)
pause
exit /b %rc%
'''
restore=install.replace('INSTALL-DAYTONA365-TEST.ps1"\nset "rc=', 'INSTALL-DAYTONA365-TEST.ps1" -Restore\nset "rc=').replace('[OK] Daytona native texture install complete.','[OK] Daytona native texture restore complete.')
readme=f"""DAYTONA365 PHOTO-BASED MESH REWORK V3 / 2026-11-07

TARGET: OutRun 2006 PC VR, Ferrari 365 GTS/4 Daytona (second Ferrari).
DINO 246: NO MODIFICATION.

INSTALL (from the directory with OR2006C2C.EXE):
1. Unzip THIS ZIP into the game directory.
2. Double click INSTALL-DAYTONA365-TEST.cmd.
3. Native Daytona texture replacement is active even WITHOUT a new DLL.
4. For ADDITIVE 3D metal rings / raised seams, install the matching tested
   dinput8.dll from the GitHub Daytona branch, then set in OutRun2006Tweaks.ini:
   [VR]
   DaytonaExternalCockpit = true
   VRQuestCockpitV2Enabled must also be enabled with mode-1 stereo.
5. The native game still renders original steering/chassis. This sidecar adds real photo-textured refined seat/console/tonneau surfaces,\n   piping, source-UV photographed switch-bank, and physically raised trim.\n   Native steering wheel remains original; no second entire vehicle.
   Player kind=2 gate is static-source-assumed and needs an actual run test.
6. VR HMD/game execute not tested in this environment. Keep a copy of your
   working game install separate.

RESTORE:
Double click RESTORE-DAYTONA365-TEST.cmd.
This restores the original car PMT and deletes only the matching test OVC.
The installed new DLL/INI (if you manually changed these) must be rolled back
separately. Any unrelated car assets stay untouched.

Native texture files cannot gain more pixels using this in-place BC1 edit;
this is a visual repaint at the original resolutions, not a 4K atlas.
Complete HMD parity still requires mapping and verifying the replacement 3D asset to the
verified player car space, plus original interior draw suppression.

Source original SHA256: {ORIGINAL_SHA}
Candidate native SHA256: {pmth}
Candidate additive OVC SHA256: {ovch}
GitHub source branch:
https://github.com/thp32tt/OutRun2006Tweaks/tree/feature/daytona365-runtime-ovc-r26-20261107

PRIVATE: Original game asset derivatives are not for public redistribution.
"""
files={
"INSTALL-DAYTONA365-TEST.ps1":ps1.encode("utf-8"),
"INSTALL-DAYTONA365-TEST.cmd":install.encode("ascii"),
"RESTORE-DAYTONA365-TEST.cmd":restore.encode("ascii"),
"README_DAYTONA365_TEST.txt":readme.encode("utf-8"),
"DAYTONA365_TEST_ASSETS/"+PMT:(RUNTIME/PMT).read_bytes(),
"DAYTONA365_TEST_ASSETS/"+OVC:(RUNTIME/OVC).read_bytes(),
"DAYTONA365_TEST_ASSETS/DAYTONA_NATIVE_PMT_REPAINT_REPORT.json":(RUNTIME/"DAYTONA_NATIVE_PMT_REPAINT_REPORT.json").read_bytes(),
"DAYTONA365_TEST_ASSETS/DAYTONA_V3_PHOTO_MODEL_MANIFEST.json":(RUNTIME/"DAYTONA_V3_PHOTO_MODEL_MANIFEST.json").read_bytes()
}
# Include the exact privately-generated photo-derived materials and editable mesh,
# but never include any downloaded source reference photo.
for asset in sorted(RUNTIME.glob("Daytona365_PHOTO_*.png")):
    files["DAYTONA365_EDITABLE_MATERIALS/"+asset.name]=asset.read_bytes()
for filename in ("Daytona365_Cockpit_SOURCE_ALIGNED_v3.obj",
                 "Daytona365_v3.mtl",
                 "DAYTONA_V3_PHOTO_MODEL_MANIFEST.json"):
    asset=RUNTIME/filename
    files["DAYTONA365_EDITABLE_MATERIALS/"+filename]=asset.read_bytes()
archive=ROOT/"Daytona365_PHOTO_MESH_TEXTURE_TEST_v3_PRIVATE.zip"
with zipfile.ZipFile(archive,"w",zipfile.ZIP_DEFLATED,compresslevel=8) as z:
    for name,data in files.items():z.writestr(name,data)
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert set(z.namelist())==set(files)
    ps=z.read("INSTALL-DAYTONA365-TEST.ps1").decode()
    assert pmth.upper() in ps and ovch.upper() in ps and ORIGINAL_SHA.upper() in ps
    assert " -Restore" in z.read("RESTORE-DAYTONA365-TEST.cmd").decode()
print(json.dumps({"archive":str(archive),"size_bytes":archive.stat().st_size,
  "zip_entries":list(files),"native_sha":pmth,"ovc_sha":ovch,
  "zip_test":"PASS","preserved":"Dino/no EXE/DLL modification"} ,indent=2))