使用：
 - 将`redpoint.py`放置在`~/.homeassistant/custom_components/`目录下
 - 配置文件：
```yaml
redpoint:

```
 - 如果HomeAssistant并不是以hass命令启动的（例如在群晖的docker上），可以增加以下的配置参数：
```yaml
redpoint:
  hass_cmd: python -m homeassistant
```
 
