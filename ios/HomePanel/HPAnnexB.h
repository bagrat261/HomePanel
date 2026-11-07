#ifndef HP_ANNEX_B_H
#define HP_ANNEX_B_H
#include <stddef.h>
#include <stdint.h>
/* Returns the next start code, including a three- or four-byte prefix. */
int hp_annexb_start(const uint8_t *bytes, size_t count, size_t from, size_t *offset, size_t *prefix);
/* Parses first_mb_in_slice from an escaped NAL (including its header). */
int hp_slice_starts_picture(const uint8_t *nal, size_t count);
uint32_t hp_frame_id(const uint8_t *nal, size_t count);
#endif
