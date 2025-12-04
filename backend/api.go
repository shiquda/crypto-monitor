package backend

import (
	"encoding/json"
	"fmt"
	"regexp"

	"github.com/iaping/go-okx/ws"
	"github.com/iaping/go-okx/ws/public"
	"github.com/gorilla/websocket"
)

// 扩展 Public 类型以支持自定义 Dialer
type PublicWithDialer struct {
	*public.Public
	customDialer *websocket.Dialer
}

// NewPublicWithDialer 创建带自定义 Dialer 的 Public 实例
func NewPublicWithDialer(simulated bool, dialer *websocket.Dialer) *PublicWithDialer {
	publicClient := public.NewPublic(simulated)
	return &PublicWithDialer{
		Public:       publicClient,
		customDialer: dialer,
	}
}

// Subscribe 重写订阅方法以使用自定义 Dialer
func (p *PublicWithDialer) Subscribe(args interface{}, handler ws.Handler, handlerError ws.HandlerError) error {
	if p.customDialer != nil && p.Public.C != nil {
		p.Public.C.Dialer = p.customDialer
	}
	return p.Public.Subscribe(args, handler, handlerError)
}

func GetCryptoPairListener(cryptoPair string) (<-chan public.EventTickers, error) {
	match, err := regexp.MatchString("^[A-Z]+-[A-Z]+$", cryptoPair)
	if err != nil {
		return nil, fmt.Errorf("cryptoPair format error: %w", err)
	}
	if !match {
		return nil, fmt.Errorf("cryptoPair format error, correct example is BTC-USDT")
	}

	tickerChan := make(chan public.EventTickers)

	handler := func(c public.EventTickers) {
		tickerChan <- c
	}

	handlerError := func(err error) {
		fmt.Printf("SubscribeTickers error: %v\n", err)
		close(tickerChan)
	}

	// 获取当前代理配置
	proxyConfig := GetGlobalProxyConfig()

	// 创建代理 Dialer
	dialer, err := CreateProxyDialer(proxyConfig)
	if err != nil {
		return nil, fmt.Errorf("代理配置错误: %w", err)
	}

	// 如果启用了代理，使用自定义客户端
	if proxyConfig.Enabled && dialer != nil {
		publicClient := NewPublicWithDialer(false, dialer)

		// 创建订阅参数
		args := &ws.Args{
			Channel: "tickers",
			InstId:  cryptoPair,
		}

		if err := publicClient.Subscribe(args, func(message []byte) {
			var event public.EventTickers
			if err := json.Unmarshal(message, &event); err != nil {
				handlerError(fmt.Errorf("JSON 解析失败: %w", err))
				return
			}
			handler(event)
		}, handlerError); err != nil {
			return nil, fmt.Errorf("代理订阅失败: %w", err)
		}

		return tickerChan, nil
	}

	// 否则使用默认的 go-okx 订阅
	if err := public.SubscribeTickers(cryptoPair, handler, handlerError, false); err != nil {
		return nil, fmt.Errorf("SubscribeTickers failed: %w", err)
	}

	return tickerChan, nil
}
