#import "HPConnection.h"

@implementation HPConnection {
    NSURL *_base;
    NSURLSession *_session;
    NSURLSessionDataTask *_stream;
    NSString *_csrf;
    NSUInteger _generation, _epoch;
}
- (instancetype)initWithURL:(NSURL *)url {
    if ((self = [super init])) {
        _base = url;
        NSURLSessionConfiguration *config = [NSURLSessionConfiguration ephemeralSessionConfiguration];
        config.timeoutIntervalForRequest = 15;
        config.timeoutIntervalForResource = 24 * 3600;
        config.URLCache = nil;
        _session = [NSURLSession sessionWithConfiguration:config delegate:self delegateQueue:[NSOperationQueue mainQueue]];
    }
    return self;
}
- (NSUInteger)generation { return _generation; }
- (void)request:(NSString *)path body:(NSDictionary *)body done:(void (^)(NSDictionary *, NSString *))done {
    NSMutableURLRequest *request = [NSMutableURLRequest requestWithURL:[NSURL URLWithString:path relativeToURL:_base]];
    request.cachePolicy = NSURLRequestReloadIgnoringLocalCacheData;
    if (body) {
        request.HTTPMethod = @"POST";
        [request setValue:@"application/json" forHTTPHeaderField:@"Content-Type"];
        if (_csrf) [request setValue:_csrf forHTTPHeaderField:@"X-CSRF-Token"];
        request.HTTPBody = [NSJSONSerialization dataWithJSONObject:body options:0 error:NULL];
    }
    NSUInteger epoch = _epoch;
    [[_session dataTaskWithRequest:request completionHandler:^(NSData *data, NSURLResponse *response, NSError *error) {
        dispatch_async(dispatch_get_main_queue(), ^{
            if (epoch != self->_epoch) return;
            NSInteger code = [(NSHTTPURLResponse *)response statusCode];
            NSDictionary *result = data ? [NSJSONSerialization JSONObjectWithData:data options:0 error:NULL] : nil;
            if (![result isKindOfClass:[NSDictionary class]]) result = nil;
            NSString *message = nil;
            if (error) message = @"Нет связи. Действие не повторено автоматически.";
            else if (code < 200 || code >= 300 || !result) {
                id detail = result[@"detail"];
                message = [detail isKindOfClass:[NSString class]] ? detail : @"Сервер отклонил запрос";
            }
            done(result, message);
        });
    }] resume];
}
- (void)login:(NSString *)password done:(void (^)(NSString *))done {
    NSDictionary *body = password.length ? @{@"password":password} : nil;
    [self request:body ? @"/api/login" : @"/api/session" body:body done:^(NSDictionary *result, NSString *error) {
        id csrf = result[@"csrf"];
        if (!error && ![csrf isKindOfClass:[NSString class]]) error = @"Неверный ответ сервера";
        if (!error) self->_csrf = csrf;
        done(error);
    }];
}
- (void)surface:(NSString *)surface done:(void (^)(NSString *))done {
    [_stream cancel]; _stream = nil;
    [self request:@"/api/display/surface" body:@{@"surface":surface} done:^(NSDictionary *result, NSString *error) {
        id generation = result[@"generation"];
        if (!error && ![generation isKindOfClass:[NSNumber class]]) error = @"Неверный номер экрана";
        if (!error) {
            self->_generation = [generation unsignedIntegerValue];
            NSString *path = [NSString stringWithFormat:@"/api/display/stream.h264?generation=%lu", (unsigned long)self->_generation];
            NSMutableURLRequest *request = [NSMutableURLRequest requestWithURL:[NSURL URLWithString:path relativeToURL:self->_base]];
            request.timeoutInterval = 30;
            self->_stream = [self->_session dataTaskWithRequest:request];
            [self->_stream resume];
        }
        done(error);
    }];
}
- (void)tapX:(double)x y:(double)y frame:(NSUInteger)identity {
    [self input:@{@"kind":@"tap", @"x":@(x), @"y":@(y)} frame:identity];
}
- (void)input:(NSDictionary *)coordinates frame:(NSUInteger)identity {
    NSMutableDictionary *body = [coordinates mutableCopy];
    body[@"generation"] = @(_generation); body[@"frame"] = @(identity);
    [self request:@"/api/display/input" body:body done:^(NSDictionary *result, NSString *error) {
        if ((error || ![result[@"ok"] boolValue]) && self.offline) self.offline(error ?: @"Действие не подтверждено");
    }];
}
- (void)stop {
    [self pause];
    [_session invalidateAndCancel];
    self.bytes = nil; self.offline = nil;
}
- (void)pause {
    _epoch += 1;
    [_stream cancel]; _stream = nil;
}
- (void)URLSession:(NSURLSession *)session dataTask:(NSURLSessionDataTask *)task didReceiveResponse:(NSURLResponse *)response completionHandler:(void (^)(NSURLSessionResponseDisposition))handler {
    if (task != _stream) { handler(NSURLSessionResponseAllow); return; }
    BOOL valid = [(NSHTTPURLResponse *)response statusCode] == 200 && [response.MIMEType isEqualToString:@"video/h264"];
    handler(valid ? NSURLSessionResponseAllow : NSURLSessionResponseCancel);
    if (!valid && self.offline) self.offline(@"Видеопоток недоступен");
}
- (void)URLSession:(NSURLSession *)session dataTask:(NSURLSessionDataTask *)task didReceiveData:(NSData *)data {
    if (task == _stream && self.bytes) self.bytes(data);
}
- (void)URLSession:(NSURLSession *)session task:(NSURLSessionTask *)task didCompleteWithError:(NSError *)error {
    if (task == _stream && self.offline) { _stream = nil; self.offline(@"Поток остановлен. Подключитесь заново."); }
}
- (void)URLSession:(NSURLSession *)session task:(NSURLSessionTask *)task willPerformHTTPRedirection:(NSHTTPURLResponse *)response newRequest:(NSURLRequest *)request completionHandler:(void (^)(NSURLRequest *))handler {
    handler(nil);
}
@end
