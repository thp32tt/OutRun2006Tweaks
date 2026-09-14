from pathlib import Path

path = Path(__file__).resolve().parents[1] / "vrhost" / "main_stereo.cpp"
text = path.read_text(encoding="utf-8")
start_marker = "\\n        bool ServiceInteropProbe"
end_marker = "\n        std::uint32_t Write"

if start_marker not in text:
    print("host interop block already normalized")
    raise SystemExit(0)

start = text.index(start_marker)
end = text.index(end_marker, start)
correct = '''
        bool ServiceInteropProbe(ID3D11Device* device, ID3D11DeviceContext* context)
        {
            if (!HeaderValid() || !device || !context) return false;
            const std::uint32_t handleValue = state_->clientInteropProbeHandle;
            const std::uint32_t token = state_->clientInteropProbeToken;
            if (!handleValue || !token) return false;
            if (interopVerifiedToken_ == token && state_->hostInteropProbeAckToken == token) return true;
            if (state_->clientAdapterLuidLow != adapterLuid_.LowPart ||
                state_->clientAdapterLuidHigh != static_cast<std::uint32_t>(adapterLuid_.HighPart)) return false;

            ID3D11Resource* resource = nullptr;
            ID3D11Texture2D* texture = nullptr;
            ID3D11Texture2D* staging = nullptr;
            const HANDLE handle = reinterpret_cast<HANDLE>(static_cast<std::uintptr_t>(handleValue));
            bool verified = false;
            if (SUCCEEDED(device->OpenSharedResource(handle, __uuidof(ID3D11Resource), reinterpret_cast<void**>(&resource))) && resource &&
                SUCCEEDED(resource->QueryInterface(__uuidof(ID3D11Texture2D), reinterpret_cast<void**>(&texture))) && texture)
            {
                D3D11_TEXTURE2D_DESC desc{};
                texture->GetDesc(&desc);
                if (desc.Width == 1 && desc.Height == 1 && desc.SampleDesc.Count == 1 &&
                    (desc.Format == DXGI_FORMAT_R8G8B8A8_UNORM || desc.Format == DXGI_FORMAT_B8G8R8A8_UNORM))
                {
                    D3D11_TEXTURE2D_DESC sd = desc;
                    sd.BindFlags = 0;
                    sd.MiscFlags = 0;
                    sd.Usage = D3D11_USAGE_STAGING;
                    sd.CPUAccessFlags = D3D11_CPU_ACCESS_READ;
                    if (SUCCEEDED(device->CreateTexture2D(&sd, nullptr, &staging)) && staging)
                    {
                        context->CopyResource(staging, texture);
                        D3D11_MAPPED_SUBRESOURCE mapped{};
                        if (SUCCEEDED(context->Map(staging, 0, D3D11_MAP_READ, 0, &mapped)) && mapped.pData)
                        {
                            const auto* px = static_cast<const std::uint8_t*>(mapped.pData);
                            verified = px[0] == 0x7B && px[1] == 0x7B && px[2] == 0x7B && px[3] == 0xFF;
                            context->Unmap(staging, 0);
                        }
                    }
                }
            }
            ReleaseCom(staging);
            ReleaseCom(texture);
            ReleaseCom(resource);
            if (verified)
            {
                interopVerifiedToken_ = token;
                InterlockedExchange(reinterpret_cast<volatile LONG*>(&state_->hostInteropProbeAckToken), static_cast<LONG>(token));
                if (!interopVerifiedLogged_)
                {
                    interopVerifiedLogged_ = true;
                    std::cout << "D3D9Ex/D3D11 interop verification pixel passed on the OpenXR adapter.\\n";
                }
            }
            return verified;
        }

        void AckDirectFrame(std::uint32_t frameId)
        {
            if (HeaderValid() && frameId)
                InterlockedExchange(reinterpret_cast<volatile LONG*>(&state_->hostDirectConsumedFrameId), static_cast<LONG>(frameId));
        }
'''
text = text[:start] + correct + text[end:]
path.write_text(text, encoding="utf-8", newline="\n")
print("normalized host interop block")
