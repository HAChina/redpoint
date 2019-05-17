使用：
 - 建立目录`~/.homeassistant/custom_components/redpoint`
 - 将`__init__.py`与`manifest.json`放置在`redpoint`目录下
 - 配置文件：
```yaml
redpoint:
```
 - HomeAssistant 0.74.2之前版本，需要在配置文件的`http`配置中，增加跨域访问配置（`cors_allowed_origins`），如下：
```yaml
http:
  # 其它的一些配置保留，增加以下两行配置内容
  cors_allowed_origins:
    - 'http://redpoint.hachina.io'
```

 - HomeAssistant 0.74.2及以后版本，不需要增加以上配置。