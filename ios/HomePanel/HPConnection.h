#import <Foundation/Foundation.h>

@interface HPConnection : NSObject <NSURLSessionDataDelegate>
@property(nonatomic, copy) void (^bytes)(NSData *data);
@property(nonatomic, copy) void (^offline)(NSString *message);
@property(nonatomic, readonly) NSUInteger generation;
- (instancetype)initWithURL:(NSURL *)url;
- (void)login:(NSString *)password done:(void (^)(NSString *error))done;
- (void)surface:(NSString *)surface done:(void (^)(NSString *error))done;
- (void)tapX:(double)x y:(double)y frame:(NSUInteger)identity;
- (void)input:(NSDictionary *)coordinates frame:(NSUInteger)identity;
- (void)pause;
- (void)stop;
@end
