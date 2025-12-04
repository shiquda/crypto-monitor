package backend

import (
	"fmt"
	"net/http"
	"net/url"
	"time"

	"github.com/gorilla/websocket"
)

// ProxyConfig 代理配置结构体
type ProxyConfig struct {
	Enabled   bool   `json:"enabled"`
	Type      string `json:"type"`       // "http" 或 "socks5"
	Host      string `json:"host"`
	Port      int    `json:"port"`
	Username  string `json:"username"`
	Password  string `json:"password"`
}

// CreateProxyDialer 创建代理 Dialer
func CreateProxyDialer(config ProxyConfig) (*websocket.Dialer, error) {
	if !config.Enabled {
		return nil, nil
	}

	var proxyURL *url.URL
	var err error

	// 构建代理 URL
	if config.Type == "http" {
		if config.Username != "" {
			proxyURL, err = url.Parse(fmt.Sprintf("http://%s:%s@%s:%d",
				config.Username, config.Password, config.Host, config.Port))
		} else {
			proxyURL, err = url.Parse(fmt.Sprintf("http://%s:%d", config.Host, config.Port))
		}
	} else if config.Type == "socks5" {
		if config.Username != "" {
			proxyURL, err = url.Parse(fmt.Sprintf("socks5://%s:%s@%s:%d",
				config.Username, config.Password, config.Host, config.Port))
		} else {
			proxyURL, err = url.Parse(fmt.Sprintf("socks5://%s:%d", config.Host, config.Port))
		}
	} else {
		return nil, fmt.Errorf("不支持的代理类型: %s", config.Type)
	}

	if err != nil {
		return nil, fmt.Errorf("代理 URL 解析失败: %w", err)
	}

	// 创建 WebSocket Dialer
	dialer := &websocket.Dialer{
		Proxy:             http.ProxyURL(proxyURL),
		HandshakeTimeout:  10 * time.Second,
		ReadBufferSize:    4096,
		WriteBufferSize:   4096,
		EnableCompression: true,
	}

	return dialer, nil
}

// 全局变量存储代理配置
var globalProxyConfig ProxyConfig

// SetGlobalProxyConfig 设置全局代理配置
func SetGlobalProxyConfig(config ProxyConfig) {
	globalProxyConfig = config
}

// GetGlobalProxyConfig 获取全局代理配置
func GetGlobalProxyConfig() ProxyConfig {
	return globalProxyConfig
}
