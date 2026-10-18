#pragma once

// Portable HLSL emitter shared by the native D3D9 SM3 materializer and
// its compile/run regression. Only validated SM3 register operands reach it.
#include <array>
#include <string>

namespace outrun::vr::dx11 {

enum class NativeSm3ArithmeticOpcode {
    Move, Add, Subtract, Multiply, MultiplyAdd, Dot3, Dot4, Minimum, Maximum,
    Absolute, Fraction, SetLessThan, SetGreaterEqual, Compare,
    Reciprocal, ReciprocalSquareRoot, Exponential2, Logarithm2,
    Power, LinearInterpolate, Normalize3, Cross3, Dot2Add
};

// Translate only D3D9 source modifiers with exact component-wise SM3
// semantics. Unknown address/predicate/depth-divide modes stay rejected by
// the bytecode materializer; no source modifier can silently be ignored.
inline bool append_native_sm3_source_modifier(std::string& operand,
                                              unsigned modifier) {
    if (operand.empty()) return false;
    const auto value = "(" + operand + ")";
    switch (modifier) {
    case 0u: break;                         // D3DSPSM_NONE
    case 1u: operand = "-(" + operand + ")"; break; // D3DSPSM_NEG
    case 2u: operand = "(" + value + " - 0.5f)"; break; // BIAS
    case 3u: operand = "-(" + value + " - 0.5f)"; break; // BIASNEG
    case 4u: operand = "(2.0f * " + value + " - 1.0f)"; break; // SIGN
    case 5u: operand = "-(2.0f * " + value + " - 1.0f)"; break; // SIGNNEG
    case 6u: operand = "(1.0f - " + value + ")"; break; // COMP
    case 7u: operand = "(2.0f * " + value + ")"; break; // X2
    case 8u: operand = "-(2.0f * " + value + ")"; break; // X2NEG
    case 11u: operand = "abs(" + operand + ")"; break; // ABS
    case 12u: operand = "-abs(" + operand + ")"; break; // ABSNEG
    default: return false; // DZ/DW/NOT and reserved modifier encodings
    }
    return true;
}

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
    case NativeSm3ArithmeticOpcode::Reciprocal:
    case NativeSm3ArithmeticOpcode::ReciprocalSquareRoot:
    case NativeSm3ArithmeticOpcode::Exponential2:
    case NativeSm3ArithmeticOpcode::Logarithm2: {
        if (!validSources(1u)) return false;
        const auto x = "((" + sources[0] + ").x)";
        const std::string scalar =
            opcode == NativeSm3ArithmeticOpcode::Reciprocal ? "(1.0f / " + x + ")" :
            opcode == NativeSm3ArithmeticOpcode::ReciprocalSquareRoot ? "rsqrt(abs(" + x + "))" :
            opcode == NativeSm3ArithmeticOpcode::Exponential2 ? "exp2(" + x + ")" :
            "log2(abs(" + x + "))";
        expression = "float4(" + scalar + ", " + scalar + ", " +
                     scalar + ", " + scalar + ")";
        break;
    }
    case NativeSm3ArithmeticOpcode::Normalize3: {
        if (!validSources(1u) || (mask & 8u)) return false;
        // SM3 nrm writes xyz; the undefined w lane must not be fabricated.
        expression = "float4(normalize((" + sources[0] +
                     ").xyz), 0.0f)";
        break;
    }
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
    case NativeSm3ArithmeticOpcode::LinearInterpolate:
        if (!validSources(3u)) return false;
        expression = "((" + sources[0] + " * " + sources[1] +
                     ") + ((1.0f - (" + sources[0] + ")) * " +
                     sources[2] + "))";
        break;
    case NativeSm3ArithmeticOpcode::Power: {
        if (!validSources(2u)) return false;
        const auto scalar = "pow(abs((" + sources[0] + ").x), (" +
                            sources[1] + ").x)";
        expression = "float4(" + scalar + ", " + scalar + ", " +
                     scalar + ", " + scalar + ")";
        break;
    }
    case NativeSm3ArithmeticOpcode::Cross3:
        if (!validSources(2u) || (mask & 8u)) return false;
        expression = "float4(cross((" + sources[0] + ").xyz, (" +
                     sources[1] + ").xyz), 0.0f)";
        break;
    case NativeSm3ArithmeticOpcode::Dot2Add: {
        if (!validSources(3u)) return false;
        const auto scalar = "(dot((" + sources[0] + ").xy, (" +
                            sources[1] + ").xy) + (" + sources[2] + ").x)";
        expression = "float4(" + scalar + ", " + scalar + ", " +
                     scalar + ", " + scalar + ")";
        break;
    }
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
