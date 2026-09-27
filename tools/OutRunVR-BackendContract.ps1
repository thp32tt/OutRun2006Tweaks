Set-StrictMode -Version Latest

function Get-OutRunVRBackendContract {
    param(
        [Parameter(Mandatory=$true)]
        [ValidateSet('2d','d3d9','dx11','dxvk-safe','dxvk','dx12')]
        [string]$Backend
    )

    switch ($Backend) {
        '2d' {
            return [pscustomobject]@{
                Backend='2d'; PayloadBackend='d3d9'; DefaultVariant='CONTROL_2D'
                SemanticContract='ORIGINAL_2D'; RenderBackend=1
                VrEnabled=$false; DirectGpuOnly=$false; DisableDesktopDuplication=$false
                NeedsDxvk=$false; NeedsMultiview=$false; RequiresDx12Probe=$false
            }
        }
        'd3d9' {
            return [pscustomobject]@{
                Backend='d3d9'; PayloadBackend='d3d9'; DefaultVariant='R69_FIXPACK'
                SemanticContract='R69_CLEAN'; RenderBackend=1
                VrEnabled=$true; DirectGpuOnly=$false; DisableDesktopDuplication=$false
                NeedsDxvk=$false; NeedsMultiview=$false; RequiresDx12Probe=$false
            }
        }
        'dx11' {
            return [pscustomobject]@{
                Backend='dx11'; PayloadBackend='d3d9'; DefaultVariant='R69_FIXPACK'
                SemanticContract='R69_CLEAN'; RenderBackend=1
                VrEnabled=$true; DirectGpuOnly=$true; DisableDesktopDuplication=$true
                NeedsDxvk=$false; NeedsMultiview=$false; RequiresDx12Probe=$false
            }
        }
        'dxvk-safe' {
            return [pscustomobject]@{
                Backend='dxvk-safe'; PayloadBackend='d3d9'; DefaultVariant='R69_FIXPACK'
                SemanticContract='R69_CLEAN'; RenderBackend=1
                VrEnabled=$true; DirectGpuOnly=$false; DisableDesktopDuplication=$false
                NeedsDxvk=$true; NeedsMultiview=$false; RequiresDx12Probe=$false
            }
        }
        'dxvk' {
            return [pscustomobject]@{
                Backend='dxvk'; PayloadBackend='dxvk'; DefaultVariant='R69_FIXPACK'
                SemanticContract='R69_CLEAN'; RenderBackend=2
                VrEnabled=$true; DirectGpuOnly=$true; DisableDesktopDuplication=$true
                NeedsDxvk=$true; NeedsMultiview=$true; RequiresDx12Probe=$false
            }
        }
        'dx12' {
            return [pscustomobject]@{
                Backend='dx12'; PayloadBackend='dx12'; DefaultVariant='R69_FIXPACK'
                SemanticContract='R69_CLEAN'; RenderBackend=3
                VrEnabled=$true; DirectGpuOnly=$true; DisableDesktopDuplication=$true
                NeedsDxvk=$false; NeedsMultiview=$false; RequiresDx12Probe=$true
            }
        }
    }
}
