#import "HPVideoView.h"
#import "HPAnnexB.h"
#import <AVFoundation/AVFoundation.h>
#import <CoreMedia/CoreMedia.h>

@implementation HPVideoView {
    NSMutableData *_pending, *_accessUnit;
    NSData *_sps, *_pps;
    CMVideoFormatDescriptionRef _format;
    BOOL _hasSlice, _idr, _waitingIDR;
}
+ (Class)layerClass { return [AVSampleBufferDisplayLayer class]; }
- (instancetype)initWithFrame:(CGRect)frame {
    if ((self = [super initWithFrame:frame])) {
        _pending = [NSMutableData data]; _accessUnit = [NSMutableData data];
        _waitingIDR = YES;
        ((AVSampleBufferDisplayLayer *)self.layer).videoGravity = AVLayerVideoGravityResizeAspect;
        self.backgroundColor = [UIColor blackColor];
    }
    return self;
}
- (void)dealloc { if (_format) CFRelease(_format); }
- (void)reset {
    NSAssert([NSThread isMainThread], @"Video is main-thread confined");
    [_pending setLength:0]; [_accessUnit setLength:0];
    _hasSlice = NO; _idr = NO; _waitingIDR = YES;
    _sps = nil; _pps = nil;
    if (_format) { CFRelease(_format); _format = NULL; }
    [(AVSampleBufferDisplayLayer *)self.layer flushAndRemoveImage];
}
- (void)configure {
    if (!_sps || !_pps) return;
    if (_format) { CFRelease(_format); _format = NULL; }
    const uint8_t *sets[] = {_sps.bytes, _pps.bytes};
    size_t sizes[] = {_sps.length, _pps.length};
    OSStatus status = CMVideoFormatDescriptionCreateFromH264ParameterSets(kCFAllocatorDefault, 2, sets, sizes, 4, &_format);
    if (status && self.failure) self.failure(@"Неподдерживаемый формат видео");
}
- (void)emitFrame {
    if (!_hasSlice) { [_accessUnit setLength:0]; return; }
    AVSampleBufferDisplayLayer *layer = (AVSampleBufferDisplayLayer *)self.layer;
    if (layer.status == AVQueuedSampleBufferRenderingStatusFailed) {
        [layer flushAndRemoveImage]; _waitingIDR = YES;
    }
    if (!_format || (_waitingIDR && !_idr)) goto clear;
    if (!layer.readyForMoreMediaData) {
        [layer flush]; _waitingIDR = YES; goto clear;
    }
    CMBlockBufferRef block = NULL;
    CMSampleBufferRef sample = NULL;
    size_t size = _accessUnit.length;
    OSStatus status = CMBlockBufferCreateWithMemoryBlock(kCFAllocatorDefault, NULL, size, kCFAllocatorDefault, NULL, 0, size, 0, &block);
    if (!status) status = CMBlockBufferReplaceDataBytes(_accessUnit.bytes, block, 0, size);
    CMSampleTimingInfo timing = {kCMTimeInvalid, kCMTimeInvalid, kCMTimeInvalid};
    if (!status) status = CMSampleBufferCreateReady(kCFAllocatorDefault, block, _format, 1, 1, &timing, 1, &size, &sample);
    if (!status) {
        CFArrayRef attachments = CMSampleBufferGetSampleAttachmentsArray(sample, YES);
        CFMutableDictionaryRef dict = (CFMutableDictionaryRef)CFArrayGetValueAtIndex(attachments, 0);
        CFDictionarySetValue(dict, kCMSampleAttachmentKey_DisplayImmediately, kCFBooleanTrue);
        [layer enqueueSampleBuffer:sample]; _waitingIDR = NO;
        if (self.frameReady) self.frameReady();
    } else { _waitingIDR = YES; if (self.failure) self.failure(@"Ошибка декодирования видео"); }
    if (sample) CFRelease(sample);
    if (block) CFRelease(block);
clear:
    [_accessUnit setLength:0]; _hasSlice = NO; _idr = NO;
}
- (void)acceptNAL:(NSData *)nal {
    if (nal.length < 1) return;
    const uint8_t *b = nal.bytes; unsigned type = b[0] & 31;
    if (type == 9) { [self emitFrame]; return; }
    if (type == 7 || type == 8) {
        [self emitFrame];
        NSData *previous = type == 7 ? _sps : _pps;
        if (![previous isEqualToData:nal]) {
            if (type == 7) _sps = nal; else _pps = nal;
            _waitingIDR = YES; [self configure];
        }
        return;
    }
    BOOL slice = type == 1 || type == 5;
    if (slice && _hasSlice && hp_slice_starts_picture(b, nal.length)) [self emitFrame];
    if (type != 1 && type != 5 && type != 6) return;
    if (_accessUnit.length + nal.length + 4 > 2 * 1024 * 1024) { [self reset]; return; }
    uint32_t length = CFSwapInt32HostToBig((uint32_t)nal.length);
    [_accessUnit appendBytes:&length length:4]; [_accessUnit appendData:nal];
    _hasSlice |= slice; _idr |= type == 5;
}
- (void)consume:(NSData *)data {
    NSAssert([NSThread isMainThread], @"Video is main-thread confined");
    if (_pending.length + data.length > 2 * 1024 * 1024) {
        [self reset]; if (self.failure) self.failure(@"Переполнение видеопотока; ожидается ключевой кадр"); return;
    }
    [_pending appendData:data];
    size_t start, prefix;
    if (!hp_annexb_start(_pending.bytes, _pending.length, 0, &start, &prefix)) return;
    if (start) { [_pending replaceBytesInRange:NSMakeRange(0, start) withBytes:NULL length:0]; start = 0; }
    size_t next, nextPrefix;
    while (hp_annexb_start(_pending.bytes, _pending.length, prefix, &next, &nextPrefix)) {
        if (next > prefix) [self acceptNAL:[_pending subdataWithRange:NSMakeRange(prefix, next - prefix)]];
        [_pending replaceBytesInRange:NSMakeRange(0, next) withBytes:NULL length:0];
        prefix = nextPrefix;
    }
}
@end
