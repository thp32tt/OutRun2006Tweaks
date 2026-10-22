// Live D3D9 shader-program acceptance: vs_3_0 EXPP/LOGP generate
// the higher-precision scalar EXP/LOG GPU math; ps_3_0 remains unsupported.
#include "../src/vr/d3d11/native_sm3_arithmetic_codegen.hpp"
#include <array>
#include <cassert>
#include <fstream>
#include <iterator>
#include <string>

using namespace outrun::vr::dx11;

int main() {
    const std::array<std::string, 3> sources{"game_vs_scalar", "", ""};
    std::string exp, log, pixel;
    assert(append_native_sm3_arithmetic(exp,
        NativeSm3ArithmeticOpcode::Exponential2, "r283_t0", 0x0fu,
        sources, 1u, 130u, true));
    assert(append_native_sm3_arithmetic(log,
        NativeSm3ArithmeticOpcode::Logarithm2, "r283_t1", 0x05u,
        sources, 1u, 131u, true));
    assert(exp.find("exp2(((game_vs_scalar).x))") != std::string::npos);
    assert(log.find("log2(abs(") != std::string::npos);
    assert(log.find("== 0.0f ? -3.402823466e+38f") != std::string::npos);
    assert(log.find("r283_t1.xz = r283_value_131.xz;") != std::string::npos);
    assert(append_native_sm3_arithmetic(pixel,
        NativeSm3ArithmeticOpcode::Logarithm2, "r283_t2", 0x01u,
        sources, 1u, 132u, false)); // Full LOG still legal in PS.
    assert(!append_native_sm3_arithmetic(pixel,
        NativeSm3ArithmeticOpcode::Exponential2, "r283_t2", 0u,
        sources, 1u, 133u, false)); // Invalid destination mask stays closed.
    // Guard the ACTUAL production SM3 compiler switch. The isolated emitter
    // cannot demonstrate an admitted live game shader without these cases.
    std::ifstream input("src/vr/d3d11/native_backend.cpp");
    assert(input && "Production live SM3 compiler source must be available");
    const std::string backend((std::istreambuf_iterator<char>(input)),
                               std::istreambuf_iterator<char>());
    const auto expp = backend.find("case D3DSIO_EXPP:");
    const auto logp = backend.find("case D3DSIO_LOGP:");
    assert(expp != std::string::npos && logp != std::string::npos);
    const auto expCase = backend.find("case D3DSIO_EXP:", expp);
    const auto logCase = backend.find("case D3DSIO_LOG:", logp);
    assert(expCase != std::string::npos && logCase != std::string::npos);
    const auto exppGuard = backend.substr(expp, expCase - expp);
    const auto logpGuard = backend.substr(logp, logCase - logp);
    assert(exppGuard.find("if (!vertexStage) return false;") != std::string::npos);
    assert(logpGuard.find("if (!vertexStage) return false;") != std::string::npos);
    assert(exppGuard.find("NativeSm3ArithmeticOpcode::Exponential2") != std::string::npos);
    assert(logpGuard.find("NativeSm3ArithmeticOpcode::Logarithm2") != std::string::npos);
    // A native opcode case is insufficient when R266 source-register role
    // decoding rejects it first. Guard the genuine upstream shader path.
    std::ifstream decoderFile("src/vr/d3d11/pipeline_translation.cpp");
    assert(decoderFile);
    const std::string decoder((std::istreambuf_iterator<char>(decoderFile)),
                               std::istreambuf_iterator<char>());
    const auto decodedExpp = decoder.find("case D3DSIO_EXPP:");
    const auto decodedLogp = decoder.find("case D3DSIO_LOGP:");
    assert(decodedExpp != std::string::npos && decodedLogp != std::string::npos);
    const auto sourcePlan = decoder.substr(decodedExpp,
        decoder.find("case D3DSIO_ADD:", decodedLogp) - decodedExpp);
    assert(sourcePlan.find("vertexStage && shaderMajor == 3u") != std::string::npos);
    assert(sourcePlan.find("PlanKind::Registers, 1u, 1u") != std::string::npos);
}
