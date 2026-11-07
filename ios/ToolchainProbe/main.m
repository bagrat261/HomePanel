#import <UIKit/UIKit.h>
#import <AVFoundation/AVFoundation.h>
#import <CoreMedia/CoreMedia.h>

int main(int argc, char *argv[]) {
    @autoreleasepool {
        AVSampleBufferDisplayLayer *layer = [AVSampleBufferDisplayLayer layer];
        [layer flushAndRemoveImage];
        CMTime time = CMTimeMake(1, 15);
        if (!CMTIME_IS_VALID(time)) return 1;
        return UIApplicationMain(argc, argv, nil, nil);
    }
}
