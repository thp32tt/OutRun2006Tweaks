#pragma once

// Bounded SM3 CALL/LABEL/RET inline expansion. This runs before the existing
// shader register-provenance, derivative, IF/REP and native Draw validators.
// Unsupported or malformed call graphs must return to the original D3D9 Draw.
#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <map>
#include <utility>
#include <vector>

namespace outrun::vr::dx11 {

template <class Instruction, class DecodeLabel, class ValidateBoolean, class ExecutableBody>
bool native_sm3_expand_subroutines(
    const std::vector<Instruction>& instructions,
    std::uint32_t callOpcode,
    std::uint32_t conditionalCallOpcode,
    std::uint32_t labelOpcode,
    std::uint32_t returnOpcode,
    std::uint32_t ifOpcode,
    std::uint32_t endIfOpcode,
    DecodeLabel decodeLabel,
    ValidateBoolean validateBoolean,
    ExecutableBody executableBody,
    std::vector<Instruction>& expanded) {
    expanded.clear();
    constexpr std::size_t kMaxInstructions = 512u;
    constexpr std::size_t kMaxCallDepth = 8u;
    if (instructions.empty() || instructions.size() > kMaxInstructions)
        return false;

    bool hasCallGraph = false;
    for (const auto& ins : instructions) {
        if (ins.opcode == callOpcode ||
            ins.opcode == conditionalCallOpcode ||
            ins.opcode == labelOpcode || ins.opcode == returnOpcode) {
            hasCallGraph = true;
            break;
        }
    }
    if (!hasCallGraph) {
        expanded = instructions;
        return true;
    }

    std::size_t mainReturn = instructions.size();
    for (std::size_t i = 0; i < instructions.size(); ++i) {
        if (instructions[i].opcode == labelOpcode) {
            // Main must terminate with RET immediately before label blocks.
            if (i == 0 || mainReturn != i - 1u) return false;
            break;
        }
        if (instructions[i].opcode == returnOpcode) {
            if (mainReturn != instructions.size() ||
                !instructions[i].operandTokens.empty() ||
                (instructions[i].instructionToken & 0xf0ff0000u) != 0u)
                return false;
            mainReturn = i;
        } else if (mainReturn != instructions.size()) {
            return false;
        }
    }
    if (mainReturn == instructions.size() ||
        mainReturn + 1u == instructions.size()) return false;

    struct Range { std::size_t begin; std::size_t end; };
    std::map<unsigned, Range> labels;
    for (std::size_t i = mainReturn + 1u; i < instructions.size();) {
        const auto& entry = instructions[i];
        unsigned label = 0u;
        if (entry.opcode != labelOpcode ||
            entry.operandTokens.size() != 1u ||
            (entry.instructionToken & 0xf0ff0000u) != 0u ||
            !decodeLabel(entry.operandTokens[0], label) ||
            labels.count(label) != 0u)
            return false;
        const auto begin = ++i;
        while (i < instructions.size() &&
               instructions[i].opcode != returnOpcode) {
            if (instructions[i].opcode == labelOpcode ||
                !executableBody(instructions[i].opcode))
                return false;
            ++i;
        }
        if (i == instructions.size() || begin == i ||
            !instructions[i].operandTokens.empty() ||
            (instructions[i].instructionToken & 0xf0ff0000u) != 0u)
            return false;
        labels.emplace(label, Range{begin, i});
        ++i;
    }

    std::vector<unsigned> callStack;
    std::function<bool(std::size_t, std::size_t)> expandRange;
    expandRange = [&](std::size_t first, std::size_t last) -> bool {
        for (std::size_t i = first; i < last; ++i) {
            const auto& ins = instructions[i];
            if (ins.opcode == callOpcode ||
                ins.opcode == conditionalCallOpcode) {
                const bool conditional = ins.opcode == conditionalCallOpcode;
                unsigned target = 0u;
                if (ins.operandTokens.size() != (conditional ? 2u : 1u) ||
                    (ins.instructionToken & 0xf0ff0000u) != 0u ||
                    !decodeLabel(ins.operandTokens[0], target) ||
                    (conditional &&
                     (ifOpcode == 0u || endIfOpcode == 0u ||
                      !validateBoolean(ins.operandTokens[1]))))
                    return false;
                const auto found = labels.find(target);
                if (found == labels.end() ||
                    callStack.size() >= kMaxCallDepth ||
                    std::find(callStack.begin(), callStack.end(), target) !=
                        callStack.end())
                    return false;

                // CALLNZ l#, b# executes its body only when the game's
                // DEFB/live b# is true. Materialize IF/ENDIF as real SM3
                // operations, preserving flow-dependent TEMP/output writes,
                // derivative safety and per-Draw boolean bindings downstream.
                if (conditional) {
                    if (expanded.size() + 2u > kMaxInstructions)
                        return false;
                    Instruction begin = ins;
                    begin.opcode = ifOpcode;
                    begin.instructionToken = (1u << 24u) | ifOpcode;
                    begin.operandTokens = {ins.operandTokens[1]};
                    expanded.push_back(std::move(begin));
                }
                callStack.push_back(target);
                const bool ok = expandRange(found->second.begin,
                                            found->second.end);
                callStack.pop_back();
                if (!ok) return false;
                if (conditional) {
                    if (expanded.size() >= kMaxInstructions)
                        return false;
                    Instruction end = ins;
                    end.opcode = endIfOpcode;
                    end.instructionToken = endIfOpcode;
                    end.operandTokens.clear();
                    expanded.push_back(std::move(end));
                }
            } else {
                if (ins.opcode == labelOpcode ||
                    ins.opcode == returnOpcode ||
                    ins.opcode == conditionalCallOpcode ||
                    expanded.size() >= kMaxInstructions)
                    return false;
                expanded.push_back(ins);
            }
        }
        return true;
    };
    if (!expandRange(0u, mainReturn) || expanded.empty()) {
        expanded.clear();
        return false;
    }
    return true;
}

// Preserve the established unconditional-only API. Existing callers keep
// rejecting CALLNZ until they explicitly provide boolean register validation
// and native IF/ENDIF lowering.
template <class Instruction, class DecodeLabel, class ExecutableBody>
bool native_sm3_expand_subroutines(
    const std::vector<Instruction>& instructions,
    std::uint32_t callOpcode,
    std::uint32_t conditionalCallOpcode,
    std::uint32_t labelOpcode,
    std::uint32_t returnOpcode,
    DecodeLabel decodeLabel,
    ExecutableBody executableBody,
    std::vector<Instruction>& expanded) {
    return native_sm3_expand_subroutines(
        instructions, callOpcode, conditionalCallOpcode, labelOpcode,
        returnOpcode, 0u, 0u, decodeLabel,
        [](std::uint32_t) noexcept { return false; },
        executableBody, expanded);
}

} // namespace outrun::vr::dx11
