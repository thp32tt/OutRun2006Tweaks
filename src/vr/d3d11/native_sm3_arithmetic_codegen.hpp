#pragma once

// Portable HLSL emitter shared by the native D3D9 SM3 materializer and
// its compile/run regression. Only validated SM3 register operands reach it.
#include <array>
#include <string>

namespace outrun::vr::dx11 {

enum class NativeSm3ArithmeticOpcode {
    Move, Add, Subtract, Multiply, MultiplyAdd, Dot3, Dot4, Minimum, Maximum,
    Absolute, Fraction, SetLessThan, SetGreaterEqual, Compare
};

// Preserve lane masks and scalar-dot replication. Unsupported operand counts,
// empty expressions or unknown opcodes fail closed before the HLSL compiler.
inline bool append_native_sm3_arithmetic(
    std::string& translated, NativeSm3ArithmeticOpcode opcode,
    const std::string& destination, unsigned mask,
    const std::array<std::string, 3>& sources,
    unsigned sourceCount, unsigned ordinal) {
    if (destination.empty() || (mask & ~0x0fu) || mask == 0u)
        return false;
    const auto validSources = [&](unsigned expected) {
        if (sourceCount != expected) return false;
        for (unsigned i = 0; i < expected; ++i)
            if (sources[i].empty()) return false;
        return true;
    };
    std::string expression;
    switch (opcode) {
    case NativeSm3ArithmeticOpcode::Move:
        if (!validSources(1u)) return false;
        expression = sources[0]; break;
    case NativeSm3ArithmeticOpcode::Absolute:
    case NativeSm3ArithmeticOpcode::Fraction:
        if (!validSources(1u)) return false;
        expression = std::string(
            opcode == NativeSm3ArithmeticOpcode::Absolute ? "abs(" : "frac(") +
            sources[0] + ")"; break;
    case NativeSm3ArithmeticOpcode::Add:
    case NativeSm3ArithmeticOpcode::Subtract:
    case NativeSm3ArithmeticOpcode::Multiply:
    case NativeSm3ArithmeticOpcode::Minimum:
    case NativeSm3ArithmeticOpcode::Maximum:
        if (!validSources(2u)) return false;
        if (opcode == NativeSm3ArithmeticOpcode::Minimum ||
            opcode == NativeSm3ArithmeticOpcode::Maximum)
            expression = std::string(
                opcode == NativeSm3ArithmeticOpcode::Minimum ? "min(" : "max(") +
                sources[0] + ", " + sources[1] + ")";
        else {
            const char* operation =
                opcode == NativeSm3ArithmeticOpcode::Add ? " + " :
                opcode == NativeSm3ArithmeticOpcode::Subtract ? " - " : " * ";
            expression = "(" + sources[0] + operation + sources[1] + ")";
        }
        break;
    case NativeSm3ArithmeticOpcode::MultiplyAdd:
        if (!validSources(3u)) return false;
        expression = "((" + sources[0] + " * " + sources[1] +
                     ") + " + sources[2] + ")";
        break;
    case NativeSm3ArithmeticOpcode::SetLessThan:
    case NativeSm3ArithmeticOpcode::SetGreaterEqual: {
        if (!validSources(2u)) return false;
        expression = "float4(";
        constexpr char lanes[] = "xyzw";
        for (unsigned lane = 0; lane < 4u; ++lane) {
            if (lane) expression += ", ";
            const char component = lanes[lane];
            expression += "((" + sources[0] + ")." + component +
                (opcode == NativeSm3ArithmeticOpcode::SetLessThan
                    ? " < (" : " >= (") + sources[1] + ")." +
                component + " ? 1.0f : 0.0f)";
        }
        expression += ")";
        break;
    }
    case NativeSm3ArithmeticOpcode::Compare: {
        if (!validSources(3u)) return false;
        expression = "float4(";
        constexpr char lanes[] = "xyzw";
        for (unsigned lane = 0; lane < 4u; ++lane) {
            if (lane) expression += ", ";
            const char component = lanes[lane];
            expression += "((" + sources[0] + ")." + component +
                " >= 0.0f ? (" + sources[1] + ")." + component +
                " : (" + sources[2] + ")." + component + ")";
        }
        expression += ")";
        break;
    }
    case NativeSm3ArithmeticOpcode::Dot3:
    case NativeSm3ArithmeticOpcode::Dot4: {
        if (!validSources(2u)) return false;
        const char* lanes = opcode == NativeSm3ArithmeticOpcode::Dot3
            ? ".xyz" : ".xyzw";
        const auto scalar =
            "dot((" + sources[0] + ")" + lanes + ", (" +
            sources[1] + ")" + lanes + ")";
        expression = "float4(" + scalar + ", " + scalar + ", " +
                     scalar + ", " + scalar + ")";
        break;
    }
    default:
        return false;
    }
    const auto temporary = "r283_value_" + std::to_string(ordinal);
    translated += "    float4 " + temporary + " = " + expression + ";\n";
    std::string lanes;
    const char xyzw[] = "xyzw";
    for (unsigned lane = 0; lane < 4u; ++lane)
        if ((mask & (1u << lane)) != 0u) lanes += xyzw[lane];
    translated += "    " + destination + "." + lanes + " = " +
                  temporary + "." + lanes + ";\n";
    return true;
}

} // namespace outrun::vr::dx11
