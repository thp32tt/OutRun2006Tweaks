// AArch64-to-C++ research arithmetic reference for the user-owned Quest APK.
// Derived only from frame-correction floating-point ops at ELF 0x10CBF6C..0x10CC2FC.
// NOT the original authored C++ and not a PCVR gameplay patch.
// ELF SHA-256: fa0f9db9b744515a9a1439741bc9806ad007470b621b88d22a0b8cbced6120b6
// Requires caller to validate camera mode and frame ownership, preserve guest state,
// and enforce normal + exception restoration around frame render.
#include <array>
#include <cmath>

namespace quest_research {
std::array<float,16> body_correction_from_guest_matrices(
   const std::array<float,16>& old_matrix, // guest +0xB0..+0xEC
   const std::array<float,16>& new_matrix) // guest +0xF0..+0x12C
{
  float s[32]{}; 
  float stack[128]{};
  std::array<float,16> result{};
  // ELF 0x10cbf6c
  s[2] = 0.0f;
  // ELF 0x10cbf74
  s[17] = old_matrix[0]; s[16] = old_matrix[1];
  // ELF 0x10cbf78
  s[14] = new_matrix[5];
  // ELF 0x10cbf7c
  s[5] = old_matrix[12]; s[19] = old_matrix[13];
  // ELF 0x10cbf80
  s[4] = new_matrix[13];
  // ELF 0x10cbf84
  s[0] = new_matrix[0]; s[8] = new_matrix[1];
  // ELF 0x10cbf88
  s[1] = new_matrix[4];
  // ELF 0x10cbf8c
  s[18] = old_matrix[4]; s[7] = old_matrix[5];
  // ELF 0x10cbf90
  stack[84] = s[4];
  // ELF 0x10cbf94
  s[3] = s[16] * s[19];
  // ELF 0x10cbf98
  s[21] = old_matrix[8]; s[22] = old_matrix[9];
  // ELF 0x10cbf9c
  s[6] = s[8] * s[4];
  // ELF 0x10cbfa0
  s[20] = s[14] * s[4];
  // ELF 0x10cbfa4
  s[31] = new_matrix[12];
  // ELF 0x10cbfa8
  s[4] = s[7] * s[19];
  // ELF 0x10cbfac
  stack[56] = s[19];
  // ELF 0x10cbfb0
  s[10] = new_matrix[14];
  // ELF 0x10cbfb4
  s[23] = s[22] * s[19];
  // ELF 0x10cbfb8
  stack[80] = s[31];
  // ELF 0x10cbfbc
  s[26] = std::fma(s[1], s[17], s[2]);
  // ELF 0x10cbfc0
  s[25] = std::fma(s[17], s[5], s[3]);
  // ELF 0x10cbfc4
  s[27] = std::fma(s[0], s[16], s[2]);
  // ELF 0x10cbfc8
  s[29] = std::fma(s[0], s[31], s[6]);
  // ELF 0x10cbfcc
  s[30] = std::fma(s[1], s[31], s[20]);
  // ELF 0x10cbfd0
  s[13] = new_matrix[2];
  // ELF 0x10cbfd4
  s[31] = std::fma(s[18], s[5], s[4]);
  // ELF 0x10cbfd8
  s[3] = old_matrix[14]; s[4] = old_matrix[15];
  // ELF 0x10cbfdc
  s[19] = old_matrix[2]; s[6] = old_matrix[3];
  // ELF 0x10cbfe0
  s[28] = std::fma(s[1], s[16], s[2]);
  // ELF 0x10cbfe4
  s[24] = std::fma(s[0], s[17], s[2]);
  // ELF 0x10cbfe8
  stack[72] = s[8]; stack[76] = s[0];
  // ELF 0x10cbff0
  stack[48] = s[5]; stack[52] = s[4];
  // ELF 0x10cbff4
  s[4] = std::fma(s[21], s[5], s[23]);
  // ELF 0x10cbff8
  s[5] = new_matrix[8];
  // ELF 0x10cbffc
  s[25] = std::fma(s[19], s[3], s[25]);
  // ELF 0x10cc000
  stack[88] = s[6];
  // ELF 0x10cc004
  s[23] = std::fma(s[14], s[18], s[26]);
  // ELF 0x10cc008
  s[26] = std::fma(s[8], s[7], s[27]);
  // ELF 0x10cc00c
  s[9] = std::fma(s[14], s[7], s[28]);
  // ELF 0x10cc010
  s[6] = s[3];
  // ELF 0x10cc014
  s[28] = std::fma(s[13], s[10], s[29]);
  // ELF 0x10cc018
  stack[44] = s[3];
  // ELF 0x10cc01c
  s[24] = std::fma(s[8], s[18], s[24]);
  // ELF 0x10cc020
  stack[96] = s[4]; stack[100] = s[10];
  // ELF 0x10cc024
  s[20] = old_matrix[6]; s[4] = old_matrix[7];
  // ELF 0x10cc028
  s[29] = std::fma(s[0], s[25], -s[2]);
  // ELF 0x10cc02c
  s[11] = std::fma(s[0], s[19], s[2]);
  // ELF 0x10cc030
  stack[60] = s[1]; stack[64] = s[14];
  // ELF 0x10cc034
  stack[68] = s[13];
  // ELF 0x10cc040
  stack[32] = s[4];
  // ELF 0x10cc044
  s[4] = s[10];
  // ELF 0x10cc048
  s[27] = std::fma(s[20], s[3], s[31]);
  // ELF 0x10cc04c
  s[3] = new_matrix[6];
  // ELF 0x10cc050
  s[10] = std::fma(s[5], s[25], -s[2]);
  // ELF 0x10cc054
  s[31] = std::fma(s[1], s[25], -s[2]);
  // ELF 0x10cc058
  s[25] = std::fma(s[25], s[2], -s[2]);
  // ELF 0x10cc05c
  s[24] = std::fma(s[13], s[21], s[24]);
  // ELF 0x10cc064
  s[9] = std::fma(s[3], s[22], s[9]);
  // ELF 0x10cc068
  s[15] = std::fma(s[3], s[4], s[30]);
  // ELF 0x10cc06c
  s[4] = new_matrix[9];
  // ELF 0x10cc070
  s[30] = std::fma(s[3], s[21], s[23]);
  // ELF 0x10cc074
  s[29] = std::fma(s[8], s[27], -s[29]);
  // ELF 0x10cc078
  s[31] = std::fma(s[14], s[27], -s[31]);
  // ELF 0x10cc07c
  s[0] = std::fma(s[4], s[27], -s[10]);
  // ELF 0x10cc080
  s[12] = std::fma(s[28], s[2], -s[24]);
  // ELF 0x10cc084
  s[23] = old_matrix[10]; s[24] = old_matrix[11];
  // ELF 0x10cc088
  s[9] = std::fma(s[15], s[2], -s[9]);
  // ELF 0x10cc08c
  stack[40] = s[0];
  // ELF 0x10cc090
  s[0] = std::fma(s[27], s[2], -s[25]);
  // ELF 0x10cc094
  s[10] = std::fma(s[17], s[12], s[2]);
  // ELF 0x10cc098
  s[25] = std::fma(s[8], s[20], s[11]);
  // ELF 0x10cc09c
  s[11] = std::fma(s[16], s[12], s[2]);
  // ELF 0x10cc0a0
  s[8] = std::fma(s[19], s[12], s[2]);
  // ELF 0x10cc0a4
  stack[36] = s[0];
  // ELF 0x10cc0a8
  s[0] = stack[96];
  // ELF 0x10cc0ac
  s[25] = std::fma(s[13], s[23], s[25]);
  // ELF 0x10cc0b0
  stack[96] = s[3];
  // ELF 0x10cc0b4
  s[27] = std::fma(s[23], s[6], s[0]);
  // ELF 0x10cc0b8
  s[6] = std::fma(s[13], s[22], s[26]);
  // ELF 0x10cc0bc
  s[0] = stack[88];
  // ELF 0x10cc0c0
  s[26] = std::fma(s[15], s[2], -s[30]);
  // ELF 0x10cc0c4
  s[30] = std::fma(s[1], s[19], s[2]);
  // ELF 0x10cc0c8
  stack[88] = s[4]; stack[92] = s[5];
  // ELF 0x10cc0cc
  s[12] = std::fma(s[0], s[12], s[2]);
  // ELF 0x10cc0d0
  s[6] = std::fma(s[28], s[2], -s[6]);
  // ELF 0x10cc0d4
  s[29] = std::fma(s[13], s[27], -s[29]);
  // ELF 0x10cc0d8
  s[1] = std::fma(s[18], s[26], s[10]);
  // ELF 0x10cc0dc
  s[30] = std::fma(s[14], s[20], s[30]);
  // ELF 0x10cc0e0
  s[14] = std::fma(s[5], s[17], s[2]);
  // ELF 0x10cc0e4
  s[10] = std::fma(s[17], s[6], s[2]);
  // ELF 0x10cc0e8
  stack[28] = s[1];
  // ELF 0x10cc0ec
  s[1] = std::fma(s[7], s[26], s[11]);
  // ELF 0x10cc0f0
  s[11] = std::fma(s[16], s[6], s[2]);
  // ELF 0x10cc0f4
  s[14] = std::fma(s[4], s[18], s[14]);
  // ELF 0x10cc0f8
  stack[24] = s[1];
  // ELF 0x10cc0fc
  s[1] = std::fma(s[20], s[26], s[8]);
  // ELF 0x10cc100
  s[8] = s[0];
  // ELF 0x10cc104
  s[11] = std::fma(s[7], s[9], s[11]);
  // ELF 0x10cc108
  stack[20] = s[1];
  // ELF 0x10cc10c
  s[1] = stack[32];
  // ELF 0x10cc110
  s[26] = std::fma(s[1], s[26], s[12]);
  // ELF 0x10cc114
  s[12] = std::fma(s[3], s[23], s[30]);
  // ELF 0x10cc118
  s[30] = std::fma(s[28], s[2], -s[25]);
  // ELF 0x10cc11c
  s[28] = s[29] - s[28];
  // ELF 0x10cc120
  s[29] = std::fma(s[3], s[27], -s[31]);
  // ELF 0x10cc124
  s[25] = std::fma(s[18], s[9], s[10]);
  // ELF 0x10cc128
  s[10] = new_matrix[10];
  // ELF 0x10cc12c
  stack[16] = s[26];
  // ELF 0x10cc130
  s[26] = std::fma(s[19], s[6], s[2]);
  // ELF 0x10cc134
  s[6] = std::fma(s[0], s[6], s[2]);
  // ELF 0x10cc138
  s[31] = std::fma(s[17], s[30], s[2]);
  // ELF 0x10cc13c
  s[13] = std::fma(s[19], s[30], s[2]);
  // ELF 0x10cc140
  s[29] = s[29] - s[15];
  // ELF 0x10cc144
  s[14] = std::fma(s[10], s[21], s[14]);
  // ELF 0x10cc148
  s[3] = std::fma(s[20], s[9], s[26]);
  // ELF 0x10cc14c
  s[0] = stack[84];
  // ELF 0x10cc150
  s[26] = s[4] * s[0];
  // ELF 0x10cc154
  s[0] = std::fma(s[1], s[9], s[6]);
  // ELF 0x10cc158
  s[6] = s[1];
  // ELF 0x10cc15c
  s[9] = std::fma(s[15], s[2], -s[12]);
  // ELF 0x10cc160
  s[12] = std::fma(s[16], s[30], s[2]);
  // ELF 0x10cc164
  s[30] = std::fma(s[8], s[30], s[2]);
  // ELF 0x10cc168
  s[15] = std::fma(s[5], s[19], s[2]);
  // ELF 0x10cc16c
  s[8] = std::fma(s[8], s[28], s[2]);
  // ELF 0x10cc170
  stack[8] = s[0]; stack[12] = s[3];
  // ELF 0x10cc174
  s[0] = stack[80];
  // ELF 0x10cc178
  s[31] = std::fma(s[18], s[9], s[31]);
  // ELF 0x10cc17c
  s[12] = std::fma(s[7], s[9], s[12]);
  // ELF 0x10cc180
  s[26] = std::fma(s[5], s[0], s[26]);
  // ELF 0x10cc184
  s[0] = std::fma(s[17], s[2], s[2]);
  // ELF 0x10cc188
  s[17] = std::fma(s[17], s[28], s[2]);
  // ELF 0x10cc18c
  s[13] = std::fma(s[20], s[9], s[13]);
  // ELF 0x10cc190
  s[30] = std::fma(s[1], s[9], s[30]);
  // ELF 0x10cc194
  s[9] = std::fma(s[5], s[16], s[2]);
  // ELF 0x10cc198
  s[1] = stack[100];
  // ELF 0x10cc19c
  s[15] = std::fma(s[4], s[20], s[15]);
  // ELF 0x10cc1a0
  s[0] = std::fma(s[18], s[2], s[0]);
  // ELF 0x10cc1a4
  s[17] = std::fma(s[18], s[29], s[17]);
  // ELF 0x10cc1a8
  s[18] = std::fma(s[10], s[1], s[26]);
  // ELF 0x10cc1ac
  s[26] = std::fma(s[16], s[2], s[2]);
  // ELF 0x10cc1b0
  s[16] = std::fma(s[16], s[28], s[2]);
  // ELF 0x10cc1b4
  s[28] = std::fma(s[19], s[28], s[2]);
  // ELF 0x10cc1b8
  s[9] = std::fma(s[4], s[7], s[9]);
  // ELF 0x10cc1bc
  s[3] = stack[36]; s[4] = stack[40];
  // ELF 0x10cc1c0
  s[19] = std::fma(s[19], s[2], s[2]);
  // ELF 0x10cc1c4
  s[1] = std::fma(s[6], s[29], s[8]);
  // ELF 0x10cc1c8
  s[8] = std::fma(s[18], s[2], -s[14]);
  // ELF 0x10cc1cc
  s[26] = std::fma(s[7], s[2], s[26]);
  // ELF 0x10cc1d0
  s[7] = std::fma(s[7], s[29], s[16]);
  // ELF 0x10cc1d4
  s[28] = std::fma(s[20], s[29], s[28]);
  // ELF 0x10cc1d8
  s[29] = std::fma(s[10], s[27], -s[4]);
  // ELF 0x10cc1dc
  s[27] = std::fma(s[27], s[2], -s[3]);
  // ELF 0x10cc1e0
  s[3] = stack[24]; s[4] = stack[28];
  // ELF 0x10cc1e4
  s[16] = std::fma(s[10], s[22], s[9]);
  // ELF 0x10cc1e8
  s[19] = std::fma(s[20], s[2], s[19]);
  // ELF 0x10cc1ec
  s[20] = std::fma(s[10], s[23], s[15]);
  // ELF 0x10cc1f0
  s[0] = std::fma(s[21], s[2], s[0]);
  // ELF 0x10cc1f4
  s[9] = std::fma(s[21], s[8], s[4]);
  // ELF 0x10cc1f8
  s[14] = std::fma(s[22], s[8], s[3]);
  // ELF 0x10cc1fc
  s[3] = stack[16]; s[4] = stack[20];
  // ELF 0x10cc200
  s[26] = std::fma(s[22], s[2], s[26]);
  // ELF 0x10cc204
  s[16] = std::fma(s[18], s[2], -s[16]);
  // ELF 0x10cc208
  s[20] = std::fma(s[18], s[2], -s[20]);
  // ELF 0x10cc20c
  s[18] = s[29] - s[18];
  // ELF 0x10cc210
  s[0] = s[0] + s[2];
  // ELF 0x10cc214
  s[15] = std::fma(s[23], s[8], s[4]);
  // ELF 0x10cc218
  s[8] = std::fma(s[24], s[8], s[3]);
  // ELF 0x10cc21c
  s[3] = stack[8]; s[4] = stack[12];
  // ELF 0x10cc220
  s[25] = std::fma(s[21], s[16], s[25]);
  // ELF 0x10cc224
  s[29] = std::fma(s[22], s[16], s[11]);
  // ELF 0x10cc228
  s[5] = std::fma(s[22], s[18], s[7]);
  // ELF 0x10cc22c
  s[7] = s[26] + s[2];
  // ELF 0x10cc230
  s[11] = std::fma(s[23], s[16], s[4]);
  // ELF 0x10cc234
  s[6] = std::fma(s[24], s[16], s[3]);
  // ELF 0x10cc238
  s[16] = std::fma(s[23], s[2], s[19]);
  // ELF 0x10cc23c
  s[19] = std::fma(s[21], s[20], s[31]);
  // ELF 0x10cc240
  s[31] = std::fma(s[22], s[20], s[12]);
  // ELF 0x10cc244
  s[22] = 1.000000000000000000e+00f;
  // ELF 0x10cc248
  s[12] = std::fma(s[23], s[20], s[13]);
  // ELF 0x10cc24c
  s[20] = std::fma(s[24], s[20], s[30]);
  // ELF 0x10cc250
  s[4] = std::fma(s[21], s[18], s[17]);
  // ELF 0x10cc254
  s[17] = std::fma(s[23], s[18], s[28]);
  // ELF 0x10cc258
  s[18] = std::fma(s[24], s[18], s[1]);
  // ELF 0x10cc25c
  s[2] = s[16] + s[2];
  // ELF 0x10cc260
  s[22] = s[27] + s[22];
  // ELF 0x10cc264
  s[21] = stack[44]; s[1] = stack[48];
  // ELF 0x10cc268
  s[30] = stack[52]; s[3] = stack[56];
  // ELF 0x10cc26c
  s[16] = std::fma(s[1], s[0], s[9]);
  // ELF 0x10cc270
  s[24] = std::fma(s[21], s[0], s[15]);
  // ELF 0x10cc274
  s[23] = std::fma(s[3], s[0], s[14]);
  // ELF 0x10cc278
  s[0] = std::fma(s[30], s[0], s[8]);
  // ELF 0x10cc27c
  s[25] = std::fma(s[1], s[7], s[25]);
  // ELF 0x10cc280
  s[26] = std::fma(s[3], s[7], s[29]);
  // ELF 0x10cc284
  s[27] = std::fma(s[21], s[7], s[11]);
  // ELF 0x10cc288
  s[6] = std::fma(s[30], s[7], s[6]);
  // ELF 0x10cc28c
  s[7] = std::fma(s[1], s[2], s[19]);
  // ELF 0x10cc290
  s[19] = std::fma(s[3], s[2], s[31]);
  // ELF 0x10cc294
  s[28] = std::fma(s[21], s[2], s[12]);
  // ELF 0x10cc298
  s[2] = std::fma(s[30], s[2], s[20]);
  // ELF 0x10cc29c
  s[4] = std::fma(s[1], s[22], s[4]);
  // ELF 0x10cc2a0
  s[1] = std::fma(s[3], s[22], s[5]);
  // ELF 0x10cc2a4
  s[3] = std::fma(s[21], s[22], s[17]);
  // ELF 0x10cc2a8
  s[5] = std::fma(s[30], s[22], s[18]);
  // ELF 0x10cc2e0
  result[0] = s[16]; result[1] = s[23];
  // ELF 0x10cc2e4
  result[2] = s[24]; result[3] = s[0];
  // ELF 0x10cc2e8
  result[4] = s[25]; result[5] = s[26];
  // ELF 0x10cc2ec
  result[6] = s[27]; result[7] = s[6];
  // ELF 0x10cc2f0
  result[8] = s[7]; result[9] = s[19];
  // ELF 0x10cc2f4
  result[10] = s[28]; result[11] = s[2];
  // ELF 0x10cc2f8
  result[12] = s[4]; result[13] = s[1];
  // ELF 0x10cc2fc
  result[14] = s[3]; result[15] = s[5];
  return result;
}
} // namespace quest_research