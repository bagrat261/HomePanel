#import <UIKit/UIKit.h>
@interface HPVideoView : UIView
@property(nonatomic, copy) void (^failure)(NSString *message);
@property(nonatomic, copy) void (^frameReady)(NSUInteger identity);
- (void)consume:(NSData *)data;
- (void)reset;
@end
