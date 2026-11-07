#import "HPController.h"
#import "HPConnection.h"
#import "HPVideoView.h"

@implementation HPController {
    HPVideoView *_video;
    HPConnection *_connection;
    UIView *_toolbar, *_setup;
    UITextField *_address, *_password;
    UILabel *_status;
    NSString *_surface;
    NSTimer *_watchdog;
    CFTimeInterval _lastFrame, _retryAt;
    BOOL _changing, _active;
    NSUInteger _frameID;
}
- (void)viewDidLoad {
    [super viewDidLoad];
    self.view.backgroundColor = [UIColor colorWithWhite:0.07 alpha:1];
    _surface = @"dashboard"; _active = YES;
    _video = [[HPVideoView alloc] initWithFrame:CGRectZero];
    [self.view addSubview:_video];
    [_video addGestureRecognizer:[[UITapGestureRecognizer alloc] initWithTarget:self action:@selector(tap:)]];
    [_video addGestureRecognizer:[[UIPanGestureRecognizer alloc] initWithTarget:self action:@selector(pan:)]];
    _toolbar = [[UIView alloc] initWithFrame:CGRectZero];
    _toolbar.backgroundColor = [UIColor colorWithRed:0.11 green:0.14 blue:0.17 alpha:1];
    [self.view addSubview:_toolbar];
    NSArray *titles = @[@"Дом", @"Музыка", @"Связь"];
    for (NSUInteger i = 0; i < titles.count; i++) {
        UIButton *button = [UIButton buttonWithType:UIButtonTypeSystem];
        button.frame = CGRectMake(i * 110, 0, 110, 48);
        [button setTitle:titles[i] forState:UIControlStateNormal];
        button.tintColor = [UIColor colorWithRed:0.01 green:0.66 blue:0.96 alpha:1];
        button.tag = i;
        [button addTarget:self action:@selector(navigate:) forControlEvents:UIControlEventTouchUpInside];
        [_toolbar addSubview:button];
    }
    _status = [[UILabel alloc] initWithFrame:CGRectZero];
    _status.textColor = [UIColor whiteColor]; _status.font = [UIFont systemFontOfSize:13];
    [_toolbar addSubview:_status];
    _setup = [[UIView alloc] initWithFrame:CGRectZero];
    _setup.backgroundColor = [UIColor colorWithWhite:0.12 alpha:1];
    [self.view addSubview:_setup];
    _address = [[UITextField alloc] initWithFrame:CGRectMake(24, 24, 432, 48)];
    _address.placeholder = @"http://адрес-сервера:8090";
    _address.text = [[NSUserDefaults standardUserDefaults] stringForKey:@"panelURL"];
    _address.keyboardType = UIKeyboardTypeURL;
    _address.autocapitalizationType = UITextAutocapitalizationTypeNone;
    _address.autocorrectionType = UITextAutocorrectionTypeNo;
    _address.borderStyle = UITextBorderStyleRoundedRect;
    [_setup addSubview:_address];
    _password = [[UITextField alloc] initWithFrame:CGRectMake(24, 88, 432, 48)];
    _password.placeholder = @"Пароль панели (пусто для открытого Demo)";
    _password.secureTextEntry = YES; _password.borderStyle = UITextBorderStyleRoundedRect;
    [_setup addSubview:_password];
    UIButton *connect = [UIButton buttonWithType:UIButtonTypeSystem];
    connect.frame = CGRectMake(24, 152, 432, 48);
    [connect setTitle:@"Подключить" forState:UIControlStateNormal];
    [connect addTarget:self action:@selector(connect) forControlEvents:UIControlEventTouchUpInside];
    [_setup addSubview:connect];
    __weak HPController *weakSelf = self;
    _video.frameReady = ^(NSUInteger identity) { [weakSelf frame:identity]; };
    _video.failure = ^(NSString *message) { [weakSelf disconnected:message]; };
    NSNotificationCenter *center = [NSNotificationCenter defaultCenter];
    [center addObserver:self selector:@selector(background) name:UIApplicationWillResignActiveNotification object:nil];
    [center addObserver:self selector:@selector(foreground) name:UIApplicationDidBecomeActiveNotification object:nil];
    _watchdog = [NSTimer scheduledTimerWithTimeInterval:1 target:self selector:@selector(tick) userInfo:nil repeats:YES];
    [self disconnected:@"Укажите адрес сервера HomePanel"];
}
- (void)viewDidLayoutSubviews {
    [super viewDidLayoutSubviews];
    CGSize size = self.view.bounds.size;
    _video.frame = CGRectMake(0, 0, size.width, MAX(0, size.height - 48));
    _toolbar.frame = CGRectMake(0, size.height - 48, size.width, 48);
    _status.frame = CGRectMake(340, 0, MAX(0, size.width - 352), 48);
    _setup.frame = CGRectMake((size.width - 480) / 2, (size.height - 240) / 2, 480, 224);
}
- (void)dealloc {
    [[NSNotificationCenter defaultCenter] removeObserver:self];
    [_watchdog invalidate]; [_connection stop];
}
- (void)connect {
    NSURL *url = [NSURL URLWithString:_address.text];
    if (!url.host.length || (![@"http" isEqual:url.scheme] && ![@"https" isEqual:url.scheme]) || url.user || url.password || url.query || url.fragment || (url.path.length && ![url.path isEqual:@"/"])) {
        _status.text = @"Нужен HTTP(S) адрес без логина, пути и параметров"; return;
    }
    [self.view endEditing:YES];
    [_connection stop];
    _changing = NO;
    _connection = [[HPConnection alloc] initWithURL:url];
    [[NSUserDefaults standardUserDefaults] setObject:url.absoluteString forKey:@"panelURL"];
    __weak HPController *weakSelf = self;
    _connection.bytes = ^(NSData *data) { [weakSelf receive:data]; };
    _connection.offline = ^(NSString *message) { [weakSelf disconnected:message]; };
    _status.text = @"Подключение…";
    NSString *password = _password.text ?: @""; _password.text = @"";
    [_connection login:password done:^(NSString *error) {
        HPController *controller = weakSelf;
        if (!controller) return;
        if (error) [controller disconnected:error];
        else { controller->_setup.hidden = YES; [controller selectSurface]; }
    }];
}
- (void)receive:(NSData *)data { if (_active) [_video consume:data]; }
- (void)selectSurface {
    if (!_connection || _changing || !_active || !_setup.hidden) return;
    _changing = YES; _lastFrame = 0; _retryAt = CACurrentMediaTime() + 30;
    _video.userInteractionEnabled = NO; [_video reset];
    _status.text = @"Ожидание изображения…";
    __weak HPController *weakSelf = self;
    [_connection surface:_surface done:^(NSString *error) {
        HPController *controller = weakSelf;
        if (!controller) return;
        controller->_changing = NO;
        if (error) [controller disconnected:error];
    }];
}
- (void)navigate:(UIButton *)button {
    if (button.tag == 2) {
        _changing = NO;
        [_connection pause]; _setup.hidden = NO;
        [self disconnected:@"Настройка подключения"];
    } else {
        if (_changing) return;
        _surface = button.tag == 0 ? @"dashboard" : @"music";
        [self selectSurface];
    }
}
- (void)frame:(NSUInteger)identity {
    _frameID = identity;
    _lastFrame = CACurrentMediaTime();
    _video.userInteractionEnabled = YES;
    _status.text = @"Поток подключён";
    [UIApplication sharedApplication].idleTimerDisabled = _active;
}
- (void)disconnected:(NSString *)message {
    _status.text = message; _lastFrame = 0;
    _video.userInteractionEnabled = NO;
    [UIApplication sharedApplication].idleTimerDisabled = NO;
    _retryAt = CACurrentMediaTime() + 5;
}
- (void)tick {
    CFTimeInterval now = CACurrentMediaTime();
    if (_lastFrame && now - _lastFrame > 2) [self disconnected:@"Нет свежего изображения"];
    if (_active && _setup.hidden && !_lastFrame && !_changing && now >= _retryAt) [self selectSurface];
}
- (void)tap:(UITapGestureRecognizer *)gesture {
    if (!_lastFrame || CACurrentMediaTime() - _lastFrame > 2 || _changing) return;
    CGSize size = _video.bounds.size;
    CGFloat scale = MIN(size.width / 1024.0, size.height / 720.0);
    CGRect rect = CGRectMake((size.width - 1024 * scale) / 2, (size.height - 720 * scale) / 2, 1024 * scale, 720 * scale);
    CGPoint point = [gesture locationInView:_video];
    if (CGRectContainsPoint(rect, point)) [_connection tapX:(point.x - rect.origin.x) / rect.size.width y:(point.y - rect.origin.y) / rect.size.height frame:_frameID];
}
- (void)background {
    _active = NO; _changing = NO;
    [_connection pause]; [_video reset];
    [self disconnected:@"Приостановлено"];
}
- (void)pan:(UIPanGestureRecognizer *)gesture {
    if (gesture.state != UIGestureRecognizerStateEnded || !_lastFrame || _changing || CACurrentMediaTime() - _lastFrame > 2) return;
    CGSize size = _video.bounds.size;
    CGFloat scale = MIN(size.width / 1024.0, size.height / 720.0);
    CGRect rect = CGRectMake((size.width - 1024 * scale) / 2, (size.height - 720 * scale) / 2, 1024 * scale, 720 * scale);
    CGPoint end = [gesture locationInView:_video], delta = [gesture translationInView:_video];
    CGPoint start = CGPointMake(end.x - delta.x, end.y - delta.y);
    if (!CGRectContainsPoint(rect, start) || !CGRectContainsPoint(rect, end)) return;
    [_connection input:@{@"kind":@"swipe", @"x":@((start.x-rect.origin.x)/rect.size.width), @"y":@((start.y-rect.origin.y)/rect.size.height), @"end_x":@((end.x-rect.origin.x)/rect.size.width), @"end_y":@((end.y-rect.origin.y)/rect.size.height)} frame:_frameID];
}
- (void)foreground { _active = YES; [self selectSurface]; }
- (BOOL)prefersStatusBarHidden { return YES; }
@end
