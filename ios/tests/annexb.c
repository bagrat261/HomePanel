#include "../HomePanel/HPAnnexB.h"
#include <assert.h>

int main(void) {
    const uint8_t stream[] = {0, 0, 0, 1, 0x67, 0x42, 0, 0, 1, 0x65, 0x80};
    size_t offset = 99, prefix = 99;
    assert(hp_annexb_start(stream, sizeof stream, 0, &offset, &prefix));
    assert(offset == 0 && prefix == 4);
    assert(hp_annexb_start(stream, sizeof stream, 4, &offset, &prefix));
    assert(offset == 6 && prefix == 3);
    for (size_t size = 0; size < 4; ++size) {
        assert(!hp_annexb_start(stream, size, 0, &offset, &prefix));
    }
    assert(!hp_annexb_start(NULL, 5, 0, &offset, &prefix));
    assert(!hp_annexb_start(stream, sizeof stream, sizeof stream, &offset, &prefix));
    assert(hp_slice_starts_picture(stream + 9, 2));
    const uint8_t continuation[] = {0x61, 0x40};
    assert(!hp_slice_starts_picture(continuation, sizeof continuation));
    assert(!hp_slice_starts_picture(continuation, 1));
    const uint8_t metadata[] = {6, 5, 18, 'H','o','m','e','P','a','n','e','l','F','r','a','m','e','I','D','4','2',0x80};
    assert(hp_frame_id(metadata, sizeof metadata) == 42);
    assert(hp_frame_id(metadata, sizeof metadata - 1) == 0);
    assert(hp_frame_id(NULL, 0) == 0);
    return 0;
}
