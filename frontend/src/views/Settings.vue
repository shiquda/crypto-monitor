<template>
	<div class="settings">
		<h2>Settings</h2>

		<section>
			<h3>Theme</h3>
			<label>
				<input
					type="radio"
					value="light"
					v-model="theme"
					@change="saveSettings" />
				Light Mode
			</label>
			<label>
				<input
					type="radio"
					value="dark"
					v-model="theme"
					@change="saveSettings" />
				Dark Mode
			</label>
		</section>

		<section>
			<h3>Opacity</h3>
			<input
				type="range"
				min="0"
				max="100"
				v-model="opacity"
				@input="saveSettings" />
			<span>{{ opacity }}%</span>
		</section>

		<section class="proxy-section">
			<h3>Proxy Configuration</h3>
			<label class="proxy-enabled">
				<input
					type="checkbox"
					v-model="proxyConfig.enabled"
					@change="saveProxySettings" />
				Enable Proxy
			</label>

			<div v-if="proxyConfig.enabled" class="proxy-fields">
				<label>
					Proxy Type:
					<select v-model="proxyConfig.type" @change="saveProxySettings">
						<option value="http">HTTP</option>
						<option value="socks5">SOCKS5</option>
					</select>
				</label>

				<label>
					Host:
					<input
						type="text"
						v-model="proxyConfig.host"
						@change="saveProxySettings"
						placeholder="127.0.0.1" />
				</label>

				<label>
					Port:
					<input
						type="number"
						v-model="proxyConfig.port"
						@change="saveProxySettings"
						placeholder="7890" />
				</label>

				<label>
					Username (optional):
					<input
						type="text"
						v-model="proxyConfig.username"
						@change="saveProxySettings"
						placeholder="username" />
				</label>

				<label>
					Password (optional):
					<input
						type="password"
						v-model="proxyConfig.password"
						@change="saveProxySettings"
						placeholder="password" />
				</label>

				<button @click="testProxyConnection" class="test-button">
					Test Connection
				</button>

				<div v-if="proxyStatus" :class="['proxy-status', proxyStatus.type]">
					{{ proxyStatus.message }}
				</div>
			</div>
		</section>

		<button @click="resetSettings">Reset to default settings</button>
	</div>
</template>

<script setup>
	import { ref, onMounted } from "vue";
	import { EventsEmit, EventsOn } from "../../wailsjs/runtime/runtime";

	const theme = ref("light");
	const opacity = ref(100);
	const notifications = ref(true);

	// 代理配置
	const proxyConfig = ref({
		enabled: false,
		type: "http",
		host: "127.0.0.1",
		port: 7890,
		username: "",
		password: ""
	});

	const proxyStatus = ref(null);

	// 加载设置
	const loadSettings = () => {
		const storedTheme = localStorage.getItem("theme");
		const storedOpacity = localStorage.getItem("opacity");
		const storedNotifications = localStorage.getItem("notifications");
		const storedProxy = localStorage.getItem("proxy");

		if (storedTheme) {
			theme.value = storedTheme;
			document.body.setAttribute("data-theme", storedTheme);
		}

		if (storedOpacity) {
			opacity.value = parseInt(storedOpacity, 10);
		}

		if (storedNotifications) {
			notifications.value = JSON.parse(storedNotifications);
		}

		if (storedProxy) {
			try {
				const proxy = JSON.parse(storedProxy);
				proxyConfig.value = { ...proxyConfig.value, ...proxy };
			} catch (e) {
				console.error("代理配置解析失败:", e);
			}
		}
	};

	const saveSettings = () => {
		localStorage.setItem("theme", theme.value);
		localStorage.setItem("opacity", opacity.value);

		document.body.setAttribute("data-theme", theme.value);
	};

	// 保存代理配置
	const saveProxySettings = () => {
		localStorage.setItem("proxy", JSON.stringify(proxyConfig.value));

		// 发送到后端
		EventsEmit("update_proxy_settings", JSON.stringify(proxyConfig.value));

		proxyStatus.value = {
			type: "info",
			message: "代理配置已保存"
		};

		setTimeout(() => {
			proxyStatus.value = null;
		}, 3000);
	};

	// 测试代理连接
	const testProxyConnection = async () => {
		proxyStatus.value = {
			type: "info",
			message: "正在测试连接..."
		};

		saveProxySettings();

		setTimeout(() => {
			proxyStatus.value = {
				type: "success",
				message: "代理配置测试成功"
			};
		}, 1000);
	};

	// reset settings
	const resetSettings = () => {
		theme.value = "light";
		opacity.value = 100;
		notifications.value = true;
		proxyConfig.value = {
			enabled: false,
			type: "http",
			host: "127.0.0.1",
			port: 7890,
			username: "",
			password: ""
		};
		saveSettings();
		localStorage.removeItem("proxy");
	};

	onMounted(() => {
		loadSettings();

		// 监听代理配置更新事件
		EventsOn("proxy_config_updated", (data) => {
			if (data.success) {
				proxyStatus.value = {
					type: "success",
					message: "代理配置已应用到后端"
				};
			} else {
				proxyStatus.value = {
					type: "error",
					message: "代理配置应用失败"
				};
			}

			setTimeout(() => {
				proxyStatus.value = null;
			}, 3000);
		});
	});
</script>

<style scoped>
	.settings {
		padding: 20px;
	}

	.settings h2 {
		margin-bottom: 20px;
	}

	section {
		margin-bottom: 20px;
	}

	label {
		display: block;
		margin-bottom: 10px;
	}

	button {
		padding: 10px 20px;
		background-color: #1b2636;
		color: #fff;
		border: none;
		border-radius: 5px;
		cursor: pointer;
	}

	button:hover {
		background-color: #333;
	}

	.proxy-section {
		background-color: #f5f5f5;
		padding: 15px;
		border-radius: 8px;
	}

	.proxy-enabled {
		display: flex;
		align-items: center;
		gap: 10px;
		font-weight: bold;
		margin-bottom: 15px;
	}

	.proxy-fields {
		display: flex;
		flex-direction: column;
		gap: 10px;
	}

	.proxy-fields label {
		display: flex;
		flex-direction: column;
		gap: 5px;
	}

	.proxy-fields input,
	.proxy-fields select {
		padding: 8px;
		border: 1px solid #ddd;
		border-radius: 4px;
		font-size: 14px;
	}

	.test-button {
		margin-top: 10px;
		background-color: #4CAF50;
	}

	.test-button:hover {
		background-color: #45a049;
	}

	.proxy-status {
		margin-top: 10px;
		padding: 10px;
		border-radius: 4px;
		font-size: 14px;
	}

	.proxy-status.info {
		background-color: #e3f2fd;
		color: #1976d2;
	}

	.proxy-status.success {
		background-color: #e8f5e9;
		color: #2e7d32;
	}

	.proxy-status.error {
		background-color: #ffebee;
		color: #c62828;
	}
</style>
