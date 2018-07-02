使用：
 - 将`redpoint.py`放置在`~/.homeassistant/custom_components/`目录下
 - 配置文件：

```yaml
redpoint:

```

 - 如果HomeAssistant并不是以hass命令启动的（例如在群晖的docker上），可以增加以下的配置参数（指定启动命令）：

```yaml
redpoint:
  # 其中python在某些系统中可能为python3
  hass_cmd: python -m homeassistant
```

 - 如果在HomeAssistant的`http`配置中，配置了跨域访问（`cors_allowed_origins`），请在其中增加`http://redpoint.hachina.io`<br>
如果没有配置跨域访问，不必增加。