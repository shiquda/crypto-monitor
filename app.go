package main

import (
	"context"
	"encoding/json"
	"fmt"
	"strconv"
	"sync"

	"crypto-monitor/backend"

	"github.com/iaping/go-okx/ws/public"
	"github.com/wailsapp/wails/v2/pkg/runtime"
)

// App struct
type App struct {
	ctx             context.Context
	subscribedPairs map[string]bool
	mu              sync.Mutex
}

// NewApp creates a new App application struct
func NewApp() *App {
	return &App{
		subscribedPairs: make(map[string]bool),
	}
}

// startup is called when the app starts. The context is saved
// so we can call the runtime methods
func (a *App) startup(ctx context.Context) {
	a.ctx = ctx
	runtime.EventsOn(ctx, "crypto_pairs_changed", a.handleCryptoPairsChanged)
	runtime.EventsOn(ctx, "update_proxy_settings", a.handleProxySettings)
}

// handleProxySettings 处理代理配置更新
func (a *App) handleProxySettings(data ...interface{}) {
	if len(data) < 1 {
		fmt.Println("未接收到代理配置数据")
		return
	}

	proxyJSON, ok := data[0].(string)
	if !ok {
		fmt.Println("代理配置数据格式错误")
		return
	}

	var proxyConfig backend.ProxyConfig
	if err := json.Unmarshal([]byte(proxyJSON), &proxyConfig); err != nil {
		fmt.Printf("代理配置解析失败: %v\n", err)
		return
	}

	backend.SetGlobalProxyConfig(proxyConfig)

	fmt.Printf("代理配置已更新: %+v\n", proxyConfig)

	// 通知前端配置已更新
	runtime.EventsEmit(a.ctx, "proxy_config_updated", map[string]interface{}{
		"success": true,
		"message": "代理配置已更新",
	})
}

// handleCryptoPairsChanged 是包装后的事件处理函数
func (a *App) handleCryptoPairsChanged(data ...interface{}) {
	if len(data) < 1 {
		fmt.Println("did not receive any data")
		return
	}

	pairsInterface, ok := data[0].([]interface{})
	if !ok {
		fmt.Println("received data format is incorrect")
		return
	}

	pairs := make([]string, 0, len(pairsInterface))
	for _, pair := range pairsInterface {
		if p, ok := pair.(string); ok {
			pairs = append(pairs, p)
		} else {
			fmt.Println("pair is not a string")
		}
	}

	a.subscribeCryptoPrices(pairs)
}

// subscribeCryptoPrices subscribes to the prices of the given crypto pairs
func (a *App) subscribeCryptoPrices(pairs []string) {
	a.mu.Lock()
	defer a.mu.Unlock()

	for _, pair := range pairs {
		if a.subscribedPairs[pair] {
			continue
		}

		tickerChan, err := backend.GetCryptoPairListener(pair)
		if err != nil {
			priceInfo := map[string]interface{}{
				"pair":  pair,
				"error": err.Error(),
			}
			runtime.EventsEmit(a.ctx, "ticker_subscription_error", priceInfo)
			continue
		}

		a.subscribedPairs[pair] = true

		go func(pair string, ch <-chan public.EventTickers) {
			for ticker := range ch {
				last, _ := strconv.ParseFloat(ticker.Data[0].Last, 64)
				sodUtc0, _ := strconv.ParseFloat(ticker.Data[0].SodUtc0, 64)
				percentage := (last - sodUtc0) / sodUtc0 * 100
				percentageStr := ""
				if percentage > 0 {
					percentageStr = fmt.Sprintf("+%.2f%%", percentage)
				} else {
					percentageStr = fmt.Sprintf("%.2f%%", percentage)
				}
				priceInfo := map[string]interface{}{
					"pair":       pair,
					"price":      ticker.Data[0].Last,
					"percentage": percentageStr,
				}
				runtime.EventsEmit(a.ctx, "ticker_update", priceInfo)
			}

			a.mu.Lock()
			delete(a.subscribedPairs, pair)
			a.mu.Unlock()

			priceInfo := map[string]interface{}{
				"pair": pair,
				"msg":  "ticker subscription closed",
			}
			runtime.EventsEmit(a.ctx, "ticker_subscription_closed", priceInfo)
		}(pair, tickerChan)
	}
}
