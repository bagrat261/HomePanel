#include "HPAnnexB.h"
int hp_annexb_start(const uint8_t *b, size_t n, size_t from, size_t *o, size_t *p) {
    if (!b || !o || !p || from >= n) return 0;
    for (size_t i = from; n - i >= 3; ++i) {
        if (b[i] || b[i + 1]) continue;
        if (b[i + 2] == 1) { *o = i; *p = 3; return 1; }
        if (n - i >= 4 && b[i + 2] == 0 && b[i + 3] == 1) {
            *o = i; *p = 4; return 1;
        }
    }
    return 0;
}
int hp_slice_starts_picture(const uint8_t *nal, size_t count) {
    /* Unsigned Exp-Golomb zero is a leading 1 bit; no unescaping is
       needed before the very first bit following the one-byte NAL header. */
    return nal && count > 1 && (nal[1] & 0x80) != 0;
}
