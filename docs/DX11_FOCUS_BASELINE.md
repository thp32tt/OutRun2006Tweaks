# Focus-first DX11 hybrid build

This branch uses the **exact published DX9Ex Focus v0.01 runtime as its default fallback executable** in the hybrid package; the independent DX11 renderer stays in a separate opt-in binary. This is a Focus-based runtime/package, NOT a blanket merge of thousands of divergent source commits.

Focus source: `5d68d900deeccc003c4c8bf0e5eb46614eaa3302`. Focus release SHA256: `66e6b8cfdea6bbe28d45778d9663466ba0d212c0e6027b518ec3800db9f50959`. The workflow validates both before packaging. The DX11 compiler outputs are saved under `DX11_Experimental/`; original native source and CI contracts remain unchanged.

Install by extracting into an existing legal OutRun2006 game folder. `Start-OutRun-VR.cmd` uses the published Focus runtime by default. To experiment with the DX11 DLL choose `Start-OutRun-DX11-Experimental.cmd`; to restore the Focus runtime choose `Start-OutRun-Focus.cmd`, optionally passing `launch`. Never change the backend while the game is running.

Important: Focus runtime's previous HMD result does not prove the DX11 branch or experimental DX11 path is playable. DX11 HMD test is UNTESTED. No game exe or original assets are packaged.
